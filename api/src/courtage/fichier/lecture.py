"""Lecture d'un fichier du personnel (xlsx, csv) en lignes typées."""
import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

import openpyxl

from courtage.actuariat.ifc import Salarie

Niveau = Literal["bloquant", "avertissement"]
Periodicite = Literal["mensuel", "annuel"]

CHAMPS_OBLIGATOIRES = ("matricule", "naissance", "embauche", "salaire")
LIBELLES = {
    "matricule": "matricule",
    "naissance": "date de naissance",
    "embauche": "date d'embauche",
    "salaire": "salaire",
    "sexe": "sexe",
    "categorie": "catégorie",
}

# Intitulés normalisés (minuscules, sans accents ni ponctuation) → champ.
_SYNONYMES = {
    "matricule": ["matricule", "mat", "n", "no", "numero", "id", "employee id", "employee number", "staff id"],
    "naissance": ["date de naissance", "naissance", "ne le", "nee le", "ne e le", "date naissance",
                  "birth date", "date of birth", "dob"],
    "embauche": ["date d embauche", "embauche", "date d entree", "entree", "date entree", "date embauche",
                 "hire date", "date of hire", "start date"],
    "salaire": ["salaire", "salaire brut", "remuneration", "salary", "gross salary", "base salary"],
    "sexe": ["sexe", "genre", "sex", "gender"],
    "categorie": ["categorie", "categorie professionnelle", "category", "college", "csp", "classification"],
}
# Colonnes identifiantes : repérées pour être écartées sans lecture.
_NOMS = ["nom", "prenom", "prenoms", "nom et prenom", "nom et prenoms", "nom prenom", "noms",
         "name", "first name", "last name", "full name", "surname"]
_MENSUEL = ("mensuel", "monthly", "par mois", "mois")
_ANNUEL = ("annuel", "annual", "par an", "yearly")


@dataclass(frozen=True)
class Anomalie:
    niveau: Niveau
    code: str
    message: str
    ligne: int | None = None
    colonne: str | None = None


@dataclass(frozen=True)
class LigneLue:
    numero: int  # numéro de ligne dans le tableur de l'utilisateur
    matricule: str | None
    sexe: Literal["F", "M"] | None
    naissance: date | None
    embauche: date | None
    salaire_annuel: int | None
    categorie: str | None = None


@dataclass
class Lecture:
    lignes: list[LigneLue] = field(default_factory=list)
    anomalies: list[Anomalie] = field(default_factory=list)
    colonnes: dict[str, str] = field(default_factory=dict)  # champ → intitulé lu
    colonnes_ignorees: list[str] = field(default_factory=list)
    periodicite: Periodicite | None = None


def lire_fichier(contenu: bytes, nom_fichier: str, periodicite: Periodicite | None = None) -> Lecture:
    extension = nom_fichier.rsplit(".", 1)[-1].lower() if "." in nom_fichier else ""
    if extension in ("xlsx", "xlsm"):
        grille = _grille_xlsx(contenu)
    elif extension in ("csv", "txt"):
        grille = _grille_csv(contenu)
    else:
        lecture = Lecture()
        lecture.anomalies.append(Anomalie("bloquant", "format_non_pris_en_charge",
                                          f"Format « .{extension} » non pris en charge : envoyer un fichier xlsx ou csv."))
        return lecture
    return _lire_grille(grille, periodicite)


def salaries(lecture: Lecture) -> list[Salarie]:
    """Les lignes complètes, pour le moteur. Les contrôles disent si l'étude peut sortir."""
    return [
        Salarie(matricule=l.matricule, naissance=l.naissance, embauche=l.embauche, salaire_annuel=l.salaire_annuel,
                categorie=l.categorie)
        for l in lecture.lignes
        if l.matricule and l.naissance and l.embauche and l.salaire_annuel is not None
    ]


# --- Grilles ------------------------------------------------------------------

