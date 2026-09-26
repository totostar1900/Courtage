"""Services métier. Chaque fonction reçoit une `Session` déjà placée dans le
contexte de l'organisation (RLS) et ne s'occupe pas des droits : c'est la
couche API qui dit qui a le droit d'appeler quoi."""
import uuid

from sqlalchemy import insert
from sqlalchemy.orm import Session

from courtage.db import EntreeJournal


def journaliser(session: Session, organisation_id: uuid.UUID | None, utilisateur_id: uuid.UUID | None,
                action: str, cible, details: dict | None = None) -> None:
    # Sans RETURNING : la politique de LECTURE s'appliquerait à la ligne rendue, et
    # une action de plateforme (sans organisation) n'est lisible par aucun client.
    session.connection().execute(insert(EntreeJournal.__table__).values(
        organisation_id=organisation_id, utilisateur_id=utilisateur_id,
        action=action, cible=str(cible), details=details or {}))
