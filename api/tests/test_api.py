"""API de l'étude IFC : le parcours complet, les refus d'émission, l'isolation, la rémunération."""
import pytest
from sqlalchemy import text

from tests.outils import AZITO, V1, codes, deposer, en_tant_que, etude, fichier_azito


# --- Parcours -----------------------------------------------------------------

def test_parcours_complet_du_depot_a_l_emission(client, azito, bases):
    a = azito
    r = etude(client, a)
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["statut"] == "brouillon"
    assert e["totaux"]["effectif"] == 23
    assert e["totaux"]["dette"] == pytest.approx(60_130_415, rel=1e-5)
    assert {"au_dela_de_la_retraite", "poids_excessif"} <= codes(e["anomalies"], "avertissement")
    assert e["emission"] == {"possible": True, "motifs": []}
    assert e["sensibilites"]["taux_actualisation_moins_1pt"]["dette"] > e["totaux"]["dette"]
    assert sum(an["effectif"] for an in e["echeancier"]) == 23

    # La DRH lance l'étude, elle ne l'émet pas.
    r = client.post(f"{V1}/organisations/{a['org']}/etudes/{e['id']}/emission", headers=en_tant_que(a["drh"]))
    assert r.status_code == 403

    r = client.post(f"{V1}/organisations/{a['org']}/etudes/{e['id']}/emission", headers=en_tant_que(a["conseiller"]))
    assert r.status_code == 200, r.text
    emise = r.json()
    assert emise["statut"] == "emise"
    assert emise["honoraires_ht"] == 750_000 + 23 * 2_000
    assert len(emise["empreinte"]) == 64

    # Émise : ni modifiée, ni supprimée, ni réémise.
    url = f"{V1}/organisations/{a['org']}/etudes/{e['id']}"
    assert client.put(url, json={"fichier_id": a["fichier"], "date_evaluation": "2019-12-31",
                                 "convention_code": "CI_CCI", "fonds_disponible": 0},
                      headers=en_tant_que(a["conseiller"])).json()["code"] == "etude_emise"
    assert client.delete(url, headers=en_tant_que(a["conseiller"])).status_code == 409
    assert client.post(f"{url}/emission", headers=en_tant_que(a["conseiller"])).status_code == 409

    # Relue, elle dit la même chose ; le journal a tout suivi.
    relue = client.get(url, headers=en_tant_que(a["drh"])).json()
    assert relue["empreinte"] == emise["empreinte"] and relue["statut"] == "emise"
    with bases[0].connect() as c:
        actions = set(c.execute(text("SELECT action FROM journal WHERE organisation_id = :o"), {"o": a["org"]}).scalars())
    assert {"remuneration.fixee", "fichier.depose", "etude.creee", "etude.emise"} <= actions


def test_le_fichier_depose_ne_garde_aucun_nom(client, azito, bases):
    with bases[0].connect() as c:
        lignes = c.execute(text("SELECT lignes::text FROM fichiers_personnel WHERE id = :f"), {"f": azito["fichier"]}).scalar_one()
    assert "Nom Prénom" not in lignes


def test_un_brouillon_se_recalcule_et_se_supprime(client, azito):
    a = azito
    e = etude(client, a).json()
    url = f"{V1}/organisations/{a['org']}/etudes/{e['id']}"
    r = client.put(url, headers=en_tant_que(a["conseiller"]), json={
        "fichier_id": a["fichier"], "date_evaluation": "2019-12-31", "convention_code": "CI_CCI",
        "fonds_disponible": 0})
    assert r.status_code == 200, r.text
    assert r.json()["totaux"]["cotisation_nette"] > 0
    assert client.delete(url, headers=en_tant_que(a["conseiller"])).status_code == 204
    assert client.get(url, headers=en_tant_que(a["conseiller"])).status_code == 404


# --- Refus d'émission : les leçons d'AZITO ------------------------------------

def test_le_bareme_d_un_autre_pays_ne_sort_pas(client, azito):
    """Le rapport AZITO 2023 : le barème des banques malgaches pour une société ivoirienne."""
    e = etude(client, azito, convention_code="MG_APB").json()
    # Présence calculée : 40 839 104 F (41 403 797 F avec les présences collées du classeur).
    assert e["totaux"]["dette"] == pytest.approx(40_839_104, rel=1e-5)
    assert "pays_different" in e["emission"]["motifs"]
    r = client.post(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/emission",
                    headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 409
    assert r.json()["code"] == "emission_refusee"
    assert "pays_different" in r.json()["details"]["motifs"]


def test_des_donnees_de_2019_ne_font_pas_une_etude_2022(client, azito):
    e = etude(client, azito, date_evaluation="2022-12-31").json()
    assert "donnees_trop_anciennes" in e["emission"]["motifs"]


def test_une_anomalie_bloquante_du_fichier_empeche_l_emission(client, azito):
    f = deposer(client, azito["org"], azito["drh"], fichier_azito(doublon=True))
    e = etude(client, {**azito, "fichier": f["id"]}).json()
    assert "matricule_double" in e["emission"]["motifs"]


def test_sans_conditions_de_remuneration_pas_d_emission(client, personnes):
    org = client.post(f"{V1}/organisations", json={"nom": "Sans contrat", "pays": "CI"},
                      headers=en_tant_que(personnes["admin"])).json()["id"]
    client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": str(personnes["conseiller"]),
                                                             "role": "conseiller"}, headers=en_tant_que(personnes["admin"]))
    f = deposer(client, org, personnes["conseiller"], fichier_azito())
    e = etude(client, {"org": org, "fichier": f["id"], **personnes}, qui="conseiller").json()
    assert "remuneration_absente" in e["emission"]["motifs"]


