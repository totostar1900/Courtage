"""Les anomalies en anglais, à l'affichage.

Une anomalie naît en français et s'enregistre en français (le fichier déposé, les résultats d'une étude, que
l'empreinte scelle). Ce module inscrit dans `courtage.langue.TRADUCTIONS`, pour chaque code, le message français
tel que le code l'écrit (ses parties variables en groupes nommés) et son gabarit anglais ; `traduire` s'en sert
au moment de rendre la réponse. Un message qu'aucun motif ne reconnaît reste en français : jamais d'erreur.

Les nombres et les dates gardent leur écriture française (jj/mm/aaaa, espaces des milliers), sauf l'âge à virgule.
"""
import re
from courtage.langue import TRADUCTIONS, traduire

# Les intitulés de champ, tels que lecture.py et departs.py les écrivent.
_CHAMPS = {
    "matricule": "staff number",
    "date de naissance": "date of birth",
    "date d'embauche": "hire date",
    "salaire": "salary",
    "sexe": "sex",
    "catégorie": "category",
    "date de départ": "departure date",
    "motif": "reason",
    "salaire de référence": "reference salary",
    "montant versé": "amount paid",
    "payé par le fonds": "paid by the fund",
    "date de paiement": "payment date",
}
_PERIODICITES = {"mensuel": "monthly", "annuel": "annual"}
_EVENEMENTS = {"retraite": "retirement", "depart_anticipe": "early departure",
               "licenciement_economique": "economic dismissal", "deces": "death"}


class _Gabarit:
    """Un gabarit calculé : `traduire` appelle `.format(**groupes)`, on y répond par une fonction."""
    def __init__(self, fonction):
        self.fonction = fonction

    def format(self, **groupes) -> str:
        return self.fonction(**groupes)


def _motif(francais: str) -> str:
    """« Âge de {age} ans. » → une expression qui reconnaît ce message, chaque {nom} en groupe nommé."""
    morceaux = re.split(r"\{(\w+)\}", francais)
    return "".join(re.escape(m) if i % 2 == 0 else f"(?P<{m}>.+?)" for i, m in enumerate(morceaux))


def _champ(libelle: str) -> str:
    return _CHAMPS.get(libelle.lower(), libelle)


def _champs(liste: str) -> str:
    return ", ".join(_champ(x) for x in liste.split(", "))


def _periodicite(mot: str) -> str:
    return _PERIODICITES.get(mot, mot)


def _libelle(libelle: str) -> str:
    """`regimes._libelle` : « Tout le personnel » ou « Catégorie « X » »."""
    if libelle == "Tout le personnel":
        return "All staff"
    m = re.fullmatch(r"Catégorie « (.+) »", libelle, flags=re.S)
    return f"Category “{m.group(1)}”" if m else libelle


def _plages(plages: str) -> str:
    """`regimes._plages` : « 3 à 5 ans, 9 ans » → « 3 to 5 years, 9 years »."""
    return re.sub(r"(\d+) ans", r"\1 years", plages).replace(" à ", " to ")


def _milliers(nombre: str) -> str:
    return nombre.replace(" ", ",")


def _ajouter(code: str, francais: str, anglais) -> None:
    TRADUCTIONS.setdefault(code, []).append((_motif(francais), anglais))


# --- lecture.py -------------------------------------------------------------------

_ajouter("format_non_pris_en_charge", "Format « .{ext} » non pris en charge : envoyer un fichier xlsx ou csv.",
         "Format “.{ext}” is not supported: send an xlsx or csv file.")
# departs.py : manquants et attendus. Avant la forme courte, qui l'avalerait.
_ajouter("colonnes_introuvables", "Colonne introuvable : {manquants}. Colonnes attendues : {attendus}.",
         _Gabarit(lambda manquants, attendus: f"Column not found: {_champs(manquants)}. "
                                              f"Expected columns: {_champs(attendus)}."))
_ajouter("colonnes_introuvables", "Intitulés introuvables. Colonnes attendues : {attendus}.",
         _Gabarit(lambda attendus: f"Column headings not found. Expected columns: {_champs(attendus)}."))
_ajouter("colonnes_introuvables", "Colonne introuvable : {manquants}.",
         _Gabarit(lambda manquants: f"Column not found: {_champs(manquants)}."))
_ajouter("colonne_en_double",
         "Deux colonnes pour le champ {champ} : « {retenue} » est retenue, « {ignoree} » est ignorée.",
         _Gabarit(lambda champ, retenue, ignoree: f"Two columns for the field {_champ(champ)}: “{retenue}” is used, "
                                                  f"“{ignoree}” is ignored."))
_ajouter("periodicite_contradictoire",
         "La colonne « {colonne} » indique un salaire {dite}, mais le dépôt le déclare {declaree}.",
         _Gabarit(lambda colonne, dite, declaree: f"The column “{colonne}” indicates a {_periodicite(dite)} salary, "
                                                  f"but the upload declares it {_periodicite(declaree)}."))
_ajouter("periodicite_inconnue", "Préciser si les salaires sont mensuels ou annuels.",
         "Specify whether the salaries are monthly or annual.")
_ajouter("fichier_vide", "Le fichier ne contient aucun salarié.", "The file contains no employees.")
_ajouter("date_illisible", "Date illisible : « {valeur} » (attendu jj/mm/aaaa).",
         "Unreadable date: “{valeur}” (expected dd/mm/yyyy).")
_ajouter("montant_illisible", "Montant illisible : « {valeur} ».", "Unreadable amount: “{valeur}”.")
_ajouter("sexe_illisible", "Sexe non reconnu : « {valeur} ».", "Sex not recognised: “{valeur}”.")

# --- controles.py -----------------------------------------------------------------