def _grille_xlsx(contenu: bytes) -> list[list]:
    classeur = openpyxl.load_workbook(io.BytesIO(contenu), read_only=True, data_only=True)
    feuille = classeur.worksheets[0]
    return [list(r) for r in feuille.iter_rows(values_only=True)]


def _grille_csv(contenu: bytes) -> list[list]:
    try:
        texte = contenu.decode("utf-8-sig")
    except UnicodeDecodeError:
        texte = contenu.decode("cp1252", errors="replace")  # exports Excel de Windows
    premiere = texte.splitlines()[0] if texte else ""
    separateur = max(";,\t", key=premiere.count)
    return [list(r) for r in csv.reader(io.StringIO(texte), delimiter=separateur)]


# --- Intitulés ----------------------------------------------------------------

def _normaliser(texte) -> str:
    texte = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", texte).strip()


def _champ_de(intitule) -> str | None:
    n = _normaliser(intitule)
    if not n:
        return None
    if n in _NOMS:
        return "_nom"
    sans_parentheses = _normaliser(re.sub(r"\(.*?\)", "", str(intitule)))
    for champ, synonymes in _SYNONYMES.items():
        for s in synonymes:
            if n == s or sans_parentheses == s:
                return champ
    # « Salaire brut mensuel », « Salaire annuel (FCFA) » : un salaire qualifié.
    if n.startswith(("salaire", "salary", "remuneration")) or n.endswith("salary"):
        return "salaire"
    return None


def _trouver_entete(grille: list[list]) -> int | None:
    for i, rangee in enumerate(grille[:15]):
        champs = {_champ_de(c) for c in rangee if c is not None}
        if len(champs & set(CHAMPS_OBLIGATOIRES)) >= 3:
            return i
    return None


def _periodicite_de(intitule: str) -> Periodicite | None:
    n = _normaliser(intitule)
    if any(m in n for m in _ANNUEL):
        return "annuel"
    if any(m in n for m in _MENSUEL):
        return "mensuel"
    return None


# --- Lecture ------------------------------------------------------------------

def _lire_grille(grille: list[list], periodicite: Periodicite | None) -> Lecture:
    lecture = Lecture()
    i_entete = _trouver_entete(grille)
    if i_entete is None:
        manquants = ", ".join(LIBELLES[c] for c in CHAMPS_OBLIGATOIRES)
        lecture.anomalies.append(Anomalie("bloquant", "colonnes_introuvables",
                                          f"Intitulés introuvables. Colonnes attendues : {manquants}."))
        return lecture

    index: dict[str, int] = {}
    for j, intitule in enumerate(grille[i_entete]):
        if intitule is None or str(intitule).strip() == "":
            continue
        champ = _champ_de(intitule)
        if champ in LIBELLES and champ not in index:
            index[champ] = j
            lecture.colonnes[champ] = str(intitule)
        else:
            lecture.colonnes_ignorees.append(str(intitule))
            if champ in LIBELLES:
                lecture.anomalies.append(Anomalie(
                    "avertissement", "colonne_en_double",
                    f"Deux colonnes pour le champ {LIBELLES[champ]} : « {lecture.colonnes[champ]} » est retenue, "
                    f"« {intitule} » est ignorée.", colonne=LIBELLES[champ]))

    manquants = [LIBELLES[c] for c in CHAMPS_OBLIGATOIRES if c not in index]
    if manquants:
        lecture.anomalies.append(Anomalie("bloquant", "colonnes_introuvables",
                                          "Colonne introuvable : " + ", ".join(manquants) + "."))
        return lecture

    dite = _periodicite_de(lecture.colonnes["salaire"])
    if dite and periodicite and dite != periodicite:
        lecture.anomalies.append(Anomalie("bloquant", "periodicite_contradictoire",
                                          f"La colonne « {lecture.colonnes['salaire']} » indique un salaire {dite}, "
                                          f"mais le dépôt le déclare {periodicite}.", colonne="salaire"))
        return lecture
    lecture.periodicite = dite or periodicite
    if lecture.periodicite is None:
        lecture.anomalies.append(Anomalie("bloquant", "periodicite_inconnue",
                                          "Préciser si les salaires sont mensuels ou annuels.", colonne="salaire"))
        return lecture

    for i in range(i_entete + 1, len(grille)):
        rangee = grille[i]
        valeurs = {c: (rangee[j] if j < len(rangee) else None) for c, j in index.items()}
        if all(_vide(v) for v in valeurs.values()):
            continue
        lecture.lignes.append(_lire_ligne(i + 1, valeurs, lecture))
    if not lecture.lignes:
        lecture.anomalies.append(Anomalie("bloquant", "fichier_vide", "Le fichier ne contient aucun salarié."))
    return lecture


