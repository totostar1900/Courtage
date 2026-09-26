"""API HTTP (FastAPI), sous /api/v1.

Chaque requête ouvre UNE transaction : les droits sont vérifiés sur les
adhésions, puis la transaction est placée dans le contexte de l'organisation
(RLS) avant tout accès aux données du client. Une erreur annule tout ce que la
requête avait écrit.

L'authentification réelle arrive à la tâche 8. D'ici là, le mode `entete_dev`
lit l'identité dans l'en-tête `X-Utilisateur` : il est refusé au démarrage en
production.
"""
import os
import uuid
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from courtage.db import Adhesion, Organisation, Utilisateur, contexte
from courtage.erreurs import ErreurMetier
from courtage.services.rapport import ConfigSceau

ModeAuthentification = Literal["entete_dev", "aucune"]


def creer_app(moteur: Engine, authentification: ModeAuthentification = "aucune",
              cle_sceau: bytes | None = None, url_publique: str | None = None) -> FastAPI:
    production = os.environ.get("COURTAGE_ENV") == "production"
    if production and authentification == "entete_dev":
        raise RuntimeError("L'identité par en-tête est réservée au développement et aux tests.")
    if production and not cle_sceau:
        raise RuntimeError("Clé de sceau absente : un rapport émis en production doit être probant.")
    app = FastAPI(title="Courtage", version="0.1.0")
    app.state.moteur = moteur
    app.state.authentification = authentification
    app.state.sceau = ConfigSceau.depuis(cle_sceau, url_publique)

    @app.exception_handler(ErreurMetier)
    async def _erreur_metier(_: Request, e: ErreurMetier):
        return JSONResponse({"code": e.code, "message": e.message, "details": e.details}, status_code=e.statut)

    from .routes import routeur
    app.include_router(routeur, prefix="/api/v1")
    return app


# --- Dépendances --------------------------------------------------------------

def session_db(request: Request):
    with Session(request.app.state.moteur, expire_on_commit=False) as session:
        with session.begin():
            yield session


def identite(request: Request, session: Session = Depends(session_db),
             x_utilisateur: str | None = Header(default=None)) -> Utilisateur:
    if request.app.state.authentification != "entete_dev" or not x_utilisateur:
        raise ErreurMetier("non_authentifie", "Identifiez-vous.", 401)
    try:
        utilisateur = session.get(Utilisateur, uuid.UUID(x_utilisateur))
    except ValueError:
        utilisateur = None
    if utilisateur is None:
        raise ErreurMetier("non_authentifie", "Identité inconnue.", 401)
    return utilisateur


@dataclass
class Acces:
    organisation: Organisation
    utilisateur: Utilisateur
    role: str
    session: Session


def acces(*roles: str):
    """Membre de l'organisation, avec l'un des rôles donnés (tous si aucun), puis contexte RLS."""
    def dependance(organisation_id: uuid.UUID, session: Session = Depends(session_db),
                   moi: Utilisateur = Depends(identite)) -> Acces:
        role = session.scalar(select(Adhesion.role).where(
            Adhesion.utilisateur_id == moi.id, Adhesion.organisation_id == organisation_id))
        if role is None:
            raise ErreurMetier("acces_refuse", "Vous n'êtes pas membre de cette organisation.", 403)
        if roles and role not in roles:
            raise ErreurMetier("acces_refuse", "Votre rôle ne permet pas cette action.", 403)
        organisation = session.get(Organisation, organisation_id)
        contexte(session.connection(), organisation_id)
        return Acces(organisation, moi, role, session)
    return dependance
