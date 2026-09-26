"""P5 : l'expérience réelle — attendu contre réel, rotation observée (proposée, jamais appliquée), historique publiable."""
import json
from datetime import date

from courtage.experience import (Depart, attendu_contre_reel, delais_constates, historique_publiable,
                                 paiements_du_fonds, rotation_observee)

D = date(2025, 12, 31)


def dep(annee, motif="retraite", du=1_000_000, paye=None, le=None, m="X"):
    return Depart(matricule=m, date_depart=date(annee, 6, 30), motif=motif, du=du, verse=du, paye=paye, payee_le=le)


def test_attendu_contre_reel():
    echeancier = [{"annee": 2023, "effectif": 2, "prestations_probables": 1_800_000},
                  {"annee": 2024, "effectif": 1, "prestations_probables": 900_000},
                  {"annee": 2025, "effectif": 3, "prestations_probables": 2_700_000}]
    lignes = attendu_contre_reel([dep(2023), dep(2025, du=2_000_000), dep(2025, motif="demission")], echeancier, D, 2022)
    assert lignes == [
        {"annee": 2023, "attendu_retraites": 2, "attendu_prestations": 1_800_000, "reel_retraites": 1, "reel_du": 1_000_000, "reel_verse": 1_000_000},
        {"annee": 2024, "attendu_retraites": 1, "attendu_prestations": 900_000, "reel_retraites": 0, "reel_du": 0, "reel_verse": 0},
        {"annee": 2025, "attendu_retraites": 3, "attendu_prestations": 2_700_000, "reel_retraites": 1, "reel_du": 2_000_000, "reel_verse": 2_000_000},
    ]


def test_sans_etude_precedente_le_reel_seul():
    lignes = attendu_contre_reel([dep(2022)], None, D, None)
    assert lignes == [{"annee": 2022, "attendu_retraites": None, "attendu_prestations": None, "reel_retraites": 1,
                       "reel_du": 1_000_000, "reel_verse": 1_000_000}]


def test_une_rotation_credible_et_differente_est_proposee():
    departs = [dep(a, "demission") for a in (2021, 2022, 2022, 2023, 2024, 2025)] + [dep(2024, "deces")]
    r = rotation_observee(departs, effectif=20, date_evaluation=D, taux_hypothese=0.02)
    # 6 démissions en 5 ans (2021-2025) pour 20 salariés : 6 %. Le décès ne compte pas.
    assert (r["departs"], r["annees"], r["taux"], r["credible"]) == (6, 5, 0.06, True)
    assert r["proposition"]["taux_turnover"] == 0.06 and "6 démissions et licenciements" in r["proposition"]["justification"]


def test_peu_de_departs_ne_prouvent_rien():
    r = rotation_observee([dep(2024, "demission"), dep(2025, "licenciement")], 20, D, 0.02)
    assert r["credible"] is False and r["proposition"] is None and "trop peu" in r["message"]


def test_une_hypothese_confirmee_n_est_pas_changee():
    departs = [dep(a, "demission") for a in (2021, 2022, 2023, 2024, 2025)]
    r = rotation_observee(departs, 50, D, 0.02)            # 5 / (5 × 50) = 2 %
    assert r["proposition"] is None and "tient" in r["message"]


def test_aucun_depart():
    assert rotation_observee([], 20, D, 0.02)["taux"] is None


def test_paiements_du_fonds_depuis_la_derniere_evaluation():
    departs = [dep(2023, paye=500, le=date(2023, 8, 1)), dep(2025, paye=700, le=date(2025, 9, 1)),
               dep(2025, paye=900, le=date(2026, 2, 1))]
    assert paiements_du_fonds(departs, date(2024, 12, 31), D) == 700
    assert paiements_du_fonds(departs, None, D) == 1200


def test_l_historique_publiable_regroupe_par_trois():
    departs = [dep(2021, du=1), dep(2022, du=2), dep(2022, du=3), dep(2023, du=4), dep(2024, du=5), dep(2025, du=6),
               dep(2025, motif="demission")]
    assert historique_publiable(departs, D) == [
        {"periode": "2021-2022", "retraites": 3, "du": 6, "paye": 0},
        {"periode": "2023-2025", "retraites": 3, "du": 15, "paye": 0}]


def test_moins_de_trois_retraites_rien_de_chiffre():
    assert historique_publiable([dep(2024, du=5_000_000), dep(2025)], D) == [
        {"periode": "—", "retraites": "<3", "du": None, "paye": None}]
    assert historique_publiable([], D) == []


def test_les_delais():
    assert delais_constates([20, 45]) is None
    assert delais_constates([20, 45, 30, 90]) == {"dossiers": 4, "median": 38, "max": 90}


# --- Dans l'étude et le cahier des charges ----------------------------------------------------

from datetime import timedelta  # noqa: E402

from tests.outils import AZITO, V1, en_tant_que, etude  # noqa: E402
from tests.test_prestations import DEPART  # noqa: E402