def _lire_ligne(numero: int, v: dict, lecture: Lecture) -> LigneLue:
    def date_de(champ):
        if _vide(v.get(champ)):
            return None
        d = _date(v[champ])
        if d is None:
            lecture.anomalies.append(Anomalie("bloquant", "date_illisible",
                                              f"Date illisible : « {v[champ]} » (attendu jj/mm/aaaa).",
                                              ligne=numero, colonne=LIBELLES[champ]))
        return d

    salaire = None
    if not _vide(v.get("salaire")):
        montant = _montant(v["salaire"])
        if montant is None:
            lecture.anomalies.append(Anomalie("bloquant", "montant_illisible",
                                              f"Montant illisible : « {v['salaire']} ».", ligne=numero, colonne="salaire"))
        else:
            annuel = montant * 12 if lecture.periodicite == "mensuel" else montant
            salaire = int(annuel.quantize(Decimal(1), rounding=ROUND_HALF_UP))

    sexe = None
    if not _vide(v.get("sexe")):
        sexe = _sexe(v["sexe"])
        if sexe is None:
            lecture.anomalies.append(Anomalie("avertissement", "sexe_illisible",
                                              f"Sexe non reconnu : « {v['sexe']} ».", ligne=numero, colonne="sexe"))

    return LigneLue(
        numero=numero,
        matricule=None if _vide(v.get("matricule")) else _texte_matricule(v["matricule"]),
        sexe=sexe,
        naissance=date_de("naissance"),
        embauche=date_de("embauche"),
        salaire_annuel=salaire,
        categorie=None if _vide(v.get("categorie")) else str(v["categorie"]).strip(),
    )


# --- Valeurs ------------------------------------------------------------------

def _vide(x) -> bool:
    return x is None or (isinstance(x, str) and x.strip() == "")


def _texte_matricule(x) -> str:
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return str(x).strip()


_FORMATS_DATE = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d")


def _date(x) -> date | None:
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    if isinstance(x, (int, float)) and 1 < x < 80000:  # numéro de série Excel
        return (datetime(1899, 12, 30) + timedelta(days=int(x))).date()
    texte = str(x).strip()
    for f in _FORMATS_DATE:
        try:
            d = datetime.strptime(texte, f).date()
        except ValueError:
            continue
        if d.year >= 1900:  # une année sur deux chiffres est ambiguë : refusée
            return d
    return None


def _montant(x) -> Decimal | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return Decimal(str(x))
    texte = re.sub(r"(?i)(fcfa|f\s*cfa|xaf|cfa|f)$", "", str(x).strip())
    texte = re.sub(r"[\s  ]", "", texte).replace(",", ".")
    try:
        return Decimal(texte)
    except InvalidOperation:
        return None


def _sexe(x) -> Literal["F", "M"] | None:
    n = _normaliser(x)
    if n in ("f", "femme", "female", "feminin", "w", "woman"):
        return "F"
    if n in ("m", "h", "homme", "male", "masculin", "man"):
        return "M"
    return None
