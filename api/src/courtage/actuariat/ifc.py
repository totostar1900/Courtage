"""Indemnités de fin de carrière : évaluation prospective, salarié par salarié.

Méthode reprise du classeur Ariane IFC (feuille « Calcul Exo ») et décrite au
§7 de la spécification. Fonction pure : ni base de données, ni date du jour.
Les calculs sont en flottant ; les totaux sont arrondis au franc à la sortie.
"""
from dataclasses import dataclass
from datetime import date
from math import floor
from typing import Literal, Mapping, Sequence

from dateutil.relativedelta import relativedelta

from courtage.referentiel import Bareme, BaremePaliers, BaremeTranches, Convention, TableMortalite

VERSION_MOTEUR = "ifc-1.1.0"


@dataclass(frozen=True)
class Salarie:
    matricule: str
    naissance: date
    embauche: date
    salaire_annuel: int
    categorie: str | None = None


@dataclass(frozen=True)
class Regles:
    """Ce qu'un régime verse à une catégorie de personnel.

    `plancher` est la règle de la convention collective : le salarié y a
    toujours droit, et le moteur retient le plus favorable des deux, ancienneté
    par ancienneté. Le plancher a ses propres conditions.
    """
    bareme: Bareme
    plancher: "Regles | None" = None
    anciennete_minimale: int = 0          # années révolues ouvrant droit
    plafond_mois: float | None = None     # nombre de mois de salaire au plus
    arrondi: Literal["annees", "mois"] = "annees"


class CategorieInconnue(ValueError):
    def __init__(self, categorie):
        super().__init__(f"aucune règle pour la catégorie « {categorie} »")
        self.categorie = categorie


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
    categorie: str | None = None
    mois: float = 0.0                 # mois de salaire retenus
    plancher_applique: bool = False   # la convention a donné plus que le régime


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
    par_categorie: dict[str, dict] | None = None


def annees_entre(debut: date, fin: date) -> float:
    """Années révolues + jours depuis le dernier anniversaire / 365 (DATEDIF Y et YD)."""
    revolues = relativedelta(fin, debut).years
    anniversaire = debut + relativedelta(years=revolues)
    return revolues + (fin - anniversaire).days / 365


def mois_d_ifc(bareme: Bareme, anciennete: int) -> float:
    """Nombre de mois de salaire dus pour une ancienneté entière."""
    if isinstance(bareme, BaremeTranches):
        mois, plancher = 0.0, 0
        for t in bareme.tranches:
            plafond = t.jusqu_a if t.jusqu_a is not None else anciennete
            mois += max(min(anciennete, plafond) - plancher, 0) * t.mois_par_annee
            plancher = plafond
            if anciennete <= plancher:
                break
        return mois
    if isinstance(bareme, BaremePaliers):
        atteints = [p for p in bareme.paliers if anciennete >= p.a_partir_de]
        if atteints:
            return max(atteints, key=lambda p: p.a_partir_de).mois
        return anciennete * bareme.sous_premier_palier_mois_par_annee
    raise TypeError(f"barème inconnu : {type(bareme).__name__}")


def mois_dus(regles: Regles, anciennete_totale: float) -> tuple[float, bool]:
    """Mois de salaire dus à une ancienneté : (mois retenus, le plancher a-t-il joué ?)."""
    propres = _mois_selon(regles, anciennete_totale)
    if regles.plancher is None:
        return propres, False
    plancher = _mois_selon(regles.plancher, anciennete_totale)
    return (plancher, True) if plancher > propres + 1e-12 else (propres, False)


def _mois_selon(regles: Regles, anciennete_totale: float) -> float:
    if regles.arrondi == "mois":
        anciennete = floor(anciennete_totale * 12 + 1e-9) / 12
    else:
        anciennete = floor(anciennete_totale + 1e-9)
    if anciennete < regles.anciennete_minimale:
        return 0.0
    mois = mois_d_ifc(regles.bareme, anciennete)
    return min(mois, regles.plafond_mois) if regles.plafond_mois is not None else mois


def comparer_baremes(bareme: Bareme, minimum: Bareme, jusqu_a: int = 50) -> list[int]:
    """Les anciennetés (0 à `jusqu_a` ans) où `bareme` donne moins que `minimum`."""
    return [n for n in range(jusqu_a + 1) if mois_d_ifc(bareme, n) < mois_d_ifc(minimum, n) - 1e-9]


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
    bareme: Bareme | None = None,
    regles: Mapping[str, Regles] | None = None,
) -> Resultat:
    """Évalue l'engagement IFC.

    `presences` reprend des probabilités de présence fournies par une étude
    existante (rapprochement avec un classeur) au lieu de les calculer.
    `bareme` remplace celui de la convention : le barème de l'entreprise quand
    elle verse plus que sa convention.
    `regles` donne les règles de chaque catégorie de personnel (`"*"` pour les
    autres) ; une catégorie sans règle est refusée (`CategorieInconnue`).
    """
    unique = Regles(bareme=bareme if bareme is not None else convention.bareme)
    lignes = [_evaluer_un(s, h, _regles_de(s, regles, unique), presences) for s in salaries]
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
    par_categorie: dict[str, dict] = {}
    for l in lignes:
        c = par_categorie.setdefault(l.categorie or "*", {"effectif": 0, "vapf": 0.0, "dette": 0.0, "charge": 0.0})
        c["effectif"] += 1
        c["vapf"] += l.vapf
        c["dette"] += l.dette
        c["charge"] += l.charge
    for c in par_categorie.values():
        c.update(vapf=round(c["vapf"]), dette=round(c["dette"]), charge=round(c["charge"]))
    return Resultat(VERSION_MOTEUR, convention.code, lignes, totaux, par_categorie)


def _regles_de(s: Salarie, regles: Mapping[str, Regles] | None, unique: Regles) -> Regles:
    if regles is None:
        return unique
    if s.categorie in regles:
        return regles[s.categorie]
    if "*" in regles:
        return regles["*"]
    raise CategorieInconnue(s.categorie)


def _evaluer_un(s: Salarie, h: Hypotheses, regles: Regles, presences) -> Ligne:
    age = annees_entre(s.naissance, h.date_evaluation)
    anciennete = 0.0 if s.embauche > h.date_evaluation else annees_entre(s.embauche, h.date_evaluation)
    date_retraite = s.naissance + relativedelta(years=h.age_retraite)
    au_dela = age > h.age_retraite
    restantes = 0.0 if au_dela else h.age_retraite - age
    anciennete_totale = max(anciennete, annees_entre(s.embauche, date_retraite))

    croissance = ((1 + h.inflation) * (1 + h.croissance_salaires)) ** restantes
    salaire_final = s.salaire_annuel / 12 * croissance
    mois, plancher_applique = mois_dus(regles, anciennete_totale)
    ifc = salaire_final * mois

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
        categorie=s.categorie,
        mois=mois,
        plancher_applique=plancher_applique,
    )