_ajouter("champ_manquant", "{champ} manquant(e).", _Gabarit(lambda champ: f"{_champ(champ).capitalize()} missing."))
_ajouter("salaire_invalide", "Le salaire doit être positif.", "The salary must be positive.")
_ajouter("naissance_improbable", "Âge de {age} ans à la date d'évaluation.", "Aged {age} at the valuation date.")
_ajouter("au_dela_de_la_retraite",
         "{age} ans, au-delà de l'âge de départ ({retraite} ans) : son IFC est due, pas future.",
         _Gabarit(lambda age, retraite: f"Aged {age.replace(',', '.')}, beyond the retirement age ({retraite}): "
                                        "the IFC is due now, not in the future."))
_ajouter("embauche_apres_evaluation", "Embauché(e) après la date d'évaluation.", "Hired after the valuation date.")
_ajouter("age_embauche_trop_bas", "Embauché(e) avant {age} ans.", "Hired before age {age}.")
_ajouter("matricule_double", "Matricule {matricule} présent plusieurs fois (lignes {lignes}).",
         "Staff number {matricule} appears more than once (rows {lignes}).")
_ajouter("dates_estimees", "{n} salariés nés un 1er janvier : dates probablement estimées, à confirmer.",
         "{n} employees born on 1 January: the dates are probably estimates, to be confirmed.")
_ajouter("date_evaluation_pas_fin_de_mois", "La date d'évaluation doit être une fin de mois (une clôture).",
         "The valuation date must be a month end (a closing date).")
_ajouter("donnees_trop_anciennes",
         "Données arrêtées au {donnees}, plus de {mois} mois avant la date d'évaluation ({evaluation}).",
         "Data as at {donnees}, more than {mois} months before the valuation date ({evaluation}).")
_ajouter("poids_excessif",
         "Le salarié {matricule} représente {part} % de l'engagement : vérifier ses données et qu'il relève du régime.",
         "Employee {matricule} accounts for {part}% of the liability: check their data and that they fall under "
         "the plan.")

# --- departs.py -------------------------------------------------------------------

_ajouter("fichier_vide", "Le fichier ne contient aucun départ.", "The file contains no departures.")
_ajouter("depart_en_double",
         "Le départ du matricule {matricule} au {date} figure deux fois (lignes {premiere} et {seconde}).",
         "The departure of staff number {matricule} on {date} appears twice (rows {premiere} and {seconde}).")
_ajouter("motif_inconnu", "Motif inconnu : « {valeur} » (retraite, démission, licenciement, décès ou autre).",
         "Unknown reason: “{valeur}” (retirement, resignation, dismissal, death or other).")
_ajouter("depart_avant_embauche", "Départ antérieur à l'embauche.", "Departure date before the hire date.")
_ajouter("date_paiement_requise", "Un paiement du fonds sans sa date.", "A payment by the fund without its date.")

# --- Les anomalies qu'une étude ajoute (services/etudes.py, experience.py, prestations.py) ----------

_ajouter("ecart_etude_precedente",
         "La dette passe de {avant} F au {date} à {apres} F ({ecart}) : expliquer l'écart.",
         _Gabarit(lambda avant, date, apres, ecart: f"The liability moves from {_milliers(avant)} F at {date} to "
                                                    f"{_milliers(apres)} F ({ecart}): explain the difference."))
_ajouter("parti_mais_dans_le_fichier",
         "{n} salarié(s) enregistré(s) comme parti(s) avant le {date} figurent encore dans le fichier "
         "(matricules {matricules}) : l'engagement les compte. Retirez-les du fichier, ou corrigez le départ.",
         "{n} employee(s) recorded as having left before {date} are still in the file (staff numbers "
         "{matricules}): the liability counts them. Remove them from the file, or correct the departure.")
_ajouter("deja_enregistree", "Le départ du matricule {matricule} au {date} est déjà enregistré.",
         "The departure of staff number {matricule} on {date} is already recorded.")

# Les constats du régime (services/regimes.py), repris dans les anomalies d'une étude : « sous_le_plancher » y
# devient « non_conformite ». Les deux codes, pour que l'écran du régime puisse s'en servir aussi.
_ajouter("convention_introuvable", "Aucune version de {convention} en vigueur le {date}.",
         "No version of {convention} in force on {date}.")
for _code in ("sous_le_plancher", "non_conformite"):
    _ajouter(_code, "{libelle} : le régime donne moins que {convention} pour {plages} d'ancienneté. "
                    "Les salariés gardent droit au plancher.",
             _Gabarit(lambda libelle, convention, plages: f"{_libelle(libelle)}: the plan gives less than {convention} "
                                                          f"for {_plages(plages)} of service. Employees keep their "
                                                          "right to the floor."))
_ajouter("base_salaire_approchee",
         "{libelle} : la base est la moyenne des 12 derniers mois ; l'évaluation retient le salaire courant du fichier.",
         _Gabarit(lambda libelle: f"{_libelle(libelle)}: the basis is the average of the last 12 months; the "
                                  "valuation uses the current salary in the file."))
_ajouter("evenements_non_evalues",
         "{libelle} : le régime couvre aussi {evenements}, que l'évaluation ne chiffre pas encore.",
         _Gabarit(lambda libelle, evenements: f"{_libelle(libelle)}: the plan also covers "
                                              f"{', '.join(_EVENEMENTS.get(e, e) for e in evenements.split(', '))}, "
                                              "which the valuation does not quantify yet."))


def anomalies_en_clair(anomalies: list[dict]) -> list[dict]:
    """Des COPIES, message traduit dans la langue de la requête : l'enregistré ne change jamais."""
    return [{**a, "message": traduire(a.get("code"), a["message"]) if a.get("message") else a.get("message")}
            for a in anomalies]


__all__ = ["anomalies_en_clair"]
