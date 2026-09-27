"""Ce que le rapport explique : synthèse et décision, pyramide, courbes de prestation, couverture par le fonds."""
import re
import xml.etree.ElementTree as ET

from courtage.services import graphiques, lecture
from tests.test_rapport import emettre, pages, rapport


def _svg_valide(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def test_la_pyramide_range_par_cinq_ans_et_retire_les_bouts_vides():
    lignes = [{"age": a, "anciennete": n} for a, n in [(23.5, 1), (31, 4.9), (34.9, 5), (47, 12), (61, 31)]]
    p = lecture.pyramide(lignes)
    assert p["ages"][0] == ("moins de 25 ans", 1)
    assert dict(p["ages"])["30-34 ans"] == 2 and p["ages"][-1] == ("60 ans et plus", 1)
    assert p["anciennetes"][:2] == [("moins de 5 ans", 2), ("5-9 ans", 1)]
    assert sum(n for _, n in p["ages"]) == sum(n for _, n in p["anciennetes"]) == 5
    assert lecture.pyramide([{"age": 40, "anciennete": 10}])["ages"] == [("40-44 ans", 1)]
    _svg_valide(p["svg_ages"])


def test_la_couverture_dit_quand_le_fonds_est_depasse():
    ech = [{"annee": 2026, "effectif": 1, "ifc": 12, "prestations_probables": 10},
           {"annee": 2028, "effectif": 2, "ifc": 40, "prestations_probables": 30},
           {"annee": 2040, "effectif": 1, "ifc": 70, "prestations_probables": 60}]
    c = lecture.couverture(ech, 35, 2025)
    assert c["epuisement"] == 2028
    assert c["proches"] == {"departs": 3, "montant": 40, "part": 0.4}
    assert lecture.couverture(ech, 1000, 2025)["epuisement"] is None
    assert lecture.couverture(ech, 0, 2025)["epuisement"] is None
    # Une étude d'avant les prestations probables se lit sur l'indemnité.
    assert lecture.couverture([{"annee": 2026, "effectif": 1, "ifc": 50}], 20, 2025)["epuisement"] == 2026
    racine = _svg_valide(c["svg_cumul"])
    assert "Fonds constitué" in "".join(racine.itertext())


def test_les_graphiques_sont_du_svg_bien_forme_sans_texte_colore():
    svgs = [graphiques.histogramme("Âges", [("30-34 ans", 3), ("35-39 ans", 0)]),
            graphiques.courbes("Mois", [("Régime", [(0, 0), (5, 2.5)]), ("Convention", [(0, 0), (5, 2)])],
                               reference="Convention"),
            graphiques.echeancier("Par année", [(2026, 5.0), (2027, 0.0)], fonds=3, cumul=True)]
    for svg in svgs:
        racine = _svg_valide(svg)
        # Le texte porte l'encre ou le gris, jamais la couleur d'une série.
        couleurs = {t.get("fill") for t in racine.iter("{http://www.w3.org/2000/svg}text")}
        assert couleurs <= {graphiques.ENCRE, graphiques.DISCRET}
    assert graphiques.haut_rond(83) == 100 and graphiques.haut_rond(0.7) == 0.8 and graphiques.haut_rond(0) == 1


def test_la_synthese_met_les_chiffres_en_phrases_et_nomme_la_decision():
    e = {"totaux": {"effectif": 40, "dette": 1_000_000, "charge": 100_000, "cotisation_nette": 600_000,
                    "cotisation_totale": 624_000},
         "fonds_disponible": 500_000, "date_evaluation": "2025-12-31",
         "sensibilites": {"taux_actualisation_moins_1pt": {"dette": 1_100_000}}}
    couv = {"epuisement": 2029, "proches": {"departs": 3, "montant": 250_000, "part": 0.25}}
    s = lecture.synthese(e, couv, avertissements=2)
    texte = " ".join(t for _, t in s["constats"])
    assert "1 000 000 F au 31/12/2025" in texte and "il manque 600 000 F" in texte
    assert "jusqu'en 2028" in texte and "10 % de plus" in texte
    assert any("Financement" in d for d in s["decisions"]) and any("2 points d'attention" in d for d in s["decisions"])
    rien = lecture.synthese({**e, "totaux": {**e["totaux"], "cotisation_nette": 0, "cotisation_totale": 0},
                             "fonds_disponible": 2_000_000}, {**couv, "epuisement": None}, avertissements=0)
    texte = " ".join(t for _, t in rien["constats"])
    assert "aucune cotisation d'ajustement n'est due" in texte and "couvre tous les départs" in texte
    assert not any("Financement" in d or "attention" in d for d in rien["decisions"])


def test_le_rapport_imprime_la_synthese_les_graphiques_et_la_note_de_methode(client, azito):
    e = emettre(client, azito)
    tout = re.sub(r"\s+", " ", "\n".join(pages(rapport(client, azito, e["id"]))))
    for attendu in ("Ce que l'entreprise doit aujourd'hui", "La décision à prendre", "Du chiffre à la cotisation",
                    "Âges", "Anciennetés", "Prestations probables, par année", "guide/methode"):
        assert attendu in tout, attendu
