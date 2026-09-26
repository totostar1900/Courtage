"""Les modèles types de régime : des barèmes CALCULÉS depuis ceux des conventions, jamais écrits à la main.

Une entreprise sans régime part d'un modèle plutôt que d'une page blanche. Chaque modèle est conforme par
construction : arrondi vers le haut, il ne donne à aucune ancienneté moins que la convention. Il est servi
comme une version proposée (la forme de l'extraction assistée) : l'entreprise le relit, le corrige et
l'enregistre ; l'analyse habituelle suit, et elle seule adopte. Aucune donnée d'entreprise n'y entre.
Conception : docs/specs/2026-09-26-modeles-types-design.md.
"""
import math
from datetime import date

from courtage.actuariat.ifc import mois_d_ifc
from courtage.referentiel import BaremePaliers, BaremeTranches, Convention, Referentiel

ANCIENNETES = (5, 10, 15, 20, 25, 30, 35)
_HORIZON = range(1, 46)
_TAUX_MAX, _PALIER_MAX = 3.0, 36.0

MODELES = {
    "minimum": ("Minimum conventionnel",
                "Le barème de la convention, sans rien de plus : ce que la loi impose déjà."),
    "plus_25": ("Convention + 25 %",
                "Chaque taux de la convention majoré d'un quart : un geste lisible, qui suit la convention."),
    "cadres": ("Cadres favorisés",
               "Les cadres à une fois et demie la convention ; les autres salariés au minimum."),
    "simple": ("Barème unique",
               "Un seul taux par année d'ancienneté, facile à expliquer, jamais sous la convention."),
}


def _haut(x: float, pas: float = 0.01) -> float:
    """Arrondi vers le haut au pas donné (le bruit flottant sous le pas est ignoré)."""
    return round(math.ceil(round(x / pas, 9)) * pas, 2)


def _multiplier(bareme, facteur: float):
    if isinstance(bareme, BaremeTranches):
        return BaremeTranches(forme="tranches_cumulatives", tranches=[
            {"jusqu_a": t.jusqu_a, "mois_par_annee": min(_haut(t.mois_par_annee * facteur), _TAUX_MAX)}
            for t in bareme.tranches])
    return BaremePaliers(
        forme="paliers",
        sous_premier_palier_mois_par_annee=min(_haut(bareme.sous_premier_palier_mois_par_annee * facteur), _TAUX_MAX),
        paliers=[{"a_partir_de": p.a_partir_de, "mois": min(_haut(p.mois * facteur), _PALIER_MAX)}
                 for p in bareme.paliers])


def _taux_unique(bareme) -> BaremeTranches:
    taux = max(mois_d_ifc(bareme, n) / n for n in _HORIZON)
    return BaremeTranches(forme="tranches_cumulatives",
                          tranches=[{"jusqu_a": None, "mois_par_annee": min(_haut(taux, 0.05), _TAUX_MAX)}])


def _categorie(nom: str, convention: Convention, bareme) -> dict:
    return {"categorie": nom, "convention_code": convention.code, "bareme": bareme.model_dump(mode="json"),
            "anciennete_minimale": 0, "plafond_mois": None, "arrondi": "annees", "base_salaire": "dernier",
            "avec_primes": False, "evenements": ["retraite"]}


def _categories(modele: str, convention: Convention) -> list[dict]:
    b = convention.bareme
    if modele == "minimum":
        return [_categorie("*", convention, b)]
    if modele == "plus_25":
        return [_categorie("*", convention, _multiplier(b, 1.25))]
    if modele == "cadres":
        return [_categorie("Cadre", convention, _multiplier(b, 1.5)), _categorie("*", convention, b)]
    return [_categorie("*", convention, _taux_unique(b))]


def modeles_du_pays(ref: Referentiel, pays: str, jour: date) -> list[dict]:
    """Quatre modèles par convention du pays en vigueur ce jour-là ; aucun pour un pays sans convention."""
    modeles = []
    for convention in sorted(ref.conventions_du_pays(pays, jour), key=lambda c: c.code):
        for modele, (titre, description) in MODELES.items():
            categories = _categories(modele, convention)
            baremes = {c["categorie"]: (BaremeTranches if c["bareme"]["forme"] == "tranches_cumulatives"
                                        else BaremePaliers).model_validate(c["bareme"]) for c in categories}
            modeles.append({
                "code": f"{convention.code}:{modele}", "modele": modele, "titre": titre, "description": description,
                "convention": {"code": convention.code, "libelle": convention.libelle, "statut": convention.statut},
                "version": {"en_vigueur_du": None, "fondement": "accord_entreprise",
                            "document_reference": f"Modèle type de la plateforme : {titre} ({convention.libelle})",
                            "categories": categories},
                # Ce que le modèle donne, en mois de salaire, face au minimum : pour choisir sans calculer.
                "illustration": [{"anciennete": n, "minimum": round(mois_d_ifc(convention.bareme, n), 2),
                                  "par_categorie": {nom: round(mois_d_ifc(b, n), 2) for nom, b in baremes.items()}}
                                 for n in ANCIENNETES],
            })
    return modeles
