"""Les hypothèses réglables : bornes, rotation par tranche d'âge, frais, table, et ce qu'en dit le rapport."""
import pytest

from courtage.erreurs import ErreurMetier
from courtage.services import hypotheses as hyp
from tests.outils import V1, etude

TRANCHES = [{"des": 18, "taux": 0.06}, {"des": 30, "taux": 0.03}, {"des": 45, "taux": 0.0}]


def test_la_rotation_par_tranche_s_applique_age_par_age():
    t = hyp.turnover({"age_retraite": 60, "taux_turnover": 0.02, "rotation_par_age": TRANCHES})
    assert (t[18], t[29], t[30], t[44], t[45], t[59]) == (0.06, 0.06, 0.03, 0.03, 0.0, 0.0)
    assert 60 not in t and 17 not in t
    assert set(hyp.turnover({"age_retraite": 60, "taux_turnover": 0.02}).values()) == {0.02}


def test_la_rotation_moyenne_suit_la_population():
    v = {"age_retraite": 60, "taux_turnover": 0.02, "rotation_par_age": TRANCHES}
    assert hyp.taux_moyen(v, [25.4, 35, 50]) == pytest.approx(0.03)
    assert hyp.taux_moyen({"taux_turnover": 0.02}, [25]) == 0.02


@pytest.mark.parametrize("saisie, code", [
    ({"taux_actualisation": 0.4}, "hypothese_hors_bornes"),
    ({"frais_sur_cotisation": -0.01}, "hypothese_hors_bornes"),
    ({"age_retraite": 60.5}, "hypothese_invalide"),
    ({"table": "TV_INCONNUE"}, "table_indisponible"),
    ({"rotation_par_age": [{"des": 25, "taux": 0.05}]}, "rotation_invalide"),
    ({"rotation_par_age": [{"des": 18, "taux": 0.05}, {"des": 18, "taux": 0.02}]}, "rotation_invalide"),
    ({"rotation_par_age": [{"des": 18, "taux": 0.05}, {"des": 62, "taux": 0.02}]}, "rotation_invalide"),
    ({"rotation_par_age": [{"des": 18, "taux": 0.9}]}, "rotation_invalide"),
    ({"mortalite": "x"}, "hypothese_inconnue"),
])
def test_une_saisie_hors_des_bornes_est_refusee(saisie, code):
    with pytest.raises(ErreurMetier) as e:
        hyp.valeurs_et_ecarts(saisie)
    assert e.value.code == code


def test_les_ecarts_se_lisent_contre_le_referentiel():
    valeurs, ecarts = hyp.valeurs_et_ecarts({"rotation_par_age": TRANCHES, "frais_sur_cotisation": 0.04})
    assert valeurs["rotation_par_age"] == TRANCHES and valeurs["frais_sur_cotisation"] == 0.04
    assert ecarts == [{"champ": "rotation_par_age", "referentiel": None, "retenu": TRANCHES}]
    valeurs, ecarts = hyp.valeurs_et_ecarts({"rotation_par_age": []})
    assert "rotation_par_age" not in valeurs and ecarts == []


def test_le_catalogue_dit_la_table_masculine_a_venir(client):
    c = client.get(f"{V1}/referentiel/hypotheses").json()
    assert c["defauts"]["taux_actualisation"] == 0.035 and c["defauts"]["rotation_par_age"] is None
    assert {x["champ"] for x in c["champs"]} >= {"taux_actualisation", "rotation_par_age", "frais_sur_cotisation"}
    taux = next(x for x in c["champs"] if x["champ"] == "taux_actualisation")
    assert "valeur d'aujourd'hui" in taux["role"] and "{effet}" in taux["effet"]
    assert [t["disponible"] for t in c["tables"]] == [True, False]


def test_une_etude_par_tranche_d_age_et_ses_frais(client, azito):
    base = etude(client, azito).json()
    r = etude(client, azito, hypotheses={"rotation_par_age": TRANCHES, "frais_sur_cotisation": 0.02},
              justification="Départs observés par âge, contrat à 2 %")
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["hypotheses"]["valeurs"]["rotation_par_age"] == TRANCHES
    assert {x["champ"] for x in e["hypotheses"]["ecarts"]} == {"rotation_par_age", "frais_sur_cotisation"}
    assert e["totaux"]["dette"] != base["totaux"]["dette"]
    assert abs(e["totaux"]["cotisation_totale"] - e["totaux"]["cotisation_nette"] * 1.02) <= 2
    s = e["sensibilites"]
    assert s["rotation_plus_1pt"]["dette"] < e["totaux"]["dette"] < s["rotation_moins_1pt"]["dette"]
    assert s["croissance_salaires_moins_1pt"]["dette"] < e["totaux"]["dette"]


def test_le_lecteur_lit_chaque_hypothese_avec_son_effet():
    valeurs, ecarts = hyp.valeurs_et_ecarts({"rotation_par_age": TRANCHES})
    sens = {"taux_actualisation_moins_1pt": {"dette": 1120}, "croissance_salaires_plus_1pt": {"dette": 1100},
            "rotation_plus_1pt": {"dette": 950}}
    lignes = {l["champ"]: l for l in hyp.pour_le_lecteur(valeurs, ecarts, sens, 1000)}
    assert "1 point de moins augmente la dette de 12 %" in lignes["taux_actualisation"]["effet"]
    assert lignes["taux_actualisation"]["defaut"] == "3,5 %" and not lignes["taux_actualisation"]["ecarte"]
    assert lignes["taux_turnover"]["ecarte"] and "dès 30 ans : 3 %" in lignes["taux_turnover"]["retenu"]
    assert "{effet}" not in lignes["croissance_salaires"]["effet"]
