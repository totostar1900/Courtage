"""Simulation : la convention seule, le régime en vigueur et des variantes, côte à côte."""
import pytest
from sqlalchemy import text

from tests.outils import AZITO, V1, deposer, en_tant_que, fichier_azito
from tests.test_regime import AVARE, CADRES, CCI, adopter, categorie, regime

UNIFORME = {"forme": "tranches_cumulatives", "tranches": [
    {"jusqu_a": 5, "mois_par_annee": 0.45}, {"jusqu_a": 10, "mois_par_annee": 0.525},
    {"jusqu_a": None, "mois_par_annee": 0.60}]}


def simuler(client, a, variantes, qui="drh", fichier=None, **autres):
    corps = {"fichier_id": fichier or a["fichier"], "date_evaluation": "2019-12-31", "convention_code": "CI_CCI",
             "fonds_disponible": AZITO["fonds_disponible"], "variantes": variantes, **autres}
    return client.post(f"{V1}/organisations/{a['org']}/simulations", json=corps, headers=en_tant_que(a[qui]))


def test_la_convention_seule_puis_les_variantes(client, azito):
    v = regime(client, azito, [categorie("Cadre", CADRES), categorie("*", CCI)])
    adopter(client, azito, v["id"])
    f = deposer(client, azito["org"], azito["drh"], fichier_azito(categories={i: "Cadre" for i in range(5)}))["id"]
    r = simuler(client, azito, [
        {"nom": "Accord en vigueur", "regime_version_id": v["id"]},
        {"nom": "+50 % pour tous", "categories": [categorie("*", UNIFORME)]},
    ], fichier=f)
    assert r.status_code == 200, r.text
    base, accord, uniforme = r.json()["resultats"]
    assert base["nom"] == "Convention seule"
    assert base["ecart_convention"] == 0
    assert base["totaux"]["dette"] == pytest.approx(60_130_415, rel=1e-5)
    for s in (accord, uniforme):
        assert s["ecart_convention"] == s["totaux"]["dette"] - base["totaux"]["dette"] > 0
        assert s["cotisation_initiale"] == max(s["totaux"]["dette"] - AZITO["fonds_disponible"], 0)
        assert sum(x["effectif"] for x in s["echeancier"]) == 23
        assert 0 < s["part_cinq_premiers"] < 1
        assert s["constats"] == []
    assert set(accord["par_categorie"]) == {"Cadre", "Employé"}
    assert 0 <= uniforme["concentration"]["part_des_mieux_payes"] <= 1
    assert base["concentration"] is None                  # la convention n'ajoute rien à elle-même


def test_une_variante_sous_le_plancher_est_calculee_au_plancher_et_signalee(client, azito):
    base, avare = simuler(client, azito, [{"nom": "Avare", "categories": [categorie("*", AVARE)]}]).json()["resultats"]
    assert avare["totaux"]["dette"] == base["totaux"]["dette"]
    [c] = avare["constats"]
    assert c["code"] == "sous_le_plancher" and c["details"]["anciennetes"][0] == 1


def test_une_variante_qui_ne_couvre_pas_le_personnel_n_empeche_pas_les_autres(client, azito):
    base, cadres, tous = simuler(client, azito, [
        {"nom": "Cadres seuls", "categories": [categorie("Cadre", CADRES)]},
        {"nom": "Tous", "categories": [categorie("*", UNIFORME)]},
    ]).json()["resultats"]
    assert cadres["erreur"]["code"] == "categories_inconnues"
    assert "totaux" in tous


def test_les_hypotheses_se_changent_sans_justification(client, azito):
    """Une simulation n'engage personne : l'écart au référentiel n'y demande pas de justification."""
    bas = simuler(client, azito, [], hypotheses={"taux_actualisation": 0.025}).json()["resultats"][0]
    normal = simuler(client, azito, []).json()["resultats"][0]
    assert bas["totaux"]["dette"] > normal["totaux"]["dette"]


def test_rien_n_est_enregistre(client, azito, bases):
    def compter():
        with bases[0].connect() as c:
            return c.execute(text("SELECT (SELECT count(*) FROM etudes), (SELECT count(*) FROM regimes_versions)")).one()
    avant = compter()
    simuler(client, azito, [{"nom": "Idée", "categories": [categorie("*", UNIFORME)]}])
    assert compter() == avant


@pytest.mark.parametrize("variantes,code", [
    ([{"nom": "Ailleurs", "categories": [{**categorie("*", CCI), "convention_code": "CM_COMMERCE"}]}], "convention_autre_pays"),
    ([{"nom": "Les deux", "regime_version_id": "00000000-0000-0000-0000-000000000000",
       "categories": [categorie("*", CCI)]}], "variante_ambigue"),
    ([{"nom": f"V{i}", "categories": [categorie("*", CCI)]} for i in range(7)], "trop_de_variantes"),
])
def test_saisies_refusees(client, azito, variantes, code):
    r = simuler(client, azito, variantes)
    assert r.status_code == 422 and r.json()["code"] == code


def test_l_expert_comptable_peut_simuler(client, azito, personnes):
    client.post(f"{V1}/organisations/{azito['org']}/adhesions", json={"utilisateur_id": str(personnes["etranger"]),
                                                                      "role": "lecteur_client"},
                headers=en_tant_que(personnes["admin"]))
    assert simuler(client, azito, [], qui="etranger").status_code == 200
