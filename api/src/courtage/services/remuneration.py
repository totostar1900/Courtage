"""Conditions de rémunération d'un client (décision du 2026-09-26 : modèle mixte paramétrable).

Des conditions ne se modifient pas ; de nouvelles s'ajoutent avec leur date
d'effet. Les conditions applicables à un jour sont les dernières entrées en
vigueur ce jour-là.
"""
import uuid
from datetime import date
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from courtage.db import ConditionsRemuneration, Etude
from courtage.erreurs import ErreurMetier

from . import journaliser

Mode = Literal["honoraires", "commission", "mixte"]


def verifier_coherence(mode: Mode, honoraires_etude_ifc: int, honoraires_par_salarie: int, commission_bps: int) -> None:
    honoraires = honoraires_etude_ifc + honoraires_par_salarie
    attendus = {
        "honoraires": (honoraires > 0 and commission_bps == 0, "des honoraires et aucune commission"),
        "commission": (honoraires == 0 and commission_bps > 0, "une commission et aucun honoraire"),
        "mixte": (honoraires > 0 and commission_bps > 0, "des honoraires et une commission"),
    }
    ok, attendu = attendus[mode]
    if not ok:
        raise ErreurMetier("remuneration_incoherente", f"Le mode « {mode} » demande {attendu}.", 422)


def fixer(session: Session, organisation_id: uuid.UUID, auteur: uuid.UUID, *, en_vigueur_du: date, mode: Mode,
          honoraires_etude_ifc: int = 0, honoraires_par_salarie: int = 0, commission_bps: int = 0,
          note: str | None = None) -> ConditionsRemuneration:
    verifier_coherence(mode, honoraires_etude_ifc, honoraires_par_salarie, commission_bps)
    conditions = ConditionsRemuneration(
        organisation_id=organisation_id, en_vigueur_du=en_vigueur_du, mode=mode,
        honoraires_etude_ifc=honoraires_etude_ifc, honoraires_par_salarie=honoraires_par_salarie,
        commission_bps=commission_bps, note=note, cree_par=auteur)
    session.add(conditions)
    try:
        session.flush()
    except IntegrityError as e:
        if "conditions_remuneration_organisation_id_en_vigueur_du_key" in str(e.orig):
            raise ErreurMetier("remuneration_deja_fixee",
                               f"Des conditions prennent déjà effet le {en_vigueur_du:%d/%m/%Y}.", 409) from None
        raise
    journaliser(session, organisation_id, auteur, "remuneration.fixee", conditions.id,
                {"mode": mode, "en_vigueur_du": en_vigueur_du.isoformat()})
    return conditions


def historique(session: Session) -> list[ConditionsRemuneration]:
    return list(session.scalars(select(ConditionsRemuneration).order_by(ConditionsRemuneration.en_vigueur_du.desc())))


def en_vigueur(session: Session, jour: date) -> ConditionsRemuneration | None:
    return session.scalars(
        select(ConditionsRemuneration)
        .where(ConditionsRemuneration.en_vigueur_du <= jour)
        .order_by(ConditionsRemuneration.en_vigueur_du.desc())
        .limit(1)
    ).first()


def honoraires_etude(conditions: ConditionsRemuneration, effectif: int) -> int:
    """Honoraires HT d'une étude IFC : un forfait, plus une part par salarié évalué."""
    return conditions.honoraires_etude_ifc + conditions.honoraires_par_salarie * effectif


def en_clair(c: ConditionsRemuneration) -> dict:
    return {
        "id": str(c.id), "en_vigueur_du": c.en_vigueur_du.isoformat(), "mode": c.mode,
        "honoraires_etude_ifc": c.honoraires_etude_ifc, "honoraires_par_salarie": c.honoraires_par_salarie,
        "commission_bps": c.commission_bps, "note": c.note,
    }


def raison_de_garder(session: Session, c: ConditionsRemuneration) -> str | None:
    """Des conditions sur lesquelles une étude a calculé ses honoraires restent ; sinon elles se suppriment."""
    n = session.scalar(select(func.count()).select_from(Etude).where(Etude.conditions_remuneration_id == c.id)) or 0
    return f"{n} étude{'s' if n > 1 else ''} en {'ont' if n > 1 else 'a'} tiré ses honoraires : elles restent." if n else None


def supprimer(session: Session, c: ConditionsRemuneration, auteur: uuid.UUID) -> None:
    if raison := raison_de_garder(session, c):
        raise ErreurMetier("conditions_utilisees", raison, 409)
    journaliser(session, c.organisation_id, auteur, "remuneration.supprimee", c.id,
                {"en_vigueur_du": c.en_vigueur_du.isoformat(), "mode": c.mode})
    session.delete(c)
    session.flush()
