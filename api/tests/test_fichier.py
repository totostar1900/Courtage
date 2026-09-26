"""Fichier du personnel : lecture (xlsx, csv) et contrôles de la spec §6."""
import io
import json
from datetime import date, datetime
from pathlib import Path

import openpyxl
import pytest

from courtage.actuariat.ifc import Hypotheses, evaluer
from courtage.fichier import (
    controler,
    controler_parametres,
    controler_resultat,
    lire_fichier,
    salaries,
)
from courtage.referentiel import charger_convention, charger_table

EVAL = date(2019, 12, 31)
AZITO = json.loads((Path(__file__).parent / "fixtures" / "azito_2019.json").read_text())


def xlsx(lignes: list[list], titre: str | None = None) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    if titre:
        ws.append([titre])
        ws.append([])
    for l in lignes:
        ws.append(l)
    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


def codes(anomalies, niveau=None):
    return [a.code for a in anomalies if niveau is None or a.niveau == niveau]


ENTETE = ["Matricule", "Nom et prénoms", "Sexe", "Date de naissance", "Date d'embauche", "Salaire brut mensuel"]


# --- Lecture ------------------------------------------------------------------

def test_lit_un_xlsx_avec_une_ligne_de_titre():
    contenu = xlsx([ENTETE, ["A1", "Ngo Bassa Marie", "F", datetime(1980, 5, 2), datetime(2010, 3, 1), 450000]],
                   titre="Personnel au 31/12/2019")
    lu = lire_fichier(contenu, "personnel.xlsx")
    assert codes(lu.anomalies, "bloquant") == []
    [l] = lu.lignes
    assert (l.matricule, l.sexe, l.naissance, l.embauche, l.salaire_annuel) == (
        "A1", "F", date(1980, 5, 2), date(2010, 3, 1), 5_400_000)
    assert l.numero == 4  # numéro de ligne tel que l'utilisateur le voit dans son tableur


def test_les_noms_ne_sont_jamais_lus():
    contenu = xlsx([ENTETE, ["A1", "Ngo Bassa Marie", "F", datetime(1980, 5, 2), datetime(2010, 3, 1), 450000]])
    lu = lire_fichier(contenu, "personnel.xlsx")
    assert "Nom et prénoms" in lu.colonnes_ignorees
    assert "Ngo Bassa" not in repr(lu)


def test_lit_un_csv_a_la_francaise():
    texte = (
        "Matricule;Date de naissance;Date d'embauche;Salaire annuel;Genre\n"
        "12;02/05/1980;01/03/2010;5 400 000;Femme\n"
        "13;1975-01-01;2011-01-01;1 250 000,40;H\n"
    )
    lu = lire_fichier(texte.encode("latin-1"), "export.csv")
    assert codes(lu.anomalies, "bloquant") == []
    assert [l.salaire_annuel for l in lu.lignes] == [5_400_000, 1_250_000]
    assert [l.sexe for l in lu.lignes] == ["F", "M"]
    assert lu.lignes[1].naissance == date(1975, 1, 1)


def test_intitules_anglais():
    contenu = xlsx([["Employee ID", "Birth date", "Hire date", "Monthly salary"],
                    ["E7", datetime(1985, 1, 9), datetime(2015, 6, 1), 300000]])
    lu = lire_fichier(contenu, "staff.xlsx")
    assert codes(lu.anomalies, "bloquant") == []
    assert lu.lignes[0].salaire_annuel == 3_600_000


def test_periodicite_donnee_par_l_utilisateur_quand_l_intitule_se_tait():
    contenu = xlsx([["Matricule", "Date de naissance", "Date d'embauche", "Salaire"],
                    ["A1", datetime(1980, 5, 2), datetime(2010, 3, 1), 450000]])
    assert "periodicite_inconnue" in codes(lire_fichier(contenu, "p.xlsx").anomalies, "bloquant")
    lu = lire_fichier(contenu, "p.xlsx", periodicite="mensuel")
    assert lu.lignes[0].salaire_annuel == 5_400_000


