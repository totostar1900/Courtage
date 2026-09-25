"""Référentiel actuariel : barèmes de conventions et tables de mortalité.

Tâche 1 : lecture de fichiers JSON embarqués. La tâche 2 ajoute les versions,
la validation du format et la règle d'émission.
"""
import json
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any, Mapping

_DONNEES = files(__package__) / "donnees"


@dataclass(frozen=True)
class Convention:
    pays: str
    code: str
    libelle: str
    statut: str  # "valide" | "a_valider"
    source: str
    bareme: Mapping[str, Any]


@dataclass(frozen=True)
class TableMortalite:
    code: str
    libelle: str
    lx: Mapping[int, float]

    def survie(self, de: int, a: int) -> float:
        """Probabilité d'être en vie à l'âge `a` sachant l'âge `de`, plafonnée à 1."""
        return min(1.0, self.lx[a] / self.lx[de])


@cache
def charger_convention(code: str) -> Convention:
    brut = json.loads((_DONNEES / f"convention_{code.lower()}.json").read_text("utf-8"))
    return Convention(**brut)


@cache
def charger_table(code: str) -> TableMortalite:
    brut = json.loads((_DONNEES / f"table_{code.lower()}.json").read_text("utf-8"))
    return TableMortalite(
        code=brut["code"],
        libelle=brut["libelle"],
        lx={int(age): float(v) for age, v in brut["lx"].items()},
    )
