"""Les réponses des assureurs au cahier des charges : saisies, confrontées aux conditions, classées, choisies."""
import json
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from courtage.db import contexte
from tests.outils import V1, en_tant_que
from tests.test_fiche import fiche
from tests.test_rapport import emettre

# Le cahier demande : garanti ≥ 2,5 %, participation ≥ 85 %, frais cotisations ≤ 3 %, encours ≤ 0,5 %,
# préavis ≤ 3 mois, pénalité ≤ 0, délai ≤ 30 jours, étude de la plateforme acceptée, reporting annuel.
CONFORME = {"assureur": "Assureur A", "recue_le": date.today().isoformat(), "taux_garanti": 0.03,
            "participation_benefices": 0.9, "frais_sur_cotisations": 0.02, "frais_sur_encours": 0.004,
            "delai_paiement_jours": 20, "transfert_preavis_mois": 3, "transfert_penalite": 0.0,
            "accepte_etude_plateforme": True, "reporting_annuel": True}
PDF = b"%PDF-1.4\n%offre\n%%EOF"


@pytest.fixture
def cahier(client, azito):
    e = emettre(client, azito)
    f = fiche(client, azito, e["id"])
    assert f.status_code == 201, f.text
    return {**azito, "fiche": f.json()}


def u(a, suite=""):
    return f"{V1}/organisations/{a['org']}/fiches/{a['fiche']['id']}{suite}"


def repondre(client, a, qui="conseiller", offre=None, **champs):
    fichiers = {"offre": ("offre.pdf", offre)} if offre else None
    return client.post(u(a, "/reponses"), headers=en_tant_que(a[qui]), data={"donnees": json.dumps({**CONFORME, **champs})},
                       files=fichiers)


def lire(client, a, qui="drh"):
    r = client.get(u(a, "/reponses"), headers=en_tant_que(a[qui]))
    assert r.status_code == 200, r.text
    return r.json()


def test_une_reponse_conforme(client, cahier):
    r = repondre(client, cahier)
    assert r.status_code == 201, r.text
    x = r.json()
    assert x["conforme"] is True and all(c["conforme"] for c in x["conformite"])
    assert {c["critere"] for c in x["conformite"]} >= {"taux_garanti", "participation_benefices", "frais_sur_cotisations",
                                                         "frais_sur_encours", "delai_paiement_jours", "transfert_preavis_mois",
                                                         "transfert_penalite", "accepte_etude_plateforme", "reporting_annuel"}


def test_les_ecarts_sont_nommes(client, cahier):
    x = repondre(client, cahier, assureur="Assureur B", frais_sur_cotisations=0.04, transfert_preavis_mois=6,
                 accepte_etude_plateforme=False, delai_paiement_jours=None).json()
    assert x["conforme"] is False
    ecarts = {c["critere"]: c for c in x["conformite"] if c["conforme"] is False}
    assert set(ecarts) == {"frais_sur_cotisations", "transfert_preavis_mois", "accepte_etude_plateforme"}
    assert ecarts["frais_sur_cotisations"]["demande"] == 0.03 and ecarts["frais_sur_cotisations"]["offert"] == 0.04
    non_dit = next(c for c in x["conformite"] if c["critere"] == "delai_paiement_jours")
    assert non_dit["conforme"] is None                     # non renseigné : ni conforme ni en écart, et dit


def test_une_reponse_tardive_est_signalee(client, cahier, bases):
    # Un cahier dont la date limite est passée : on la recule en base (le rôle propriétaire le peut).
    with bases[0].begin() as c:
        c.execute(text("UPDATE fiches_regime SET date_limite_reponse = CURRENT_DATE - 1, emise_le = now() - interval '40 days' "
                       "WHERE id = :f"), {"f": cahier["fiche"]["id"]})
    x = repondre(client, cahier).json()
    assert x["tardive"] is True


def test_les_dates_de_reception(client, cahier):
    demain = (date.today() + timedelta(days=1)).isoformat()
    assert repondre(client, cahier, recue_le=demain).json()["code"] == "date_a_venir"
    hier = (date.today() - timedelta(days=1)).isoformat()
    assert repondre(client, cahier, recue_le=hier).json()["code"] == "reponse_avant_cahier"


def test_un_assureur_une_reponse_active(client, cahier):
    repondre(client, cahier)
    r = repondre(client, cahier)
    assert r.status_code == 409 and r.json()["code"] == "reponse_existante"


