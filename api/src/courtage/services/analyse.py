"""Analyse d'une version de régime : la légalité (services.regimes), la nature et les coûts
(courtage.analyse), en une seule table de constats."""
import uuid
from dataclasses import asdict, replace
from datetime import date, timedelta

from sqlalchemy.orm import Session

from courtage.analyse import ORDRE, Contexte, analyser
from courtage.db import Organisation, VersionRegime
from courtage.fichier import salaries
from courtage.referentiel import HYPOTHESES_PAR_DEFAUT

from . import etudes, fichiers, regimes


def analyser_version(session: Session, org: Organisation, version: VersionRegime, *,
                     fichier_id: uuid.UUID | None = None, date_evaluation: date | None = None) -> dict:
    jour = date_evaluation or version.en_vigueur_du
    regles = regimes.regles(session, version, jour)
    categories = regimes.categories_de(session, version)

    sal = h = None
    if fichier_id is not None:
        lecture = fichiers.relire(fichiers.obtenir(session, fichier_id))
        etudes.exiger_categories_connues(lecture, regles)
        sal = salaries(lecture)
        h = etudes.hypotheses_moteur(dict(HYPOTHESES_PAR_DEFAUT), jour)

    veille = regimes.version_en_vigueur(session, version.regime_id, version.en_vigueur_du - timedelta(days=1))
    precedentes = regimes.regles(session, veille, jour) if veille is not None and veille.id != version.id else None

    ctx = Contexte(
        pays=org.pays, fondement=version.fondement,
        categories=[{"categorie": c.categorie, "base_salaire": c.base_salaire, "avec_primes": c.avec_primes,
                     "evenements": list(c.evenements)} for c in categories],
        convention=regimes.conventions_de(session, version, jour)[0],
        regles=regles, regles_texte={k: replace(r, plancher=None) for k, r in regles.items()},
        regles_plancher=regimes.regles_plancher(session, version, jour),
        salaries=sal, hypotheses=h, regles_precedentes=precedentes,
    )
    legaux = [{"niveau": c["niveau"], "code": c["code"], "titre": _TITRES.get(c["code"], c["code"]),
               "message": c["message"], "categorie": c["categorie"], "chiffres": c["details"],
               "sources": [], "statut_contenu": "calcul"} for c in regimes.constats(session, version, jour)]
    constats = sorted(legaux + [asdict(c) for c in analyser(ctx)], key=lambda c: ORDRE[c["niveau"]])
    return {"version_id": str(version.id), "date": jour.isoformat(),
            "avec_personnel": fichier_id is not None, "constats": constats}


_TITRES = {
    "sous_le_plancher": "Sous la convention collective",
    "base_salaire_approchee": "Base de salaire approchée",
    "evenements_non_evalues": "Événements couverts mais non chiffrés",
    "convention_introuvable": "Convention introuvable",
}
