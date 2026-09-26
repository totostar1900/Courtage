"""Simulation : la convention seule, puis chaque variante, sur le vrai personnel de l'entreprise.

Une simulation n'engage personne et n'écrit rien : ni étude, ni version, ni
journal. Une variante est une version de régime existante (adoptée ou non) ou
des catégories saisies à la volée. Une variante qui ne couvre pas tout le
personnel rend son erreur sans empêcher les autres d'être calculées.
"""
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from courtage.actuariat.ifc import Regles, Resultat, evaluer
from courtage.analyse import concentration
from courtage.db import Organisation
from courtage.erreurs import ErreurMetier
from courtage.fichier import salaries
from courtage.referentiel import referentiel_courant

from . import etudes, fichiers, regimes

MAX_VARIANTES = 6
TETE = 5   # les cinq premiers bénéficiaires


@dataclass
class Variante:
    nom: str
    regime_version_id: uuid.UUID | None = None
    categories: list[regimes.SaisieCategorie] | None = None


def simuler(session: Session, org: Organisation, *, fichier_id: uuid.UUID, date_evaluation: date,
            convention_code: str, fonds_disponible: int, hypotheses: dict, variantes: list[Variante]) -> dict:
    if len(variantes) > MAX_VARIANTES:
        raise ErreurMetier("trop_de_variantes", f"Au plus {MAX_VARIANTES} variantes à la fois.", 422)
    for v in variantes:
        if (v.regime_version_id is None) == (v.categories is None):
            raise ErreurMetier("variante_ambigue",
                               f"« {v.nom} » : une version de régime OU des catégories, pas les deux ni aucune.", 422)
        for c in v.categories or []:
            regimes.valider_categorie(org, c, date_evaluation)
    try:
        convention = referentiel_courant().convention(convention_code, date_evaluation)
    except LookupError as e:
        raise ErreurMetier("convention_introuvable", str(e), 422) from None

    lecture = fichiers.relire(fichiers.obtenir(session, fichier_id))
    sal = salaries(lecture)
    h = etudes.hypotheses_moteur(_valeurs(hypotheses), date_evaluation, fonds_disponible)

    base = evaluer(sal, h, convention, regles={"*": Regles(bareme=convention.bareme)})
    resultats = [_resume("Convention seule", {"convention": convention.code}, base, base, sal, fonds_disponible,
                         date_evaluation, [])]
    for v in variantes:
        try:
            regles, constats, source = _regles_de_la_variante(session, v, date_evaluation)
            etudes.exiger_categories_connues(lecture, regles)
        except ErreurMetier as e:
            resultats.append({"nom": v.nom, "erreur": {"code": e.code, "message": e.message, "details": e.details}})
            continue
        r = evaluer(sal, h, convention, regles=regles)
        resultats.append(_resume(v.nom, source, r, base, sal, fonds_disponible, date_evaluation, constats))
    return {"date_evaluation": date_evaluation.isoformat(), "convention": convention.code,
            "hypotheses": _valeurs(hypotheses), "fonds_disponible": fonds_disponible, "resultats": resultats}


def _regles_de_la_variante(session: Session, v: Variante, jour: date):
    if v.regime_version_id is not None:
        version = regimes.obtenir_version(session, v.regime_version_id)
        return (regimes.regles(session, version, jour), regimes.constats(session, version, jour),
                {"regime_version_id": str(version.id), "numero": version.numero, "statut": version.statut})
    ref = referentiel_courant()
    regles = {c.categorie: regimes.regles_de(c, ref.convention(c.convention_code, jour)) for c in v.categories}
    return regles, regimes.constats_categories(v.categories, jour), {"saisie": True}


def _resume(nom: str, source: dict, r: Resultat, base: Resultat, sal, fonds: int, jour: date,
            constats: list[dict]) -> dict:
    dettes = sorted((l.dette for l in r.lignes), reverse=True)
    total = sum(dettes) or 1.0
    c = concentration(r, base, sal)
    return {
        "nom": nom, "source": source,
        "totaux": {"effectif": r.totaux.effectif, "vapf": r.totaux.vapf, "dette": r.totaux.dette,
                   "charge": r.totaux.charge},
        "charge_annuelle": r.totaux.charge,
        "cotisation_initiale": max(r.totaux.dette - fonds, 0),
        "ecart_convention": r.totaux.dette - base.totaux.dette,
        "echeancier": etudes.echeancier(r, jour),
        "par_categorie": r.par_categorie,
        "part_cinq_premiers": round(sum(dettes[:TETE]) / total, 4),
        "concentration": {"niveau": c.niveau, **c.chiffres} if c else None,
        "constats": constats,
    }


def _valeurs(saisies: dict) -> dict:
    return etudes.hypotheses.valeurs_et_ecarts(saisies)[0]
