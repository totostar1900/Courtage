"""L'essai sans compte : le personnel, le fonds, le régime, et l'étude à l'écran — rien n'est gardé.

Aucune session de base n'est ouverte : le fichier est lu en mémoire, le calcul rendu, puis tout est oublié. Pas de
sceau, pas d'export, pas de journal du contenu. Les hypothèses sont celles du référentiel (les changer, c'est le
travail d'un dossier). 300 salariés au plus : au-delà, on s'inscrit.
"""
from dataclasses import asdict
from datetime import date
from types import SimpleNamespace

from courtage.actuariat.ifc import evaluer
from courtage.erreurs import ErreurMetier
from courtage.fichier import lire_fichier, salaries
from courtage.fichier.controles import controler, controler_resultat
from courtage.referentiel import referentiel_courant

from . import etudes, regimes
from .fichiers import _STRUCTURELS

MAX_SALARIES = 300
PAYS = {"CM", "GA", "CG", "TD", "CF", "GQ"}


def evaluer_essai(*, contenu: bytes, nom_fichier: str, pays: str, date_evaluation: date, fonds_disponible: int,
                  convention_code: str, categories: list[regimes.SaisieCategorie] | None = None) -> dict:
    if pays not in PAYS:
        raise ErreurMetier("hors_cemac", "L'essai couvre les pays de la CEMAC.", 422)
    lecture = lire_fichier(contenu, nom_fichier)
    structurels = [a for a in lecture.anomalies if a.code in _STRUCTURELS]
    if structurels:
        raise ErreurMetier("fichier_illisible", structurels[0].message, 422)
    if len(lecture.lignes) > MAX_SALARIES:
        raise ErreurMetier("essai_trop_grand", f"L'essai porte sur {MAX_SALARIES} salariés au plus : inscrivez-vous "
                           "pour évaluer tout votre personnel.", 422, {"effectif": len(lecture.lignes)})
    ref = referentiel_courant()
    try:
        convention = ref.convention(convention_code, date_evaluation)
    except LookupError as e:
        raise ErreurMetier("convention_introuvable", str(e), 422) from None
    if convention.pays != pays:
        raise ErreurMetier("convention_autre_pays", f"{convention.code} n'est pas une convention de {pays}.", 422)
    regles = None
    if categories:
        for c in categories:
            regimes.valider_categorie(SimpleNamespace(pays=pays), c, date_evaluation)
        regles = {c.categorie: regimes.regles_de(c, ref.convention(c.convention_code, date_evaluation))
                  for c in categories}
        etudes.exiger_categories_connues(lecture, regles)
    h = etudes.hypotheses_moteur(etudes.hypotheses.valeurs_et_ecarts({})[0], date_evaluation, fonds_disponible)
    sal = salaries(lecture)
    r = evaluer(sal, h, convention, regles=regles)
    anomalies = [*lecture.anomalies, *controler(lecture, date_evaluation=date_evaluation, age_retraite=h.age_retraite),
                 *controler_resultat(r)]
    sensibilites = etudes._sensibilites(sal, h, convention, regles)
    principale = sensibilites.get("taux_actualisation_moins_1pt")
    return {
        "effectif": len(lecture.lignes), "convention": {"code": convention.code, "libelle": convention.libelle},
        "date_evaluation": date_evaluation.isoformat(), "fonds_disponible": fonds_disponible,
        "totaux": etudes._totaux(r), "echeancier": etudes.echeancier(r, date_evaluation),
        "sensibilite": None if principale is None else {"libelle": "Taux d'actualisation − 1 point", **principale},
        "anomalies": [asdict(a) for a in anomalies][:20], "nombre_anomalies": len(anomalies),
        "non_scelle": True,
    }
