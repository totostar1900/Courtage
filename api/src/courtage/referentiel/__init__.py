"""Référentiel actuariel : barèmes de conventions et tables de mortalité.

Un référentiel est un instantané complet, identifié par sa version. Chaque
barème est une donnée datée (en vigueur du … au …) qui cite ses sources ; une
convention peut avoir plusieurs versions successives sous le même code.

La règle d'émission (`motifs_de_refus`) est ici, pas dans le moteur : le
moteur calcule avec n'importe quel barème, une étude ne SORT qu'avec un barème
valide, du pays de l'organisation, en vigueur à la date d'évaluation.
"""
import json
from datetime import date
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION_COURANTE = "2026-09-26"
# Le périmètre servi aujourd'hui (décision du 26/09) : consultation et extraction assistée. Les conventions
# d'autres pays restent au référentiel, parce que des études s'y réfèrent, mais ne sont pas proposées.
CEMAC = {"CM": "Cameroun", "GA": "Gabon", "CG": "Congo", "TD": "Tchad", "CF": "Centrafrique", "GQ": "Guinée équatoriale"}
_DONNEES = files(__package__) / "donnees"


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Source(_Strict):
    titre: str = Field(min_length=1)
    url: str | None = None
    consulte_le: date | None = None


class Tranche(_Strict):
    jusqu_a: int | None = Field(default=None, gt=0)  # None : sans limite
    mois_par_annee: float = Field(ge=0, le=3)


class BaremeTranches(_Strict):
    """Chaque année d'ancienneté est payée au taux de sa tranche."""
    forme: Literal["tranches_cumulatives"]
    tranches: list[Tranche] = Field(min_length=1)

    @model_validator(mode="after")
    def _ordre(self):
        bornes = [t.jusqu_a for t in self.tranches]
        if bornes[-1] is not None:
            raise ValueError("la dernière tranche doit être sans limite (jusqu_a: null)")
        fermees = bornes[:-1]
        if None in fermees or fermees != sorted(set(fermees)):
            raise ValueError("les bornes des tranches doivent être strictement croissantes")
        return self


class Palier(_Strict):
    a_partir_de: int = Field(gt=0)
    mois: float = Field(ge=0, le=36)


class BaremePaliers(_Strict):
    """Un nombre de mois fixe à partir d'une ancienneté ; linéaire sous le premier palier."""
    forme: Literal["paliers"]
    sous_premier_palier_mois_par_annee: float = Field(ge=0, le=3)
    paliers: list[Palier] = Field(min_length=1)

    @model_validator(mode="after")
    def _ordre(self):
        seuils = [p.a_partir_de for p in self.paliers]
        if seuils != sorted(set(seuils)):
            raise ValueError("les paliers doivent être strictement croissants")
        return self


Bareme = Annotated[Union[BaremeTranches, BaremePaliers], Field(discriminator="forme")]


class Convention(_Strict):
    pays: str = Field(pattern=r"^[A-Z]{2}$")
    code: str = Field(pattern=r"^[A-Z]{2}_[A-Z0-9_]+$")
    libelle: str
    statut: Literal["valide", "a_valider"]
    en_vigueur_du: date
    en_vigueur_au: date | None = None
    sources: list[Source] = Field(min_length=1)
    verification: str = Field(min_length=1)
    notes: list[str] = []
    bareme: Bareme

    @model_validator(mode="after")
    def _vigueur(self):
        if self.en_vigueur_au is not None and self.en_vigueur_au < self.en_vigueur_du:
            raise ValueError("en_vigueur_au précède en_vigueur_du")
        return self

    def en_vigueur(self, jour: date) -> bool:
        return self.en_vigueur_du <= jour and (self.en_vigueur_au is None or jour <= self.en_vigueur_au)


class TableMortalite(_Strict):
    code: str
    libelle: str
    sources: list[Source] = Field(min_length=1)
    lx: dict[int, float]

    def survie(self, de: int, a: int) -> float:
        """Probabilité d'être en vie à l'âge `a` sachant l'âge `de`, plafonnée à 1."""
        return min(1.0, self.lx[a] / self.lx[de])