def test_periodicite_contradictoire():
    contenu = xlsx([ENTETE, ["A1", "", "F", datetime(1980, 5, 2), datetime(2010, 3, 1), 450000]])
    assert "periodicite_contradictoire" in codes(lire_fichier(contenu, "p.xlsx", periodicite="annuel").anomalies)


def test_colonnes_obligatoires_introuvables():
    contenu = xlsx([["Matricule", "Service"], ["A1", "Compta"]])
    lu = lire_fichier(contenu, "p.xlsx")
    [a] = [a for a in lu.anomalies if a.code == "colonnes_introuvables"]
    assert a.niveau == "bloquant"
    assert "date de naissance" in a.message


def test_date_illisible_et_annee_a_deux_chiffres():
    texte = "Matricule;Date de naissance;Date d'embauche;Salaire mensuel\n1;31/02/1980;01/03/2010;100000\n2;02/05/80;01/03/2010;100000\n"
    lu = lire_fichier(texte.encode(), "p.csv")
    assert [(a.code, a.ligne) for a in lu.anomalies if a.code == "date_illisible"] == [
        ("date_illisible", 2), ("date_illisible", 3)]


def test_lignes_vides_ignorees():
    contenu = xlsx([ENTETE, ["A1", "", "F", datetime(1980, 5, 2), datetime(2010, 3, 1), 450000], [None] * 6, []])
    assert len(lire_fichier(contenu, "p.xlsx").lignes) == 1


def test_format_non_pris_en_charge():
    lu = lire_fichier(b"%PDF-1.7", "personnel.pdf")
    assert codes(lu.anomalies, "bloquant") == ["format_non_pris_en_charge"]


# --- Contrôles des lignes -----------------------------------------------------

def lire(*lignes):
    return lire_fichier(xlsx([ENTETE, *lignes]), "p.xlsx")


def test_champs_manquants():
    lu = lire([None, "", "F", datetime(1980, 5, 2), None, 450000])
    anomalies = controler(lu, date_evaluation=EVAL, age_retraite=60)
    assert sorted((a.code, a.colonne) for a in anomalies if a.code == "champ_manquant") == [
        ("champ_manquant", "date d'embauche"), ("champ_manquant", "matricule")]


def test_matricule_en_double():
    l = ["A1", "", "F", datetime(1980, 5, 2), datetime(2010, 3, 1), 450000]
    anomalies = controler(lire(l, l), date_evaluation=EVAL, age_retraite=60)
    assert codes(anomalies, "bloquant") == ["matricule_double"]


@pytest.mark.parametrize("naissance,embauche,salaire,code", [
    (datetime(1980, 5, 2), datetime(2020, 3, 1), 450000, "embauche_apres_evaluation"),
    (datetime(2000, 5, 2), datetime(2010, 3, 1), 450000, "age_embauche_trop_bas"),
    (datetime(1920, 5, 2), datetime(1950, 3, 1), 450000, "naissance_improbable"),
    (datetime(1980, 5, 2), datetime(2010, 3, 1), 0, "salaire_invalide"),
    (datetime(1980, 5, 2), datetime(2010, 3, 1), -5, "salaire_invalide"),
])
def test_controles_bloquants(naissance, embauche, salaire, code):
    anomalies = controler(lire(["A1", "", "F", naissance, embauche, salaire]), date_evaluation=EVAL, age_retraite=60)
    assert code in codes(anomalies, "bloquant")


def test_salarie_au_dela_de_la_retraite_est_un_avertissement():
    anomalies = controler(lire(["43", "", "M", datetime(1955, 12, 4), datetime(2013, 5, 13), 3682665]),
                          date_evaluation=EVAL, age_retraite=60)
    assert codes(anomalies, "bloquant") == []
    assert codes(anomalies, "avertissement") == ["au_dela_de_la_retraite"]


def test_dates_au_premier_janvier_en_serie():
    lignes = [[f"A{i}", "", "F", datetime(1970 + i, 1, 1), datetime(2005, 1, 1), 300000] for i in range(3)]
    lignes.append(["B", "", "F", datetime(1981, 7, 9), datetime(2005, 1, 1), 300000])
    anomalies = controler(lire(*lignes), date_evaluation=EVAL, age_retraite=60)
    [a] = [a for a in anomalies if a.code == "dates_estimees"]
    assert a.niveau == "avertissement" and "3" in a.message


