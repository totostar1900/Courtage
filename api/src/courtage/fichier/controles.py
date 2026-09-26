"""Contrôles de la spec §6 : bloquants (l'étude ne sort pas) et avertissements."""
from calendar import monthrange
from collections import Counter
from datetime import date

from dateutil.relativedelta import relativedelta

from courtage.actuariat.ifc import Resultat, annees_entre

from .lecture import CHAMPS_OBLIGATOIRES, LIBELLES, Anomalie, Lecture

AGE_MIN_EMBAUCHE = 14
AGE_MAX_PLAUSIBLE = 80
FRAICHEUR_MOIS = 12
POIDS_MAX = 0.20
PART_DATES_ESTIMEES = 0.20


def controler(lecture: Lecture, *, date_evaluation: date, age_retraite: int) -> list[Anomalie]:
    """Contrôles ligne à ligne, et sur l'ensemble du fichier."""
    anomalies: list[Anomalie] = []
    attributs = {"matricule": "matricule", "naissance": "naissance", "embauche": "embauche", "salaire": "salaire_annuel"}

    for l in lecture.lignes:
        for champ in CHAMPS_OBLIGATOIRES:
            if getattr(l, attributs[champ]) is None:
                anomalies.append(Anomalie("bloquant", "champ_manquant", f"{LIBELLES[champ].capitalize()} manquant(e).",
                                          ligne=l.numero, colonne=LIBELLES[champ]))
        if l.salaire_annuel is not None and l.salaire_annuel <= 0:
            anomalies.append(Anomalie("bloquant", "salaire_invalide", "Le salaire doit être positif.",
                                      ligne=l.numero, colonne="salaire"))
        if l.naissance:
            age = annees_entre(l.naissance, date_evaluation)
            if not AGE_MIN_EMBAUCHE <= age <= AGE_MAX_PLAUSIBLE:
                anomalies.append(Anomalie("bloquant", "naissance_improbable",
                                          f"Âge de {age:.0f} ans à la date d'évaluation.",
                                          ligne=l.numero, colonne="date de naissance"))
            elif age >= age_retraite:
                anomalies.append(Anomalie("avertissement", "au_dela_de_la_retraite",
                                          f"{age:.1f} ans, au-delà de l'âge de départ ({age_retraite} ans) : "
                                          "son IFC est due, pas future.", ligne=l.numero))
        if l.embauche and l.embauche > date_evaluation:
            anomalies.append(Anomalie("bloquant", "embauche_apres_evaluation",
                                      "Embauché(e) après la date d'évaluation.",
                                      ligne=l.numero, colonne="date d'embauche"))
        if l.naissance and l.embauche and l.embauche < l.naissance + relativedelta(years=AGE_MIN_EMBAUCHE):
            anomalies.append(Anomalie("bloquant", "age_embauche_trop_bas",
                                      f"Embauché(e) avant {AGE_MIN_EMBAUCHE} ans.",
                                      ligne=l.numero, colonne="date d'embauche"))

    doublons = [m for m, n in Counter(l.matricule for l in lecture.lignes if l.matricule).items() if n > 1]
    for m in doublons:
        numeros = [str(l.numero) for l in lecture.lignes if l.matricule == m]
        anomalies.append(Anomalie("bloquant", "matricule_double",
                                  f"Matricule {m} présent plusieurs fois (lignes {', '.join(numeros)}).",
                                  colonne="matricule"))

    naissances = [l for l in lecture.lignes if l.naissance]
    premiers_janvier = [l for l in naissances if (l.naissance.month, l.naissance.day) == (1, 1)]
    if len(premiers_janvier) >= 3 and len(premiers_janvier) >= PART_DATES_ESTIMEES * len(naissances):
        anomalies.append(Anomalie("avertissement", "dates_estimees",
                                  f"{len(premiers_janvier)} salariés nés un 1er janvier : dates probablement "
                                  "estimées, à confirmer.", colonne="date de naissance"))
    return anomalies


def controler_parametres(*, date_evaluation: date, date_donnees: date) -> list[Anomalie]:
    """Paramètres de l'étude : la date d'évaluation et la fraîcheur des données."""
    anomalies: list[Anomalie] = []
    if date_evaluation.day != monthrange(date_evaluation.year, date_evaluation.month)[1]:
        anomalies.append(Anomalie("bloquant", "date_evaluation_pas_fin_de_mois",
                                  "La date d'évaluation doit être une fin de mois (une clôture)."))
    if date_donnees + relativedelta(months=FRAICHEUR_MOIS) < date_evaluation:
        anomalies.append(Anomalie("bloquant", "donnees_trop_anciennes",
                                  f"Données arrêtées au {date_donnees:%d/%m/%Y}, plus de {FRAICHEUR_MOIS} mois "
                                  f"avant la date d'évaluation ({date_evaluation:%d/%m/%Y})."))
    return anomalies


def controler_resultat(resultat: Resultat) -> list[Anomalie]:
    """Ce que le calcul révèle : un salarié qui pèse trop lourd dans l'engagement."""
    total = sum(l.vapf for l in resultat.lignes)
    if total <= 0:
        return []
    return [
        Anomalie("avertissement", "poids_excessif",
                 f"Le salarié {l.matricule} représente {round(100 * l.vapf / total)} % de l'engagement : "
                 "vérifier ses données et qu'il relève du régime.")
        for l in resultat.lignes
        if l.vapf / total > POIDS_MAX
    ]