def test_le_classement_par_le_cout_net(client, cahier):
    repondre(client, cahier)
    repondre(client, cahier, assureur="Assureur Cher", frais_sur_cotisations=0.03, taux_garanti=0.025, participation_benefices=0.85,
             frais_sur_encours=0.005)
    c = lire(client, cahier)
    assert [x["assureur"] for x in c["reponses"]] == ["Assureur A", "Assureur Cher"]
    assert [x["rang"] for x in c["reponses"]] == [1, 2]
    assert c["reponses"][0]["cout_net_actualise"] < c["reponses"][1]["cout_net_actualise"]
    assert "Provision interne" in c["comparaison"]["classement"]
    assert c["recommandee"] == c["reponses"][0]["id"]


def test_la_recommandee_est_la_moins_chere_des_conformes(client, cahier):
    # La moins chère a des frais nuls… mais une pénalité de transfert : non conforme.
    repondre(client, cahier, assureur="Piège", frais_sur_cotisations=0.0, frais_sur_encours=0.0, transfert_penalite=0.05)
    repondre(client, cahier)
    c = lire(client, cahier)
    assert c["reponses"][0]["assureur"] == "Piège" and c["reponses"][0]["conforme"] is False
    assert c["recommandee"] == next(x["id"] for x in c["reponses"] if x["assureur"] == "Assureur A")


# --- Le choix de l'entreprise --------------------------------------------------------------

def test_l_entreprise_choisit_la_recommandee_sans_avoir_a_se_justifier(client, cahier):
    a = repondre(client, cahier).json()
    assert client.post(u(cahier, "/choix"), json={"reponse_id": a["id"]}, headers=en_tant_que(cahier["conseiller"])).status_code == 403
    r = client.post(u(cahier, "/choix"), json={"reponse_id": a["id"]}, headers=en_tant_que(cahier["drh"]))
    assert r.status_code == 201, r.text
    c = lire(client, cahier)
    assert c["choix"]["reponse_id"] == a["id"] and c["choix"]["assureur"] == "Assureur A"


def test_un_autre_choix_se_motive(client, cahier):
    repondre(client, cahier)
    b = repondre(client, cahier, assureur="Assureur B", frais_sur_cotisations=0.04).json()
    r = client.post(u(cahier, "/choix"), json={"reponse_id": b["id"]}, headers=en_tant_que(cahier["drh"]))
    assert r.status_code == 422 and r.json()["code"] == "motif_requis"
    r = client.post(u(cahier, "/choix"), json={"reponse_id": b["id"], "motif": "Assureur déjà en place, service reconnu"},
                    headers=en_tant_que(cahier["drh"]))
    assert r.status_code == 201


def test_un_cahier_attribue_est_clos(client, cahier):
    a = repondre(client, cahier).json()
    client.post(u(cahier, "/choix"), json={"reponse_id": a["id"]}, headers=en_tant_que(cahier["drh"]))
    assert client.post(u(cahier, "/choix"), json={"reponse_id": a["id"]}, headers=en_tant_que(cahier["drh"])).json()["code"] == "fiche_attribuee"
    assert repondre(client, cahier, assureur="Retardataire").json()["code"] == "fiche_attribuee"


# --- Une écriture ------------------------------------------------------------------------

def test_corriger_et_retirer(client, cahier):
    a = repondre(client, cahier).json()
    r = client.post(u(cahier, f"/reponses/{a['id']}/correction"), headers=en_tant_que(cahier["conseiller"]),
                    data={"donnees": json.dumps({**CONFORME, "taux_garanti": 0.028, "motif_correction": "Offre révisée"})})
    assert r.status_code == 201, r.text
    assert [x["taux_garanti"] for x in lire(client, cahier)["reponses"]] == [0.028]
    r = client.post(u(cahier, f"/reponses/{r.json()['id']}/retrait"), headers=en_tant_que(cahier["conseiller"]),
                    json={"motif_correction": "L'assureur retire son offre"})
    assert r.status_code == 201
    c = lire(client, cahier)
    assert c["reponses"] == [] and c["comparaison"] is None


def test_une_reponse_ne_se_modifie_pas(client, cahier, bases):
    repondre(client, cahier)
    with pytest.raises(ProgrammingError, match="permission"):
        with bases[1].begin() as c:
            contexte(c, cahier["org"])
            c.execute(text("UPDATE reponses_fiche SET taux_garanti = 0.1"))


def test_l_offre_de_l_assureur_jointe(client, cahier):
    assert repondre(client, cahier, offre=b"MZ").json()["code"] == "type_de_piece"
    a = repondre(client, cahier, offre=PDF).json()
    assert a["offre"]["nom_fichier"] == "offre.pdf"
    r = client.get(u(cahier, f"/reponses/{a['id']}/offre"), headers=en_tant_que(cahier["drh"]))
    assert r.status_code == 200 and r.content == PDF
