"""Analyse d'un régime IFC : ce que la plateforme en dit, en constats sourcés.

Module pur, comme le moteur : pas de base, pas de date du jour. Il reçoit le
régime traduit en règles, et s'il y en a un, le personnel ; il rend des
constats `bloque | avertit | informe`, dans cet ordre.

Deux sortes de constats :
- les CALCULS (coût de la non-conformité, dette de passé, concentration) :
  des chiffres, que la plateforme garantit ;
- les NOTES juridiques et fiscales (provisionnement, usage, déductibilité,
  égalité de traitement, abus de biens sociaux) : sourcées, et rédigées comme
  des repères (« selon notre lecture », « pourrait »), jamais comme un avis :
  la plateforme informe, le conseil de l'entreprise tranche. `statut_contenu`
  garde en interne qu'aucun juriste ne les a encore relues.

Les constats de légalité d'une version (sous le plancher, base approchée,
événements non évalués) viennent de `services.regimes.constats`.
"""
from dataclasses import dataclass, field
from math import ceil
from typing import Literal, Sequence

from courtage.actuariat.ifc import Hypotheses, Regles, Salarie, evaluer
from courtage.referentiel import Convention, notes_juridiques

Niveau = Literal["bloque", "avertit", "informe"]
ORDRE: dict[str, int] = {"bloque": 0, "avertit": 1, "informe": 2}
PART_MIEUX_PAYES = 0.10       # le décile des salaires les plus élevés
ECART_CONCENTRATION = 0.15    # 15 points de plus que leur part de la dette conventionnelle


@dataclass(frozen=True)
class Constat:
    niveau: Niveau
    code: str
    titre: str
    message: str
    categorie: str | None = None
    chiffres: dict = field(default_factory=dict)
    sources: list[dict] = field(default_factory=list)
    statut_contenu: Literal["calcul", "valide", "a_valider"] = "calcul"


@dataclass(frozen=True)
class Contexte:
    pays: str
    fondement: str
    categories: list[dict]                       # base_salaire, avec_primes, evenements par catégorie
    convention: Convention                       # la convention principale, pour le moteur
    regles: dict[str, Regles]                    # le régime, plancher compris : ce qui est dû
    regles_texte: dict[str, Regles]              # le régime tel qu'écrit, sans plancher
    regles_plancher: dict[str, Regles]           # la seule convention
    salaries: Sequence[Salarie] | None = None
    hypotheses: Hypotheses | None = None
    regles_precedentes: dict[str, Regles] | None = None   # la version en vigueur la veille


def analyser(ctx: Contexte) -> list[Constat]:
    constats = [*_nature(ctx)]
    if ctx.salaries and ctx.hypotheses is not None:
        constats += _couts(ctx)
    return sorted(constats, key=lambda c: ORDRE[c.niveau])


# --- Nature : les notes -------------------------------------------------------

def _nature(ctx: Contexte) -> list[Constat]:
    constats = [_note("informe", "provisionnement")]
    if ctx.fondement in ("decision_direction", "usage"):
        constats.append(_note("informe", "usage"))
    if f"deductibilite_{ctx.pays}" in notes_juridiques():
        constats.append(_note("informe", f"deductibilite_{ctx.pays}"))
    if len(ctx.categories) > 1:
        constats.append(_note("informe", "egalite_de_traitement"))
    for c in ctx.categories:
        if c.get("avec_primes"):
            constats.append(Constat(
                "avertit", "base_avec_primes", "La base de salaire inclut les primes",
                ("Tout le personnel" if c["categorie"] == "*" else f"Catégorie « {c['categorie']} »")
                + " : inclure les primes gonfle la dette et rend le calcul "
                "dépendant de leur définition. Préciser lesquelles, et vérifier que le fichier les contient.",
                categorie=c["categorie"]))
    return constats


def _note(niveau: Niveau, id_note: str) -> Constat:
    n = notes_juridiques()[id_note]
    return Constat(niveau, id_note, n.titre, n.texte, sources=[s.model_dump(mode="json") for s in n.sources],
                   statut_contenu=n.statut)