def declarer(client, a, **champs):
    r = client.post(f"{V1}/organisations/{a['org']}/prestations", json={**DEPART, **champs}, headers=en_tant_que(a["drh"]))
    assert r.status_code == 201, r.text


def test_une_etude_sans_depart_n_a_pas_d_experience(client, azito):
    assert etude(client, azito).json()["experience"] is None


def test_l_etude_lit_les_departs_a_sa_date(client, azito):
    for i, annee in enumerate((2016, 2017, 2018, 2018, 2019, 2019)):
        declarer(client, azito, matricule=f"D-{i}", motif="demission", date_embauche="2010-01-01", date_depart=f"{annee}-06-30")
    declarer(client, azito, matricule="R-1", date_depart="2019-03-31", date_embauche="1990-01-01", verse=5_000_000)
    e = etude(client, azito).json()
    x = e["experience"]
    assert x["etude_precedente"] is None
    assert x["attendu_contre_reel"] == [{"annee": 2019, "attendu_retraites": None, "attendu_prestations": None,
                                         "reel_retraites": 1, "reel_du": x["attendu_contre_reel"][0]["reel_du"],
                                         "reel_verse": 5_000_000}]
    r = x["rotation"]
    # 6 démissions de 2016 à 2019 (4 ans), 23 salariés : 6,5 %, contre 2 % supposés.
    assert (r["departs"], r["annees"], r["effectif"]) == (6, 4, len(AZITO["salaries"]))
    assert r["proposition"]["taux_turnover"] == round(6 / (4 * 23), 3)
    # Proposée, pas appliquée : l'hypothèse de l'étude reste celle du référentiel.
    assert e["hypotheses"]["valeurs"]["taux_turnover"] == 0.02


def test_un_parti_encore_dans_le_fichier_est_signale(client, azito):
    matricule = AZITO["salaries"][0]["matricule"]
    declarer(client, azito, matricule=matricule, date_embauche="1998-01-01", date_depart="2019-06-30")
    anomalies = etude(client, azito).json()["anomalies"]
    assert any(a["code"] == "parti_mais_dans_le_fichier" and matricule in a["message"] for a in anomalies)


def test_l_etude_precedente_donne_l_attendu(client, azito):
    ancienne = etude(client, azito, date_evaluation="2019-12-31").json()
    client.post(f"{V1}/organisations/{azito['org']}/etudes/{ancienne['id']}/emission", headers=en_tant_que(azito["conseiller"]))
    # La première année après 2019 où l'étude précédente prévoyait des retraites.
    prevu = next(a for a in ancienne["echeancier"] if a["annee"] > 2019)
    annee = prevu["annee"]
    declarer(client, azito, matricule="R-9", date_depart=f"{annee}-06-30", date_embauche="1990-01-01")
    deposer_a = f"{annee}-12-31"
    from tests.outils import deposer, fichier_azito
    azito = {**azito, "fichier": deposer(client, azito["org"], azito["drh"], fichier_azito(), date_donnees=deposer_a)["id"]}
    e = etude(client, azito, date_evaluation=deposer_a).json()
    ligne = next(l for l in e["experience"]["attendu_contre_reel"] if l["annee"] == annee)
    assert ligne["attendu_retraites"] == prevu["effectif"] and ligne["reel_retraites"] == 1
    assert e["experience"]["etude_precedente"] == {"date_evaluation": "2019-12-31"}


def test_le_cahier_des_charges_porte_l_historique_regroupe_sans_matricule(client, azito):
    from tests.test_fiche import fiche
    for i, (annee, du) in enumerate(((2015, 1), (2016, 1), (2017, 1), (2018, 1), (2019, 1))):
        declarer(client, azito, matricule=f"R-{i}", date_depart=f"{annee}-06-30", date_embauche="1990-01-01",
                 salaire_mensuel_reference=400_000 + i)
    e = etude(client, azito).json()
    client.post(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/emission", headers=en_tant_que(azito["conseiller"]))
    f = fiche(client, azito, e["id"])
    assert f.status_code == 201, f.text
    x = f.json()["contenu"]["experience"]
    assert [g["periode"] for g in x["historique"]] == ["2015-2019"]      # 5 retraites : un seul groupe de ≥ 3
    assert x["historique"][0]["retraites"] == 5 and x["delais"] is None
    assert "R-0" not in json.dumps(f.json()["contenu"])



def test_le_rapport_scelle_porte_l_experience(client, azito):
    import pymupdf
    for i, annee in enumerate((2016, 2017, 2018, 2018, 2019, 2019)):
        declarer(client, azito, matricule=f"D-{i}", motif="demission", date_embauche="2010-01-01", date_depart=f"{annee}-06-30")
    e = etude(client, azito).json()
    client.post(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/emission", headers=en_tant_que(azito["conseiller"]))
    pdf = client.get(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/rapport", headers=en_tant_que(azito["drh"])).content
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        texte = " ".join(p.get_text() for p in doc).replace("\n", " ")
    assert "L'expérience réelle" in texte and "Rotation observée 6,5 % par an" in texte
    assert "n'est pas appliquée à cette étude" in texte