def test_ecart_avec_l_etude_precedente(client, azito):
    e = etude(client, azito).json()
    client.post(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/emission", headers=en_tant_que(azito["conseiller"]))
    suivante = etude(client, azito, qui="conseiller", date_evaluation="2020-12-31",
                     hypotheses={"taux_actualisation": 0.005}, justification="Taux de marché exceptionnellement bas").json()
    assert "ecart_etude_precedente" in codes(suivante["anomalies"], "avertissement")


# --- Hypothèses ---------------------------------------------------------------

def test_une_hypothese_hors_referentiel_demande_une_justification(client, azito):
    r = etude(client, azito, hypotheses={"taux_actualisation": 0.045})
    assert r.status_code == 422
    assert r.json()["code"] == "justification_requise"
    r = etude(client, azito, hypotheses={"taux_actualisation": 0.045}, justification="Courbe OAT CEMAC 10 ans")
    assert r.status_code == 201
    [ecart] = r.json()["hypotheses"]["ecarts"]
    assert ecart == {"champ": "taux_actualisation", "referentiel": 0.035, "retenu": 0.045,
                     "justification": "Courbe OAT CEMAC 10 ans"}


# --- Rémunération -------------------------------------------------------------

def test_conditions_de_remuneration_lues_par_le_client(client, azito):
    """La commission est publiée au client : il lit ses conditions."""
    r = client.get(f"{V1}/organisations/{azito['org']}/remuneration", headers=en_tant_que(azito["drh"]))
    assert r.status_code == 200
    assert r.json()["en_vigueur"]["commission_bps"] == 1000


def test_seul_le_conseiller_fixe_la_remuneration(client, azito):
    r = client.post(f"{V1}/organisations/{azito['org']}/remuneration", headers=en_tant_que(azito["drh"]),
                    json={"en_vigueur_du": "2026-01-01", "mode": "honoraires", "honoraires_etude_ifc": 1})
    assert r.status_code == 403


def test_remuneration_incoherente_refusee(client, azito):
    r = client.post(f"{V1}/organisations/{azito['org']}/remuneration", headers=en_tant_que(azito["conseiller"]),
                    json={"en_vigueur_du": "2026-01-01", "mode": "commission", "honoraires_etude_ifc": 500_000,
                          "commission_bps": 1000})
    assert r.status_code == 422
    assert r.json()["code"] == "remuneration_incoherente"


def test_de_nouvelles_conditions_s_appliquent_a_partir_de_leur_date(client, azito):
    client.post(f"{V1}/organisations/{azito['org']}/remuneration", headers=en_tant_que(azito["conseiller"]),
                json={"en_vigueur_du": "2019-06-01", "mode": "honoraires", "honoraires_etude_ifc": 1_000_000})
    r = client.get(f"{V1}/organisations/{azito['org']}/remuneration", headers=en_tant_que(azito["drh"])).json()
    assert r["en_vigueur"]["honoraires_etude_ifc"] == 1_000_000
    assert len(r["historique"]) == 2


# --- Accès --------------------------------------------------------------------

def test_sans_identite_401(client, azito):
    assert client.get(f"{V1}/organisations/{azito['org']}/etudes").status_code == 401


def test_un_etranger_au_dossier_n_y_entre_pas(client, azito):
    e = etude(client, azito).json()
    r = client.get(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}", headers=en_tant_que(azito["etranger"]))
    assert r.status_code == 403


def test_l_administrateur_de_plateforme_ne_lit_pas_les_donnees_des_clients(client, azito):
    r = client.get(f"{V1}/organisations/{azito['org']}/etudes", headers=en_tant_que(azito["admin"]))
    assert r.status_code == 403


def test_une_etude_d_une_autre_organisation_est_introuvable(client, azito, personnes):
    """Même membre des deux organisations, on ne lit pas l'étude de l'une sous l'adresse de l'autre."""
    e = etude(client, azito).json()
    autre = client.post(f"{V1}/organisations", json={"nom": "Autre", "pays": "CM"},
                        headers=en_tant_que(personnes["admin"])).json()["id"]
    client.post(f"{V1}/organisations/{autre}/adhesions", json={"utilisateur_id": str(personnes["conseiller"]),
                                                               "role": "conseiller"}, headers=en_tant_que(personnes["admin"]))
    r = client.get(f"{V1}/organisations/{autre}/etudes/{e['id']}", headers=en_tant_que(personnes["conseiller"]))
    assert r.status_code == 404


def test_moi_liste_mes_organisations(client, azito):
    r = client.get(f"{V1}/moi", headers=en_tant_que(azito["drh"])).json()
    assert [(o["nom"], o["role"]) for o in r["organisations"]] == [("AZITO", "admin_client")]


def test_l_equipe_du_dossier(client, azito):
    r = client.get(f"{V1}/organisations/{azito['org']}/equipe", headers=en_tant_que(azito["drh"])).json()
    assert {(m["nom"], m["role"]) for m in r} == {("Conseiller", "conseiller"), ("Drh", "admin_client")}
    assert client.get(f"{V1}/organisations/{azito['org']}/equipe", headers=en_tant_que(azito["etranger"])).status_code == 403
