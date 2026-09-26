"""`GET /api/v1/referentiel/conventions` : les conventions préremplies des pays de la CEMAC, publiques.

Un barème de convention collective est un texte public ; le montrer à qui veut
le lire, sources et degré de vérification compris, est la moitié du conseil.
Rien d'un client n'y figure. Chaque version est listée (une convention révisée
garde son ancienne version : une étude datée d'avant s'y réfère).
"""
from datetime import date

from fastapi import APIRouter

from courtage.actuariat.ifc import mois_d_ifc
from courtage.referentiel import CEMAC, referentiel_courant

routeur_referentiel = APIRouter()

ANCIENNETES = (5, 10, 15, 20, 25, 30, 35)


@routeur_referentiel.get("/referentiel/conventions")
def conventions():
    ref = referentiel_courant()
    aujourd_hui = date.today()
    return {
        "version": ref.version,
        "pays_couverts": CEMAC,
        "conventions": [{
            **c.model_dump(mode="json"),
            "pays_libelle": CEMAC[c.pays],
            "en_vigueur_aujourd_hui": c.en_vigueur(aujourd_hui),
            # Ce que le barème donne, en mois de salaire, à quelques anciennetés : pour lire sans calculer.
            "illustration": [{"anciennete": n, "mois": round(mois_d_ifc(c.bareme, n), 2)} for n in ANCIENNETES],
        } for c in sorted(ref.conventions, key=lambda c: (c.pays, c.code, c.en_vigueur_du)) if c.pays in CEMAC],
    }