class Referentiel:
    def __init__(self, version: str, conventions: list[Convention], tables: dict[str, TableMortalite]):
        self.version = version
        self.conventions = conventions
        self.tables = tables
        _refuser_les_chevauchements(conventions)

    @classmethod
    def depuis_dossier(cls, dossier, version: str) -> "Referentiel":
        dossier = Path(str(dossier))
        conventions = [
            Convention.model_validate(json.loads(f.read_text("utf-8")))
            for f in sorted(dossier.glob("convention_*.json"))
        ]
        tables = {}
        for f in sorted(dossier.glob("table_*.json")):
            t = TableMortalite.model_validate(json.loads(f.read_text("utf-8")))
            tables[t.code] = t
        return cls(version, conventions, tables)

    def convention(self, code: str, a_la_date: date) -> Convention:
        versions = [c for c in self.conventions if c.code == code]
        if not versions:
            raise LookupError(f"convention inconnue : {code}")
        for c in versions:
            if c.en_vigueur(a_la_date):
                return c
        raise LookupError(f"aucune version de {code} en vigueur le {a_la_date.isoformat()}")

    def conventions_du_pays(self, pays: str, a_la_date: date) -> list[Convention]:
        return [c for c in self.conventions if c.pays == pays and c.en_vigueur(a_la_date)]

    def table(self, code: str) -> TableMortalite:
        return self.tables[code]


def _refuser_les_chevauchements(conventions: list[Convention]) -> None:
    par_code: dict[str, list[Convention]] = {}
    for c in conventions:
        par_code.setdefault(c.code, []).append(c)
    for code, versions in par_code.items():
        versions.sort(key=lambda c: c.en_vigueur_du)
        for avant, apres in zip(versions, versions[1:]):
            if avant.en_vigueur_au is None or avant.en_vigueur_au >= apres.en_vigueur_du:
                raise ValueError(f"{code} : deux versions se chevauchent au {apres.en_vigueur_du}")


MotifDeRefus = Literal["pays_different", "convention_a_valider", "hors_vigueur"]


def motifs_de_refus(convention: Convention, *, pays_organisation: str, date_evaluation: date) -> list[MotifDeRefus]:
    """Ce qui interdit d'émettre une étude avec cette convention. Vide : émission permise."""
    motifs: list[MotifDeRefus] = []
    if convention.pays != pays_organisation:
        motifs.append("pays_different")
    if convention.statut != "valide":
        motifs.append("convention_a_valider")
    if not convention.en_vigueur(date_evaluation):
        motifs.append("hors_vigueur")
    return motifs


@cache
def referentiel_courant() -> Referentiel:
    return Referentiel.depuis_dossier(_DONNEES, version=VERSION_COURANTE)


def charger_convention(code: str, a_la_date: date | None = None) -> Convention:
    """La version de `code` en vigueur à la date ; sans date, seulement si elle est unique."""
    ref = referentiel_courant()
    if a_la_date is not None:
        return ref.convention(code, a_la_date)
    versions = [c for c in ref.conventions if c.code == code]
    if len(versions) != 1:
        raise LookupError(f"{code} a {len(versions)} versions : préciser la date")
    return versions[0]


def charger_table(code: str) -> TableMortalite:
    return referentiel_courant().table(code)


# Hypothèses par défaut d'une étude IFC (reprises d'Ariane IFC). Une étude qui
# s'en écarte enregistre l'écart et sa justification.
HYPOTHESES_PAR_DEFAUT: dict[str, float | int | str] = {
    "taux_actualisation": 0.035,
    "croissance_salaires": 0.02,
    "inflation": 0.0,
    "age_retraite": 60,
    "taux_turnover": 0.02,
    "frais_sur_cotisation": 0.04,
    "table": "TV_CIMA_F",
}


class NoteJuridique(_Strict):
    """Une information juridique ou fiscale, sourcée. `a_valider` tant qu'un juriste ne l'a pas relue :
    la plateforme informe, elle ne donne pas d'avis juridique."""
    id: str
    titre: str = Field(min_length=1)
    texte: str = Field(min_length=1)
    pays: str | None = None
    statut: Literal["valide", "a_valider"]
    sources: list[Source] = []


@cache
def notes_juridiques() -> dict[str, NoteJuridique]:
    brut = json.loads((_DONNEES / "notes_juridiques.json").read_text("utf-8"))
    return {n["id"]: NoteJuridique.model_validate(n) for n in brut["notes"]}
