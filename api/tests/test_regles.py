"""Moteur par catégorie : barème, plancher, ancienneté minimale, plafond, arrondi."""
import io
from dataclasses import replace
from datetime import datetime

import openpyxl
import pytest

from courtage.actuariat.ifc import CategorieInconnue, Regles, evaluer, mois_dus
from courtage.fichier import lire_fichier, salaries as salaries_du_fichier
from courtage.referentiel import BaremeTranches
from tests.test_ifc import CI, hypotheses, salaries


def tranches(*taux, bornes=(5, 10)):
    b = list(bornes)[: len(taux) - 1] + [None]
    return BaremeTranches(forme="tranches_cumulatives",
                          tranches=[{"jusqu_a": x, "mois_par_annee": t} for x, t in zip(b, taux)])


PLANCHER_CI = Regles(bareme=CI.bareme)


# --- Règles d'une catégorie ---------------------------------------------------

def test_sans_regles_le_moteur_ne_change_pas():
    avant = evaluer(salaries(), hypotheses(), CI)
    avec = evaluer(salaries(), hypotheses(), CI, regles={"*": Regles(bareme=CI.bareme)})
    assert avec.totaux == avant.totaux


def test_le_plancher_joue_la_ou_il_est_plus_favorable():
    """35 % par an partout : au-dessus de la CCI jusqu'à 15 ans, en dessous ensuite."""
    regles = Regles(bareme=tranches(0.35), plancher=PLANCHER_CI)
    assert mois_dus(regles, 10) == (pytest.approx(3.5), False)
    assert mois_dus(regles, 20) == (pytest.approx(7.25), True)   # la CCI : 1,5 + 1,75 + 10 × 0,40


def test_la_dette_d_un_regime_sous_le_plancher_est_au_moins_la_dette_conventionnelle():
    conventionnelle = evaluer(salaries(), hypotheses(), CI).totaux.dette
    bas = evaluer(salaries(), hypotheses(), CI, regles={"*": Regles(bareme=tranches(0.10), plancher=PLANCHER_CI)})
    assert bas.totaux.dette == conventionnelle
    assert all(l.plancher_applique for l in bas.lignes if l.ifc > 0)


def test_anciennete_minimale():
    """Industries de transformation (Cameroun) : rien avant 5 ans de présence."""
    regles = Regles(bareme=tranches(0.5), anciennete_minimale=5)
    assert mois_dus(regles, 4.9)[0] == 0
    assert mois_dus(regles, 5)[0] == pytest.approx(2.5)


def test_une_condition_plus_stricte_que_la_convention_ne_prive_pas_du_plancher():
    regles = Regles(bareme=tranches(0.5), anciennete_minimale=10, plancher=PLANCHER_CI)
    mois, plancher = mois_dus(regles, 6)
    assert plancher and mois == pytest.approx(1.5 + 0.35)


def test_plafond_en_mois():
    """Industries de transformation : un demi-mois par année, seize mois au plus."""
    regles = Regles(bareme=tranches(0.5), plafond_mois=16)
    assert mois_dus(regles, 30)[0] == 15
    assert mois_dus(regles, 40)[0] == 16


def test_arrondi_au_mois():
    annees = Regles(bareme=tranches(0.3))
    mois = Regles(bareme=tranches(0.3), arrondi="mois")
    assert mois_dus(annees, 4.99)[0] == pytest.approx(4 * 0.3)
    assert mois_dus(mois, 4.99)[0] == pytest.approx(59 / 12 * 0.3)


# --- Catégories ---------------------------------------------------------------

def _par_categorie():
    """Les cinq premiers salariés d'AZITO en cadres, les autres en employés."""
    return [replace(s, categorie="cadre" if i < 5 else "employe") for i, s in enumerate(salaries())]


def test_chaque_categorie_a_ses_regles():
    cadres = Regles(bareme=tranches(0.60, 0.70, 0.80), plancher=PLANCHER_CI)
    employes = Regles(bareme=CI.bareme, plancher=PLANCHER_CI)
    r = evaluer(_par_categorie(), hypotheses(), CI, regles={"cadre": cadres, "employe": employes})
    tout_ci = evaluer(_par_categorie(), hypotheses(), CI)
    assert r.totaux.dette > tout_ci.totaux.dette
    assert set(r.par_categorie) == {"cadre", "employe"}
    assert r.par_categorie["cadre"]["effectif"] == 5
    assert sum(c["dette"] for c in r.par_categorie.values()) == pytest.approx(r.totaux.dette, abs=2)
    employes_seuls = [l for l in r.lignes if l.categorie == "employe"]
    assert all(l.mois == next(x for x in tout_ci.lignes if x.matricule == l.matricule).mois for l in employes_seuls)


def test_une_categorie_sans_regle_est_refusee():
    with pytest.raises(CategorieInconnue, match="ouvrier"):
        evaluer([replace(salaries()[0], categorie="ouvrier")], hypotheses(), CI,
                regles={"cadre": Regles(bareme=CI.bareme)})


def test_la_regle_par_defaut_couvre_les_autres():
    r = evaluer(_par_categorie(), hypotheses(), CI, regles={"cadre": Regles(bareme=tranches(0.6)),
                                                             "*": Regles(bareme=CI.bareme)})
    assert r.par_categorie["employe"]["effectif"] == 18


# --- Le fichier porte la catégorie --------------------------------------------

def _xlsx(entete, lignes):
    wb = openpyxl.Workbook()
    wb.active.append(entete)
    for l in lignes:
        wb.active.append(l)
    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


@pytest.mark.parametrize("intitule", ["Catégorie", "Catégorie professionnelle", "Category", "Collège", "CSP"])
def test_la_categorie_est_lue(intitule):
    contenu = _xlsx(["Matricule", "Date de naissance", "Date d'embauche", "Salaire mensuel", intitule],
                    [["A1", datetime(1980, 5, 2), datetime(2010, 3, 1), 450000, " Cadre "]])
    lu = lire_fichier(contenu, "p.xlsx")
    assert lu.lignes[0].categorie == "Cadre"
    assert salaries_du_fichier(lu)[0].categorie == "Cadre"


def test_sans_colonne_categorie():
    contenu = _xlsx(["Matricule", "Date de naissance", "Date d'embauche", "Salaire mensuel"],
                    [["A1", datetime(1980, 5, 2), datetime(2010, 3, 1), 450000]])
    assert lire_fichier(contenu, "p.xlsx").lignes[0].categorie is None


def test_references_azito_intactes():
    """Le cas de référence ne bouge pas : 60 130 415 F sans catégorie ni règle."""
    assert evaluer(salaries(), hypotheses(), CI).totaux.dette == pytest.approx(60_130_415, rel=1e-5)
