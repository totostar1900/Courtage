"""P3 : en courtage, le dossier de prise en charge — l'identité ici seulement, un PDF scellé, un suivi, un effacement."""
import io
from datetime import date, timedelta

import pymupdf
import pytest
from dateutil.relativedelta import relativedelta
from sqlalchemy import text

from tests.outils import V1, en_tant_que, sous_contrat
from tests.test_prestations import DEPART

IDENTITE = {"qualite": "salarie", "nom": "KOUASSI", "prenoms": "Aya Esther", "date_naissance": "1960-01-15",
            "piece_type": "cni", "piece_numero": "CI-0012345678", "telephone": "+2250701020304",
            "moyen_paiement": "virement", "coordonnees_paiement": "CI93 CI00 0000 0000 0000 0000 0000"}
COURTAGE = {"en_vigueur_du": "2019-01-01", "service": "courtage", "assureur": "Assureur A",
            "numero_police": "IFC-2019-7", "mandat_reference": "Mandat du 12/12/2018"}
PDF_MINIMAL = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def u(a, suite=""):
    return f"{V1}/organisations/{a['org']}{suite}"


@pytest.fixture
def depart(client, azito):
    """AZITO en courtage depuis 2019, et un départ en retraite au 01/01/2020 (dû 3 625 000 F)."""
    assert client.post(u(azito, "/contrats"), json=COURTAGE, headers=en_tant_que(azito["conseiller"])).status_code == 201
    r = client.post(u(azito, "/prestations"), json={**DEPART, "verse": 3_625_000}, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 201, r.text
    return {**azito, "prestation": r.json()}


def ouvrir(client, a, qui="drh", **champs):
    corps = {"prestation_id": a["prestation"]["id"], "montant_demande": 3_625_000, "beneficiaire": IDENTITE, **champs}
    return client.post(u(a, "/dossiers"), json=corps, headers=en_tant_que(a[qui]))


def etape(client, a, dossier, action, qui="conseiller", **corps):
    return client.post(u(a, f"/dossiers/{dossier}/{action}"), json=corps, headers=en_tant_que(a[qui]))


def piece(client, a, dossier, nature="certificat_travail", contenu=PDF_MINIMAL, nom="certificat.pdf", qui="drh"):
    return client.post(u(a, f"/dossiers/{dossier}/pieces"), headers=en_tant_que(a[qui]),
                       files={"fichier": (nom, contenu)}, data={"nature": nature})


def jusqu_a_transmis(client, a, le="2020-02-01"):
    d = ouvrir(client, a).json()
    assert piece(client, a, d["id"]).status_code == 201
    assert etape(client, a, d["id"], "verification", conforme=True).status_code == 201
    r = etape(client, a, d["id"], "transmission", le=le)
    assert r.status_code == 201, r.text
    return r.json()


# --- Qui, et seulement en courtage ------------------------------------------------------

def test_en_comparaison_aucune_identite_n_est_recueillie(client, azito, bases):
    sous_contrat(client, azito)          # sous contrat depuis 2021 : le départ de 2020 est d'avant le mandat
    p = client.post(u(azito, "/prestations"), json=DEPART, headers=en_tant_que(azito["drh"])).json()
    r = client.post(u(azito, "/dossiers"), headers=en_tant_que(azito["drh"]),
                    json={"prestation_id": p["id"], "montant_demande": 1, "beneficiaire": IDENTITE})
    assert r.status_code == 409 and r.json()["code"] == "pas_de_mandat"
    assert "votre assureur" in r.json()["message"]
    with bases[0].connect() as c:
        assert c.execute(text("SELECT count(*) FROM beneficiaires WHERE organisation_id = :o"), {"o": azito["org"]}).scalar() == 0


def test_la_drh_ouvre_le_conseiller_verifie(client, depart):
    assert ouvrir(client, depart, qui="conseiller").status_code == 403
    d = ouvrir(client, depart)
    assert d.status_code == 201, d.text
    assert d.json()["statut"] == "declare" and d.json()["assureur"] == "Assureur A"
    assert etape(client, depart, d.json()["id"], "verification", qui="drh", conforme=True).status_code == 403


def test_pas_de_dossier_pour_un_depart_hors_retraite(client, depart):
    p = client.post(u(depart, "/prestations"), json={**DEPART, "matricule": "Z-1", "motif": "demission"},
                    headers=en_tant_que(depart["drh"])).json()
    r = client.post(u(depart, "/dossiers"), headers=en_tant_que(depart["drh"]),
                    json={"prestation_id": p["id"], "montant_demande": 1, "beneficiaire": IDENTITE})
    assert r.status_code == 409 and r.json()["code"] == "pas_d_ifc"


def test_un_seul_dossier_par_depart(client, depart):
    assert ouvrir(client, depart).status_code == 201
    r = ouvrir(client, depart)
    assert r.status_code == 409 and r.json()["code"] == "dossier_existant"


def test_on_ne_demande_pas_plus_que_le_verse(client, depart):
    r = ouvrir(client, depart, montant_demande=4_000_000)
    assert r.status_code == 422 and r.json()["code"] == "demande_au_dela_du_verse"


# --- L'identité ne sort pas de son dossier -----------------------------------------------

def test_l_identite_ne_se_lit_que_dans_le_dossier_et_pas_par_tous(client, depart, bases):
    d = ouvrir(client, depart).json()
    assert d["beneficiaire"]["nom"] == "KOUASSI"
    for qui in ("drh", "conseiller"):
        assert client.get(u(depart, f"/dossiers/{d['id']}"), headers=en_tant_que(depart[qui])).json()["beneficiaire"]["nom"] == "KOUASSI"
    with bases[0].begin() as c:
        lecteur = c.execute(text("INSERT INTO utilisateurs (email, nom_affiche) VALUES ('lec@x.ci', 'L') RETURNING id")).scalar_one()
        c.execute(text("INSERT INTO adhesions (utilisateur_id, organisation_id, role) VALUES (:u, :o, 'lecteur_client')"),
                  {"u": lecteur, "o": depart["org"]})
    vu = client.get(u(depart, f"/dossiers/{d['id']}"), headers=en_tant_que(lecteur))
    assert vu.status_code == 200 and vu.json()["beneficiaire"] is None and "KOUASSI" not in vu.text
    for chemin in ("/prestations", "/dossiers"):
        assert "KOUASSI" not in client.get(u(depart, chemin), headers=en_tant_que(depart["drh"])).text
    with bases[0].connect() as c:
        journal = " ".join(str(m) for m in c.execute(text("SELECT details FROM journal WHERE organisation_id = :o"),
                                                      {"o": depart["org"]}).scalars())
    assert "KOUASSI" not in journal and "CI-0012345678" not in journal


# --- Les étapes ----------------------------------------------------------------------

def test_le_parcours_jusqu_au_paiement(client, depart, bases):
    transmis = jusqu_a_transmis(client, depart)
    assert transmis["statut"] == "transmis" and transmis["numero"].startswith("PC-")
    numero = transmis["numero"]

    # Le PDF porte l'identité ; le sceau public, non.
    pdf = client.get(u(depart, f"/dossiers/{transmis['id']}/document"), headers=en_tant_que(depart["conseiller"]))
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    with pymupdf.open(stream=pdf.content, filetype="pdf") as doc:
        texte = "".join(p.get_text() for p in doc)
    assert "KOUASSI" in texte and numero in texte and "3 625 000" in texte
    publique = client.get(f"{V1}/verifier/{numero}").json()
    assert publique["authentique"] and publique["nature"] == "prise_en_charge"
    assert "KOUASSI" not in str(publique) and "A-017" not in str(publique)
    assert client.post(f"{V1}/verifier/{numero}", files={"document": ("d.pdf", pdf.content)}).json()["conforme"]

    paye = etape(client, depart, transmis["id"], "reponse", paye=True, montant=3_625_000, le="2020-03-10")
    assert paye.status_code == 201, paye.text
    assert paye.json()["statut"] == "paye"
    # Le paiement constaté s'écrit sur la prestation, par une ligne qui remplace la précédente.
    p = client.get(u(depart, "/prestations"), headers=en_tant_que(depart["drh"])).json()["prestations"][0]
    assert (p["part_fonds_payee"], p["payee_le"], p["part_fonds_demandee"]) == (3_625_000, "2020-03-10", 3_625_000)
    assert numero in p["motif_correction"] and p["dossier"]["statut"] == "paye"


def test_on_ne_transmet_pas_un_dossier_non_verifie(client, depart):
    d = ouvrir(client, depart).json()
    r = etape(client, depart, d["id"], "transmission")
    assert r.status_code == 409 and r.json()["code"] == "etape_impossible"


def test_a_completer_puis_resoumis(client, depart):
    d = ouvrir(client, depart).json()
    r = etape(client, depart, d["id"], "verification", conforme=False, motif="Il manque l'attestation de départ")
    assert r.json()["statut"] == "a_completer"
    assert piece(client, depart, d["id"], nature="attestation_depart").status_code == 201
    r = etape(client, depart, d["id"], "resoumission", qui="drh")
    assert r.status_code == 201 and r.json()["statut"] == "resoumis"
    assert etape(client, depart, d["id"], "verification", conforme=True).json()["statut"] == "verifie"
    assert [e["etape"] for e in r.json()["evenements"]] == ["declare", "a_completer", "resoumis"]


def test_un_refus_se_motive_et_se_conteste(client, depart):
    t = jusqu_a_transmis(client, depart)
    sans = etape(client, depart, t["id"], "reponse", paye=False)
    assert sans.status_code == 422
    r = etape(client, depart, t["id"], "reponse", paye=False, motif="Pièce d'identité illisible", le="2020-02-20")
    assert r.json()["statut"] == "refuse"
    r = etape(client, depart, t["id"], "transmission", le="2020-02-25")
    assert r.json()["statut"] == "transmis" and r.json()["numero"] != t["numero"]


def test_un_retard_de_l_assureur_est_signale(client, depart):
    il_y_a_60_jours = (date.today() - timedelta(days=60)).isoformat()
    t = jusqu_a_transmis(client, depart, le=il_y_a_60_jours)
    assert [c["code"] for c in t["constats"]] == ["retard_assureur"]
    assert "30 jours" in t["constats"][0]["message"]


# --- Les pièces ------------------------------------------------------------------------

def test_les_pieces(client, depart):
    d = ouvrir(client, depart).json()
    assert piece(client, depart, d["id"], contenu=b"MZ\x90", nom="virus.exe").json()["code"] == "type_de_piece"
    assert piece(client, depart, d["id"], contenu=b"%PDF" + b"0" * (5 * 1024 * 1024)).json()["code"] == "piece_trop_lourde"
    ok = piece(client, depart, d["id"])
    assert ok.status_code == 201
    lu = client.get(u(depart, f"/dossiers/{d['id']}"), headers=en_tant_que(depart["drh"])).json()
    assert [(p["nature"], p["nom_fichier"]) for p in lu["pieces"]] == [("certificat_travail", "certificat.pdf")]
    telecharge = client.get(u(depart, f"/dossiers/{d['id']}/pieces/{lu['pieces'][0]['id']}"), headers=en_tant_que(depart["drh"]))
    assert telecharge.content == PDF_MINIMAL


# --- L'effacement ---------------------------------------------------------------------

def test_l_identite_est_effacee_douze_mois_apres_le_paiement(client, depart, bases):
    t = jusqu_a_transmis(client, depart, le="2020-01-20")
    etape(client, depart, t["id"], "reponse", paye=True, montant=3_625_000,
          le=(date.today() - relativedelta(months=12, days=1)).isoformat())
    lu = client.get(u(depart, f"/dossiers/{t['id']}"), headers=en_tant_que(depart["drh"])).json()
    assert lu["beneficiaire"] is None and lu["pieces"] == [] and lu["identite_effacee"]
    assert lu["evenements"][-1]["etape"] == "identite_effacee"
    with bases[0].connect() as c:
        for table in ("beneficiaires", "pieces_dossier"):
            assert c.execute(text(f"SELECT count(*) FROM {table} WHERE organisation_id = :o"), {"o": depart["org"]}).scalar() == 0
    # Le numéro se vérifie encore : le sceau ne portait aucune identité.
    assert client.get(f"{V1}/verifier/{t['numero']}").json()["authentique"]


def test_avant_douze_mois_rien_n_est_efface(client, depart):
    t = jusqu_a_transmis(client, depart)
    etape(client, depart, t["id"], "reponse", paye=True, montant=3_625_000,
          le=(date.today() - relativedelta(months=11)).isoformat())
    lu = client.get(u(depart, f"/dossiers/{t['id']}"), headers=en_tant_que(depart["drh"])).json()
    assert lu["beneficiaire"]["nom"] == "KOUASSI" and lu["efface_le"]


def test_l_effacement_programme_pour_tous_les_clients(client, depart, bases):
    from courtage.services.dossiers import effacer_echus_partout
    t = jusqu_a_transmis(client, depart, le="2020-01-20")
    etape(client, depart, t["id"], "reponse", paye=True, montant=3_625_000, le="2020-02-01")
    assert effacer_echus_partout(bases[1], date.today()) >= 1
    with bases[0].connect() as c:
        assert c.execute(text("SELECT count(*) FROM beneficiaires WHERE organisation_id = :o"), {"o": depart["org"]}).scalar() == 0


def test_un_depart_porte_par_un_dossier_ne_s_annule_pas(client, depart):
    ouvrir(client, depart)
    pid = depart["prestation"]["id"]
    r = client.post(u(depart, f"/prestations/{pid}/annulation"), json={"motif_correction": "x"}, headers=en_tant_que(depart["drh"]))
    assert r.status_code == 409 and r.json()["code"] == "dossier_ouvert"
    r = client.post(u(depart, f"/prestations/{pid}/correction"), headers=en_tant_que(depart["drh"]),
                    json={**DEPART, "date_depart": "2020-02-01", "motif_correction": "date"})
    assert r.status_code == 409
    # Corriger un montant reste possible : la clé ne bouge pas.
    r = client.post(u(depart, f"/prestations/{pid}/correction"), headers=en_tant_que(depart["drh"]),
                    json={**DEPART, "verse": 3_700_000, "motif_correction": "Versé corrigé"})
    assert r.status_code == 201


def test_les_dates_des_etapes(client, depart):
    d = ouvrir(client, depart).json()
    etape(client, depart, d["id"], "verification", conforme=True)
    demain = (date.today() + timedelta(days=1)).isoformat()
    assert etape(client, depart, d["id"], "transmission", le=demain).json()["code"] == "date_a_venir"
    assert etape(client, depart, d["id"], "transmission", le="2019-12-31").json()["code"] == "date_avant_depart"
    assert etape(client, depart, d["id"], "transmission", le="2020-02-01").status_code == 201
    r = etape(client, depart, d["id"], "reponse", paye=True, montant=1, le="2020-01-15")
    assert r.status_code == 422 and r.json()["code"] == "reponse_avant_envoi"


def test_sans_contrat_en_vigueur_les_departs_attendent(client, azito):
    """Les départs et les prises en charge s'ouvrent une fois le contrat d'assurance signé et en vigueur."""
    lire = lambda: client.get(u(azito, "/activation"), headers=en_tant_que(azito["drh"])).json()["capacites"]["departs"]
    assert lire() is False
    r = client.post(u(azito, "/prestations"), json=DEPART, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 409 and r.json()["code"] == "contrat_requis"
    # Un contrat de courtage sans assureur (le placement n'est pas fait) ne suffit pas.
    client.post(u(azito, "/contrats"), headers=en_tant_que(azito["conseiller"]),
                json={"en_vigueur_du": "2020-06-01", "service": "courtage", "mandat_reference": "Mandat"})
    assert lire() is False
    sous_contrat(client, azito)
    assert lire() is True
    assert client.post(u(azito, "/prestations"), json=DEPART, headers=en_tant_que(azito["drh"])).status_code == 201