# --- Coûts : les calculs ------------------------------------------------------

def _couts(ctx: Contexte) -> list[Constat]:
    def evaluation(regles):
        return evaluer(ctx.salaries, ctx.hypotheses, ctx.convention, regles=regles)

    retenue = evaluation(ctx.regles)
    texte = evaluation(ctx.regles_texte)
    plancher = evaluation(ctx.regles_plancher)
    constats = []

    ecart = retenue.totaux.dette - texte.totaux.dette
    if ecart > 0:
        constats.append(Constat(
            "avertit", "cout_non_conformite", "Ce que le texte du régime ne dit pas",
            f"Lu à la lettre, le régime donnerait une dette de {_f(texte.totaux.dette)} ; parce que les salariés "
            f"gardent droit à la convention, la dette réelle est de {_f(retenue.totaux.dette)}. "
            f"Écart : {_f(ecart)}.",
            chiffres={"dette_selon_le_texte": texte.totaux.dette, "dette_retenue": retenue.totaux.dette,
                      "ecart": ecart}))

    reference, libelle = ((evaluation(ctx.regles_precedentes), "version_precedente")
                          if ctx.regles_precedentes else (plancher, "convention"))
    supplement = retenue.totaux.dette - reference.totaux.dette
    face_a = "la version précédente" if libelle == "version_precedente" else "la seule convention"
    constats.append(Constat(
        "informe", "dette_de_passe", "La dette créée pour le passé",
        f"Adopter ce régime porte la dette, pour les années déjà travaillées, de {_f(reference.totaux.dette)} "
        f"({face_a}) à {_f(retenue.totaux.dette)} : {_f(supplement)} à financer, en une fois ou en plusieurs.",
        chiffres={"reference": libelle, "dette_reference": reference.totaux.dette,
                  "dette_regime": retenue.totaux.dette, "supplement": supplement}))

    c = concentration(retenue, plancher, ctx.salaries)
    if c is not None:
        constats.append(c)
    return constats


def concentration(retenue, plancher, salaries: Sequence[Salarie]) -> Constat | None:
    """À qui profite ce que le régime ajoute à la convention ?"""
    au_plancher = {l.matricule: l.dette for l in plancher.lignes}
    surplus = {l.matricule: max(l.dette - au_plancher[l.matricule], 0.0) for l in retenue.lignes}
    total_surplus = sum(surplus.values())
    if total_surplus <= 0:
        return None
    n = max(1, ceil(PART_MIEUX_PAYES * len(salaries)))
    mieux_payes = {s.matricule for s in sorted(salaries, key=lambda s: -s.salaire_annuel)[:n]}
    part_surplus = sum(surplus[m] for m in mieux_payes) / total_surplus
    total_plancher = sum(au_plancher.values()) or 1.0
    part_plancher = sum(au_plancher[m] for m in mieux_payes) / total_plancher
    chiffres = {"effectif_mieux_payes": n, "part_des_mieux_payes": round(part_surplus, 4),
                "part_dans_la_dette_conventionnelle": round(part_plancher, 4)}
    message = (f"{_pct(part_surplus)} de ce que le régime ajoute à la convention va aux {n} salariés les mieux "
               f"payés, qui portent {_pct(part_plancher)} de la dette conventionnelle.")
    if part_surplus - part_plancher > ECART_CONCENTRATION:
        n_abs = notes_juridiques()["abus_de_biens_sociaux"]
        return Constat("avertit", "concentration", "Un régime qui profite surtout aux mieux payés",
                       message + " " + n_abs.texte, chiffres=chiffres,
                       sources=[s.model_dump(mode="json") for s in n_abs.sources], statut_contenu=n_abs.statut)
    return Constat("informe", "concentration", "À qui profite le régime", message, chiffres=chiffres)


def _f(montant: int | float) -> str:
    return f"{round(montant):,}".replace(",", " ") + " F"


def _pct(x: float) -> str:
    return f"{x * 100:.0f} %"
