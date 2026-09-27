"""`GET /api/v1/referentiel/conventions` : les conventions préremplies des pays de la CEMAC, publiques.

Un barème de convention collective est un texte public ; le montrer à qui veut
le lire, sources et degré de vérification compris, est la moitié du conseil.
Rien d'un client n'y figure. Chaque version est listée (une convention révisée
garde son ancienne version : une étude datée d'avant s'y réfère).
"""
from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import Response

from courtage.actuariat.ifc import mois_d_ifc
from courtage.erreurs import ErreurMetier
from courtage.modeles import modeles_du_pays
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


@routeur_referentiel.get("/referentiel/modeles")
def modeles(pays: str = Query(pattern=r"^[A-Z]{2}$")):
    """Les modèles types d'un pays de la CEMAC, calculés depuis ses conventions en vigueur : publics, comme elles."""
    if pays not in CEMAC:
        raise ErreurMetier("pays_non_couvert", "La plateforme couvre pour l'instant les pays de la CEMAC.", 422)
    return {"pays": pays, "pays_libelle": CEMAC[pays], "modeles": modeles_du_pays(referentiel_courant(), pays, date.today())}


@routeur_referentiel.get("/referentiel/hypotheses")
def hypotheses_etude():
    """Les hypothèses d'une étude : défauts, bornes, rôle et effet de chacune, tables de mortalité. Public."""
    from courtage.services.hypotheses import catalogue
    return catalogue()


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@routeur_referentiel.get("/referentiel/canevas-personnel")
def canevas_personnel():
    """Le classeur à remplir pour déposer son personnel : public, il ne porte aucune donnée."""
    from courtage.fichier.canevas import canevas
    return Response(canevas(), media_type=XLSX,
                    headers={"Content-Disposition": 'attachment; filename="canevas-personnel.xlsx"'})
