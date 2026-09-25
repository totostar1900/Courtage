"""Moteur IFC : tests de référence (cas AZITO) et tests unitaires."""
import json
from datetime import date
from pathlib import Path

import pytest

from courtage.actuariat.ifc import Hypotheses, Salarie, evaluer, mois_d_ifc
from courtage.referentiel import charger_convention, charger_table

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "azito_2019.json").read_text())
CI = charger_convention("CI_CCI")
APB = charger_convention("MG_APB")
TABLE = charger_table("TV_CIMA_F")


def salaries():
    return [
        Salarie(
            matricule=s["matricule"],
            naissance=date.fromisoformat(s["naissance"]),
            embauche=date.fromisoformat(s["embauche"]),
            salaire_annuel=s["salaire_annuel"],
        )
        for s in FIXTURE["salaries"]
    ]


def presences_du_classeur():
    return {s["matricule"]: s["presence_classeur"] for s in FIXTURE["salaries"]}


def hypotheses(**autres):
    base = dict(
        date_evaluation=date.fromisoformat(FIXTURE["date_evaluation"]),
        taux_actualisation=0.035,
        croissance_salaires=0.02,
        inflation=0.0,
        age_retraite=60,
        turnover={age: 0.02 for age in range(18, 61)},
        table=TABLE,
        fonds_disponible=FIXTURE["fonds_disponible"],
        frais_sur_cotisation=0.04,
    )
    base.update(autres)
    return Hypotheses(**base)


def assert_proche(obtenu: int, attendu: int, tolerance=1e-4):
    if attendu == 0:
        assert obtenu == 0
    else:
        assert abs(obtenu - attendu) / attendu < tolerance, f"{obtenu} ≠ {attendu}"


# --- Références ---------------------------------------------------------------

def test_reproduit_le_classeur_ariane_convention_ci():
    r = evaluer(salaries(), hypotheses(), CI, presences=presences_du_classeur())
    attendu = FIXTURE["attendu"]["classeur_ci"]
    assert_proche(r.totaux.vapf, attendu["vapf"])
    assert_proche(r.totaux.dette, attendu["dette"])
    assert_proche(r.totaux.charge, attendu["charge"])
    assert_proche(r.totaux.cotisation_totale, attendu["cotisation_totale"], tolerance=1e-3)


def test_reproduit_le_rapport_2023_avec_le_bareme_de_madagascar():
    """Le rapport remis à AZITO a été calculé avec le mauvais barème."""
    r = evaluer(salaries(), hypotheses(), APB, presences=presences_du_classeur())
    attendu = FIXTURE["attendu"]["rapport_2023_apb"]
    assert_proche(r.totaux.vapf, attendu["vapf"])
    assert_proche(r.totaux.dette, attendu["dette"])
    assert_proche(r.totaux.charge, attendu["charge"])
    assert r.totaux.cotisation_totale == 0


def test_presence_calculee_depuis_le_turnover():
    """Sans les valeurs collées du classeur, la présence vient du turnover."""
    r = evaluer(salaries(), hypotheses(), CI)
    assert_proche(r.totaux.dette, 60_130_415, tolerance=1e-5)
    un = next(l for l in r.lignes if l.matricule == "3")  # 50,6 ans : turnover de 50 à 59 ans, 10 années
    assert un.probabilite_presence == pytest.approx(0.98 ** 10, rel=1e-9)


def test_totaux_entiers_et_detail_par_salarie():
    r = evaluer(salaries(), hypotheses(), CI)
    assert len(r.lignes) == 23
    for champ in ("vapf", "dette", "charge", "cotisation_nette", "cotisation_totale"):
        assert isinstance(getattr(r.totaux, champ), int)
    assert r.totaux.dette == round(sum(l.dette for l in r.lignes))


# --- Cas particuliers ---------------------------------------------------------

def test_salarie_au_dela_de_l_age_de_retraite():
    """Matricule 43 : 64 ans, IFC due en entier, sans actualisation ni charge."""
    r = evaluer(salaries(), hypotheses(), CI)
    l = next(l for l in r.lignes if l.matricule == "43")
    assert l.annees_restantes == 0
    assert l.au_dela_de_la_retraite
    assert l.dette == pytest.approx(l.ifc)
    assert l.charge == 0


def test_cotisation_nulle_quand_le_fonds_couvre():
    r = evaluer(salaries(), hypotheses(fonds_disponible=10**9), CI)
    assert r.totaux.cotisation_nette == 0
    assert r.totaux.cotisation_totale == 0


def test_cotisation_frais_compris():
    r = evaluer(salaries(), hypotheses(fonds_disponible=0), CI)
    assert r.totaux.cotisation_nette == round(r.totaux.dette_brute + r.totaux.charge_brute)
    assert r.totaux.cotisation_totale == round((r.totaux.dette_brute + r.totaux.charge_brute) * 1.04)


def test_la_dette_monte_quand_le_taux_baisse():
    bas = evaluer(salaries(), hypotheses(taux_actualisation=0.025), CI).totaux.dette
    haut = evaluer(salaries(), hypotheses(taux_actualisation=0.045), CI).totaux.dette
    assert bas > haut


# --- Barèmes ------------------------------------------------------------------

@pytest.mark.parametrize("anciennete,mois", [
    (0, 0), (3, 0.9), (5, 1.5), (8, 1.5 + 3 * 0.35), (10, 3.25), (21, 3.25 + 11 * 0.40),
])
def test_bareme_tranches_cumulatives_cote_d_ivoire(anciennete, mois):
    assert mois_d_ifc(CI.bareme, anciennete) == pytest.approx(mois)


@pytest.mark.parametrize("anciennete,mois", [
    (4, 0.8), (9, 1.8), (10, 3), (14, 3), (15, 4), (26, 7), (45, 10),
])
def test_bareme_paliers_madagascar(anciennete, mois):
    assert mois_d_ifc(APB.bareme, anciennete) == pytest.approx(mois)
