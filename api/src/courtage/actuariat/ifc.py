"""Indemnités de fin de carrière : évaluation prospective, salarié par salarié.

Méthode reprise du classeur Ariane IFC (feuille « Calcul Exo ») et décrite au
§7 de la spécification. Fonction pure : ni base de données, ni date du jour.
Les calculs sont en flottant ; les totaux sont arrondis au franc à la sortie.
"""
from dataclasses import dataclass
from datetime import date
from math import floor
from typing import Any, Mapping, Sequence

from dateutil.relativedelta import relativedelta

from courtage.referentiel import Convention, TableMortalite

VERSION_MOTEUR = "ifc-1.0.0"


@dataclass(frozen=True)
class Salarie:
    matricule: str
    naissance: date
    embauche: date
    salaire_annuel: int


@dataclass(frozen=True)
class Hypotheses:
    date_evaluation: date
    taux_actualisation: float
    croissance_salaires: float
    inflation: float
    age_retraite: int
    turnover: Mapping[int, float]  # taux de sortie par âge
    table: TableMortalite
    fonds_disponible: int = 0
    frais_sur_cotisation: float = 0.0


@dataclass(frozen=True)
class Ligne:
    matricule: str
    age: float
    anciennete: float
    annees_restantes: float
    anciennete_totale: float
    salaire_final_mensuel: float
    ifc: float
    probabilite_survie: float
    probabilite_presence: float
    actualisation: float
    vapf: float
    dette: float
    charge: float
    date_retraite: date
    au_dela_de_la_retraite: bool


@dataclass(frozen=True)
class Totaux:
    effectif: int
    vapf: int
    dette: int
    charge: int
    cotisation_nette: int
    cotisation_totale: int
    dette_brute: float  # non arrondie, pour les rapprochements
    charge_brute: float


@dataclass(frozen=True)
class Resultat:
    version_moteur: str
    convention: str
    lignes: list[Ligne]
    totaux: Totaux


def annees_entre(debut: date, fin: date) -> float:
    """Années révolues + jours depuis le dernier anniversaire / 365 (DATEDIF Y et YD)."""
    revolues = relativedelta(fin, debut).years
    anniversaire = debut + relativedelta(years=revolues)
    return revolues + (fin - anniversaire).days / 365


def mois_d_ifc(bareme: Mapping[str, Any], anciennete: int) -> float:
    """Nombre de mois de salaire dus pour une ancienneté entière."""
    forme = bareme["forme"]
    if forme == "tranches_cumulatives":
        mois, plancher = 0.0, 0
        for t in bareme["tranches"]:
            plafond = t["jusqu_a"] if t["jusqu_a"] is not None else anciennete
            mois += max(min(anciennete, plafond) - plancher, 0) * t["mois_par_annee"]
            plancher = plafond
            if anciennete <= plancher:
                break
        return mois
    if forme == "paliers":
        atteints = [p for p in bareme["paliers"] if anciennete >= p["a_partir_de"]]
        if atteints:
            return max(atteints, key=lambda p: p["a_partir_de"])["mois"]
        return anciennete * bareme["sous_premier_palier_mois_par_annee"]
    raise ValueError(f"forme de barème inconnue : {forme}")


def probabilite_presence(age: float, age_retraite: int, turnover: Mapping[int, float]) -> float:
    """Probabilité de ne pas quitter l'entreprise d'ici la retraite."""
    p = 1.0
    for x in range(int(age), age_retraite):
        p *= 1 - turnover.get(x, 0.0)
    return p


def evaluer(
    salaries: Sequence[Salarie],
    h: Hypotheses,
    convention: Convention,
    presences: Mapping[str, float] | None = None,
) -> Resultat:
    """Évalue l'engagement IFC.

    `presences` reprend des probabilités de présence fournies par une étude
    existante (rapprochement avec un classeur) au lieu de les calculer.
    """
    lignes = [_evaluer_un(s, h, convention, presences) for s in salaries]
    dette = sum(l.dette for l in lignes)
    charge = sum(l.charge for l in lignes)
    nette = max(dette + charge - h.fonds_disponible, 0.0)
    totaux = Totaux(
        effectif=len(lignes),
        vapf=round(sum(l.vapf for l in lignes)),
        dette=round(dette),
        charge=round(charge),
        cotisation_nette=round(nette),
        cotisation_totale=round(nette * (1 + h.frais_sur_cotisation)),
        dette_brute=dette,
        charge_brute=charge,
    )
    return Resultat(VERSION_MOTEUR, convention.code, lignes, totaux)


def _evaluer_un(s: Salarie, h: Hypotheses, convention: Convention, presences) -> Ligne:
    age = annees_entre(s.naissance, h.date_evaluation)
    anciennete = 0.0 if s.embauche > h.date_evaluation else annees_entre(s.embauche, h.date_evaluation)
    date_retraite = s.naissance + relativedelta(years=h.age_retraite)
    au_dela = age > h.age_retraite
    restantes = 0.0 if au_dela else h.age_retraite - age
    anciennete_totale = max(anciennete, annees_entre(s.embauche, date_retraite))

    croissance = ((1 + h.inflation) * (1 + h.croissance_salaires)) ** restantes
    salaire_final = s.salaire_annuel / 12 * croissance
    ifc = salaire_final * mois_d_ifc(convention.bareme, floor(anciennete_totale))

    survie = h.table.survie(floor(age), h.age_retraite) if not au_dela else 1.0
    if presences is not None and s.matricule in presences:
        presence = presences[s.matricule]
    else:
        presence = probabilite_presence(age, h.age_retraite, h.turnover)
    actualisation = (1 + h.taux_actualisation) ** -restantes

    vapf = ifc * survie * presence * actualisation
    dette = vapf * anciennete / anciennete_totale if anciennete_totale else 0.0
    charge = vapf / anciennete_totale if (anciennete_totale and age < h.age_retraite) else 0.0

    return Ligne(
        matricule=s.matricule,
        age=age,
        anciennete=anciennete,
        annees_restantes=restantes,
        anciennete_totale=anciennete_totale,
        salaire_final_mensuel=salaire_final,
        ifc=ifc,
        probabilite_survie=survie,
        probabilite_presence=presence,
        actualisation=actualisation,
        vapf=vapf,
        dette=dette,
        charge=charge,
        date_retraite=date_retraite,
        au_dela_de_la_retraite=au_dela,
    )
