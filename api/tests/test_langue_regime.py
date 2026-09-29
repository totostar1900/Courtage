"""L'anglais de l'écran pour les hypothèses et le régime ; le français reste ce qui s'enregistre."""
import pytest

from courtage import langue
from courtage.services import hypotheses as hyp
from courtage.erreurs import ErreurMetier
from tests.outils import V1, en_tant_que
from tests.test_regime import AVARE, adopter, categorie, regime

EN = {"X-Langue": "en"}


def test_les_hypotheses_s_expliquent_en_anglais(client):
    fr = client.get(f"{V1}/referentiel/hypotheses").json()
    en = client.get(f"{V1}/referentiel/hypotheses", headers=EN).json()
    champs_fr = {c["champ"]: c for c in fr["champs"]}
    champs_en = {c["champ"]: c for c in en["champs"]}
    assert champs_fr["taux_actualisation"]["libelle"] == "Taux d'actualisation"
    assert champs_en["taux_actualisation"]["libelle"] == "Discount rate"
    assert champs_en["taux_actualisation"]["role"].startswith("A benefit paid in 20 years")
    assert champs_en["taux_turnover"]["libelle"] == "Staff turnover"
    # Chaque texte de chaque hypothèse a son anglais, et les mêmes clés que le français.
    for champ, c in champs_en.items():
        assert set(c) == set(champs_fr[champ])
        for cle in ("libelle", "role", "effet", "fixer", "avec"):
            assert c[cle] and (c[cle] != champs_fr[champ][cle] or c[cle] == "Inflation"), (champ, cle)
    tables = {t["code"]: t for t in en["tables"]}
    assert tables["TV_CIMA_F"]["libelle"] == "CIMA F mortality table (women)"
    assert en["defauts"] == fr["defauts"]


def test_une_hypothese_hors_bornes_se_refuse_dans_la_langue_de_l_ecran():
    jeton = langue.definir("en")
    try:
        with pytest.raises(ErreurMetier) as e:
            hyp.lire("taux_actualisation", 0.5)
        assert e.value.message == "Discount rate: between -2% and 15%."
    finally:
        langue._langue.reset(jeton)
    with pytest.raises(ErreurMetier) as e:
        hyp.lire("taux_actualisation", 0.5)
    assert e.value.message == "Taux d'actualisation : entre -2 % et 15 %."


def test_le_rapport_garde_le_francais_l_ecran_suit_la_langue():
    valeurs = {"taux_actualisation": 0.035, "age_retraite": 60, "taux_turnover": 0.02, "table": "TV_CIMA_F"}
    jeton = langue.definir("en")
    try:
        scelle = hyp.pour_le_lecteur(valeurs, [], {}, None)
        ecran = hyp.pour_le_lecteur(valeurs, [], {}, None, ecran=True)
    finally:
        langue._langue.reset(jeton)
    assert scelle[0]["libelle"] == "Taux d'actualisation" and scelle[1]["retenu"] == "60 ans"
    assert ecran[0]["libelle"] == "Discount rate" and ecran[1]["retenu"] == "60 years"


def test_un_constat_du_regime_en_anglais_enregistre_en_francais(client, azito):
    r = client.post(f"{V1}/organisations/{azito['org']}/regimes", json={"nom": "R"},
                    headers={**en_tant_que(azito["drh"]), **EN})
    v = client.post(f"{V1}/organisations/{azito['org']}/regimes/{r.json()['id']}/versions",
                    headers={**en_tant_que(azito["drh"]), **EN}, json={
                        "en_vigueur_du": "2015-03-12", "fondement": "accord_entreprise",
                        "document_reference": "Accord", "categories": [categorie("*", AVARE)]}).json()
    [c] = v["constats"]
    assert c["code"] == "sous_le_plancher"
    assert c["message"].startswith("All staff: the plan gives less than") and "1 to 50 years" in c["message"]

    refus = client.post(f"{V1}/organisations/{azito['org']}/regimes/versions/{v['id']}/adoption",
                        headers={**en_tant_que(azito["drh"]), **EN}, json={"accepte_non_conformite": False})
    assert refus.status_code == 409
    assert refus.json()["message"].startswith("This plan gives less than the collective agreement")

    # Sans en-tête, le même constat se lit en français : l'enregistré n'a pas changé de langue.
    fr = regime(client, azito, [categorie("*", AVARE)], nom="R2")
    assert fr["constats"][0]["message"].startswith("Tout le personnel : le régime donne moins que")
    assert adopter(client, azito, fr["id"]).json()["message"].startswith("Ce régime donne moins")


def test_une_erreur_du_regime_en_anglais(client, azito):
    r = client.post(f"{V1}/organisations/{azito['org']}/regimes", json={"nom": "R"},
                    headers=en_tant_que(azito["drh"]))
    refus = client.post(f"{V1}/organisations/{azito['org']}/regimes/{r.json()['id']}/versions",
                        headers={**en_tant_que(azito["drh"]), **EN}, json={
                            "en_vigueur_du": "2015-03-12", "fondement": "accord_entreprise",
                            "document_reference": "Accord", "categories": []})
    assert refus.json()["code"] == "regime_sans_categorie"
    assert refus.json()["message"] == "A plan has at least one category (“*” for all staff)."
