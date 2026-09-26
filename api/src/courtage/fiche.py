"""Agrégats publiables d'une population : ce qu'un assureur reçoit, sans rien d'individuel.

Module pur. Deux règles, parce qu'une petite entreprise se lit à travers ses
agrégats :
- une case de moins de SEUIL personnes est masquée (« <3 ») ; une catégorie
  masquée ne donne pas sa masse salariale ;
- l'échéancier des départs est publié par périodes de cinq ans, et une période
  de moins de SEUIL départs est fusionnée avec la suivante (la dernière avec
  la précédente) : le montant d'un départ isolé dirait le salaire d'une
  personne.
Aucun matricule, aucune date, aucun salaire individuel n'entre dans le résultat.
"""
from collections import Counter, defaultdict

SEUIL = 3
AMPLITUDE = 5


def masque(n: int) -> int | str:
    return n if n >= SEUIL else f"<{SEUIL}"


def agreger_population(lignes: list[dict], salaires: list[int]) -> dict:
    """`lignes` : âge, ancienneté, catégorie de chaque salarié ; `salaires` : annuels, dans le même ordre."""
    n = len(lignes)
    effectif_par_categorie = Counter(l["categorie"] or "*" for l in lignes)
    masse_par_categorie: dict[str, int] = defaultdict(int)
    for l, s in zip(lignes, salaires):
        masse_par_categorie[l["categorie"] or "*"] += s
    return {
        "effectif": n,
        "masse_salariale": sum(salaires),
        "age_moyen": round(sum(l["age"] for l in lignes) / n, 1) if n else None,
        "anciennete_moyenne": round(sum(l["anciennete"] for l in lignes) / n, 1) if n else None,
        "pyramide_des_ages": _tranches(l["age"] for l in lignes),
        "anciennetes": _tranches(l["anciennete"] for l in lignes),
        "par_categorie": {
            c: {"effectif": masque(k), "masse_salariale": masse_par_categorie[c] if k >= SEUIL else None}
            for c, k in sorted(effectif_par_categorie.items())
        },
    }


def regrouper_echeancier(echeancier: list[dict], depuis: int) -> list[dict]:
    """Les départs et prestations probables par périodes de cinq ans, chaque groupe d'au moins SEUIL départs."""
    periodes: dict[int, dict] = {}
    for a in echeancier:
        debut = depuis + (max(a["annee"], depuis) - depuis) // AMPLITUDE * AMPLITUDE
        p = periodes.setdefault(debut, {"debut": debut, "fin": debut + AMPLITUDE - 1, "departs": 0,
                                        "prestations_probables": 0})
        p["departs"] += a["effectif"]
        p["prestations_probables"] += a["prestations_probables"]
    groupes: list[dict] = []
    en_cours = None
    for p in (periodes[k] for k in sorted(periodes)):
        en_cours = p if en_cours is None else _fusion(en_cours, p)
        if en_cours["departs"] >= SEUIL:
            groupes.append(en_cours)
            en_cours = None
    if en_cours is not None:
        if groupes:
            groupes[-1] = _fusion(groupes[-1], en_cours)
        else:
            groupes.append(en_cours)   # moins de SEUIL départs en tout : un seul groupe, le montant reste global
    return [{"periode": f"{g['debut']}-{g['fin']}", "departs": g["departs"],
             "prestations_probables": g["prestations_probables"]} for g in groupes]


def _fusion(a: dict, b: dict) -> dict:
    return {"debut": a["debut"], "fin": b["fin"], "departs": a["departs"] + b["departs"],
            "prestations_probables": a["prestations_probables"] + b["prestations_probables"]}


def _tranches(valeurs) -> list[dict]:
    compte = Counter(int(v) // AMPLITUDE * AMPLITUDE for v in valeurs)
    return [{"tranche": f"{t}-{t + AMPLITUDE - 1}", "effectif": masque(k)} for t, k in sorted(compte.items())]
