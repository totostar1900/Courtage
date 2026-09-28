"""Fiche régime : le cahier des charges envoyé aux assureurs, agrégé, scellé, vérifiable."""
import json
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from courtage.fiche import SEUIL, agreger_population, regrouper_echeancier
from tests.outils import sous_mandat, V1, en_tant_que, etude
from tests.test_rapport import emettre, pages
from tests.test_regime import CADRES, CCI, adopter, categorie, regime

DANS_UN_MOIS = (date.today() + timedelta(days=30)).isoformat()
CONDITIONS = {"taux_garanti_minimum": 0.025, "frais_sur_cotisations_maximum": 0.03,
              "frais_sur_encours_maximum": 0.005, "participation_benefices_minimum": 0.85,
              "transfert_preavis_mois_maximum": 3, "transfert_penalite_maximum": 0.0,
              "delai_paiement_jours_maximum": 30, "base_etude_plateforme": True, "reporting_annuel": True}


def fiche(client, a, etude_id, qui="conseiller", mandat=True, **champs):
    if mandat:
        sous_mandat(client, a)
    corps = {"etude_id": etude_id, "date_limite_reponse": DANS_UN_MOIS, "conditions": CONDITIONS, **champs}
    return client.post(f"{V1}/organisations/{a['org']}/fiches", json=corps, headers=en_tant_que(a[qui]))


# --- Agrégation : rien d'individuel ne sort -----------------------------------

def test_une_case_de_moins_de_trois_personnes_est_masquee():
    lignes = [{"age": a, "anciennete": 5.0, "categorie": None} for a in (31, 32, 33, 47, 58)]
    pop = agreger_population(lignes, salaires=[1_000_000] * 5)
    cases = {t["tranche"]: t["effectif"] for t in pop["pyramide_des_ages"]}
    assert cases["30-34"] == 3
    assert cases["45-49"] == f"<{SEUIL}" and cases["55-59"] == f"<{SEUIL}"


def test_une_categorie_de_moins_de_trois_personnes_ne_donne_pas_sa_masse_salariale():
    lignes = [{"age": 40, "anciennete": 5.0, "categorie": "Direction"}] * 2 + [{"age": 40, "anciennete": 5.0,
                                                                              "categorie": "Personnel"}] * 5
    pop = agreger_population(lignes, salaires=[9_000_000] * 2 + [1_000_000] * 5)
    assert pop["par_categorie"]["Direction"] == {"effectif": f"<{SEUIL}", "masse_salariale": None}
    assert pop["par_categorie"]["Personnel"]["masse_salariale"] == 5_000_000


def test_l_echeancier_regroupe_jusqu_a_trois_departs_au_moins():
    echeancier = [{"annee": a, "effectif": n, "prestations_probables": 100 * n}
                  for a, n in [(2021, 1), (2023, 1), (2027, 2), (2029, 1), (2035, 4), (2041, 1)]]
    groupes = regrouper_echeancier(echeancier, depuis=2020)
    assert all(g["departs"] >= SEUIL for g in groupes)
    assert sum(g["departs"] for g in groupes) == 10
    assert sum(g["prestations_probables"] for g in groupes) == 1000
    assert groupes[0]["periode"] == "2020-2029"


# --- Par l'API ----------------------------------------------------------------

def test_la_fiche_d_une_etude_emise(client, azito):
    e = emettre(client, azito)
    r = fiche(client, azito, e["id"])
    assert r.status_code == 201, r.text
    f = r.json()
    assert f["numero"].startswith("RL-")
    c = f["contenu"]
    assert c["etude"]["rapport"] == e["rapport"]["numero"]
    assert c["etude"]["totaux"]["dette"] == e["totaux"]["dette"]
    assert c["population"]["effectif"] == 23
    assert sum(g["departs"] for g in c["echeancier"]) == 23
    assert all(g["departs"] >= SEUIL for g in c["echeancier"])
    assert c["conditions_demandees"]["taux_garanti_minimum"] == 0.025
    assert {"taux_garanti", "participation_benefices", "frais_sur_cotisations", "frais_sur_encours",
            "historique_participation_5_ans", "delai_paiement_jours", "transfert_preavis_mois",
            "transfert_penalite", "accepte_etude_plateforme"} <= set(c["grille_de_reponse"])
    texte = json.dumps(c, ensure_ascii=False)
    for s in ("SANS-MATRICULE", "matricule", "Nom Prénom"):
        assert s not in texte


def test_la_fiche_reprend_le_regime(client, azito):
    from tests.outils import deposer, fichier_azito
    v = regime(client, azito, [categorie("Cadre", CADRES), categorie("*", CCI)])
    adopter(client, azito, v["id"])
    f = deposer(client, azito["org"], azito["drh"], fichier_azito(categories={i: "Cadre" for i in range(5)}))["id"]
    e = emettre(client, {**azito, "fichier": f}, convention_code=None, regime_version_id=v["id"])
    c = fiche(client, azito, e["id"]).json()["contenu"]
    assert c["regime"]["nom"] == "Accord AZITO 2015"
    assert {x["categorie"] for x in c["regime"]["categories"]} == {"Cadre", "*"}
    assert set(c["population"]["par_categorie"]) == {"Cadre", "Employé"}


def test_pas_de_fiche_sur_un_brouillon(client, azito):
    e = etude(client, azito).json()
    r = fiche(client, azito, e["id"])
    assert r.status_code == 409 and r.json()["code"] == "etude_non_emise"


def test_le_conseiller_emet_le_client_lit(client, azito):
    e = emettre(client, azito)
    assert fiche(client, azito, e["id"], qui="drh").status_code == 403
    f = fiche(client, azito, e["id"]).json()
    r = client.get(f"{V1}/organisations/{azito['org']}/fiches", headers=en_tant_que(azito["drh"]))
    assert [x["numero"] for x in r.json()] == [f["numero"]]


def test_une_date_limite_passee_est_refusee(client, azito):
    e = emettre(client, azito)
    r = fiche(client, azito, e["id"], date_limite_reponse="2020-01-01")
    assert r.status_code == 422 and r.json()["code"] == "date_limite_passee"


def test_le_document_scelle_et_verifiable(client, azito):
    e = emettre(client, azito)
    f = fiche(client, azito, e["id"]).json()
    r = client.get(f"{V1}/organisations/{azito['org']}/fiches/{f['id']}/document", headers=en_tant_que(azito["drh"]))
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    textes = pages(r.content)
    assert "Cahier des charges" in textes[0]
    assert all(f["numero"] in t for t in textes)
    assert "SANS-MATRICULE" not in "\n".join(textes)
    v = client.get(f"{V1}/verifier/{f['numero']}").json()
    assert v["nature"] == "fiche_regime" and v["authentique"] is True
    assert client.post(f"{V1}/verifier/{f['numero']}", files={"document": ("f.pdf", r.content)}).json()["conforme"]


def test_une_fiche_emise_ne_bouge_plus(client, azito, bases):
    e = emettre(client, azito)
    f = fiche(client, azito, e["id"]).json()
    from sqlalchemy.exc import ProgrammingError
    from courtage.db import contexte
    with pytest.raises(ProgrammingError, match="permission denied"):
        with bases[1].begin() as c:
            contexte(c, azito["org"])
            c.execute(text("UPDATE fiches_regime SET conditions = '{}' WHERE id = :f"), {"f": f["id"]})