# --- Contrôles des paramètres et du résultat ----------------------------------

def test_date_d_evaluation_fin_de_mois():
    assert codes(controler_parametres(date_evaluation=date(2019, 12, 30), date_donnees=date(2019, 12, 30)),
                 "bloquant") == ["date_evaluation_pas_fin_de_mois"]
    assert controler_parametres(date_evaluation=date(2024, 2, 29), date_donnees=date(2024, 2, 1)) == []


def test_donnees_de_plus_de_douze_mois():
    """Le rapport AZITO « 2023 » reposait sur des données de 2019."""
    anomalies = controler_parametres(date_evaluation=date(2022, 12, 31), date_donnees=date(2019, 12, 31))
    assert codes(anomalies, "bloquant") == ["donnees_trop_anciennes"]


def test_poids_d_un_salarie_dans_l_engagement():
    h = Hypotheses(date_evaluation=EVAL, taux_actualisation=0.035, croissance_salaires=0.02, inflation=0,
                   age_retraite=60, turnover={a: 0.02 for a in range(18, 61)}, table=charger_table("TV_CIMA_F"))
    lu = lire_fichier(xlsx([["Matricule", "Date de naissance", "Date d'embauche", "Salaire annuel"]] + [
        [s["matricule"], datetime.fromisoformat(s["naissance"]), datetime.fromisoformat(s["embauche"]), s["salaire_annuel"]]
        for s in AZITO["salaries"]]), "azito.xlsx")
    r = evaluer(salaries(lu), h, charger_convention("CI_CCI"))
    [a] = controler_resultat(r)
    assert (a.code, a.niveau) == ("poids_excessif", "avertissement")
    assert "SANS-MATRICULE" in a.message and "26" in a.message


# --- De bout en bout ----------------------------------------------------------

def test_le_fichier_azito_relu_redonne_la_meme_dette():
    """Un fichier tel qu'une DRH l'enverrait, avec des noms, redonne la dette du moteur."""
    entete = ["N°", "Nom", "Prénom", "Né(e) le", "Date d'entrée", "Salaire brut annuel (FCFA)"]
    corps = [[s["matricule"], "Nom", "Prénom", datetime.fromisoformat(s["naissance"]),
              datetime.fromisoformat(s["embauche"]), s["salaire_annuel"]] for s in AZITO["salaries"]]
    lu = lire_fichier(xlsx([entete, *corps], titre="AZITO — état du personnel"), "azito.xlsx")
    assert codes(lu.anomalies, "bloquant") == []
    assert codes(controler(lu, date_evaluation=EVAL, age_retraite=60), "bloquant") == []
    h = Hypotheses(date_evaluation=EVAL, taux_actualisation=0.035, croissance_salaires=0.02, inflation=0,
                   age_retraite=60, turnover={a: 0.02 for a in range(18, 61)}, table=charger_table("TV_CIMA_F"))
    assert evaluer(salaries(lu), h, charger_convention("CI_CCI")).totaux.dette == pytest.approx(60_130_415, rel=1e-5)


def test_deux_colonnes_de_salaire_la_premiere_est_retenue_et_on_le_dit():
    contenu = xlsx([["Matricule", "Date de naissance", "Date d'embauche", "Salaire de base mensuel", "Salaire brut mensuel"],
                    ["A1", datetime(1980, 5, 2), datetime(2010, 3, 1), 400000, 450000]])
    lu = lire_fichier(contenu, "p.xlsx")
    assert lu.lignes[0].salaire_annuel == 4_800_000
    assert codes(lu.anomalies, "avertissement") == ["colonne_en_double"]


def test_csv_windows_non_utf8():
    texte = "Matricule;Né le;Date d'entrée;Salaire mensuel\n1;02/05/1980;01/03/2010;100000\n"
    lu = lire_fichier(texte.encode("cp1252"), "p.csv")
    assert codes(lu.anomalies, "bloquant") == []
    assert lu.lignes[0].naissance == date(1980, 5, 2)
