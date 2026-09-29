"""API HTTP (FastAPI), sous /api/v1.

Chaque requête ouvre UNE transaction : les droits sont vérifiés sur les
adhésions, puis la transaction est placée dans le contexte de l'organisation
(RLS) avant tout accès aux données du client. Une erreur annule tout ce que la
requête avait écrit.

Identité (tâche 8) : une session ouverte par un code reçu par téléphone
(`courtage.auth`), portée par le cookie `courtage_session` (navigateur) ou par
`Authorization: Bearer` (application). Une ÉCRITURE authentifiée par cookie
exige l'en-tête `X-Courtage: 1` : un autre site peut faire envoyer le cookie,
pas poser un en-tête (protection CSRF). Le mode `entete_dev` accepte en plus
l'en-tête `X-Utilisateur` ; il est refusé au démarrage en production.
"""
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi import Cookie, Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from courtage import auth
from courtage.db import Adhesion, Organisation, Utilisateur, contexte
from courtage.erreurs import ErreurMetier
from courtage.langue import t
from courtage.messagerie import ExpediteurJournal
from courtage.services import cycle
from courtage.services.rapport import ConfigSceau

__all__ = ["creer_app"]

ModeAuthentification = Literal["session", "entete_dev"]
COOKIE = "courtage_session"
_SURES = {"GET", "HEAD", "OPTIONS"}
# Des POST qui calculent sans rien enregistrer, et le changement d'état lui-même : permis sur un dossier clôturé.
_SANS_ECRITURE = ("/simulations", "/financement", "/cycle")


def creer_app(moteur: Engine, authentification: ModeAuthentification = "session",
              cle_sceau: bytes | None = None, url_publique: str | None = None,
              expediteur=None, cle_auth: bytes | None = None, dossier_web: Path | str | None = None,
              extracteur=None, courriel=None) -> FastAPI:
    """`dossier_web` : l'interface construite (`web/dist`), servie par la même application — une
    seule origine, donc un cookie de session sans CORS ni domaine tiers."""
    production = os.environ.get("COURTAGE_ENV") == "production"
    if production and authentification == "entete_dev":
        raise RuntimeError("L'identité par en-tête est réservée au développement et aux tests.")
    if production and not cle_sceau:
        raise RuntimeError("Clé de sceau absente : un rapport émis en production doit être probant.")
    if production and (not cle_auth or expediteur is None or isinstance(expediteur, ExpediteurJournal)):
        raise RuntimeError("Connexion : en production, il faut une clé d'authentification et un vrai "
                           "fournisseur d'envoi de messages.")
    app = FastAPI(title="Courtage", version="0.1.0")
    from courtage.langue import MiddlewareLangue
    app.add_middleware(MiddlewareLangue)
    from .securite import installer
    installer(app, production)          # en-têtes de sécurité, erreur 500 numérotée, alerte
    app.state.moteur = moteur
    app.state.authentification = authentification
    app.state.sceau = ConfigSceau.depuis(cle_sceau, url_publique)
    app.state.expediteur = expediteur or ExpediteurJournal()
    from courtage.messagerie import CourrielJournal
    app.state.courriel = courriel or CourrielJournal()
    app.state.cle_auth = cle_auth or auth.CLE_DE_DEVELOPPEMENT
    from courtage.extraction.regles import ExtracteurRegles
    app.state.extracteur = extracteur or ExtracteurRegles()
    app.state.cookie_securise = production or os.environ.get("COURTAGE_ENV") == "recette"
    from .limites import Limiteur
    app.state.limites = {
        "verification": Limiteur(30, 60),        # la vérification publique : 30 par minute et par adresse
        "demande_code": Limiteur(10, 15 * 60),   # des codes pour 10 numéros par quart d'heure et par adresse
        "essai_code": Limiteur(30, 15 * 60),
        "inscription": Limiteur(5, 60 * 60),     # 5 inscriptions par heure et par adresse
        "essai": Limiteur(20, 60 * 60),          # l'essai sans compte : 20 calculs par heure et par adresse
    }

    @app.exception_handler(ErreurMetier)
    async def _erreur_metier(_: Request, e: ErreurMetier):
        return JSONResponse({"code": e.code, "message": e.message, "details": e.details}, status_code=e.statut)

    from .connexion import routeur_connexion
    from .inscription import routeur_inscription
    from .essai import routeur_essai
    from .placement import routeur_placement
    from .profil import routeur_profil
    from .public import routeur_public
    from .routes import routeur
    from .referentiel import routeur_referentiel
    from .sante import routeur_sante
    app.include_router(routeur_sante, prefix="/api/v1")
    app.include_router(routeur_referentiel, prefix="/api/v1")
    app.include_router(routeur_public, prefix="/api/v1")
    app.include_router(routeur_connexion, prefix="/api/v1/auth")
    app.include_router(routeur_inscription, prefix="/api/v1")
    app.include_router(routeur_essai, prefix="/api/v1")
    app.include_router(routeur_profil, prefix="/api/v1")
    app.include_router(routeur_placement, prefix="/api/v1")
    app.include_router(routeur, prefix="/api/v1")
    if authentification == "entete_dev":
        from .dev import routeur_dev
        app.include_router(routeur_dev, prefix="/api/v1/dev")
    if dossier_web:
        from .web import servir_interface
        servir_interface(app, Path(dossier_web))
    return app


# --- Dépendances --------------------------------------------------------------

def session_db(request: Request):
    """Une transaction par requête. Toujours `Depends(session_db, scope="function")` : sans cela, FastAPI
    valide APRÈS l'envoi de la réponse, et le navigateur peut lire avant le COMMIT (sur Render, /moi
    répondait 401 juste après la connexion). Un seul scope partout : deux scopes feraient deux sessions."""
    with Session(request.app.state.moteur, expire_on_commit=False) as session:
        # Les avis par courriel partent à la validation (services/avis.py) : l'expéditeur et l'adresse du site.
        session.info["courriel"] = request.app.state.courriel
        session.info["url_publique"] = request.app.state.sceau.url_publique
        with session.begin():
            yield session


def identite(request: Request, session: Session = Depends(session_db, scope="function"),
             x_utilisateur: str | None = Header(default=None),
             authorization: str | None = Header(default=None),
             courtage_session: str | None = Cookie(default=None)) -> Utilisateur:
    porteur = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None
    jeton = porteur or courtage_session
    if jeton:
        utilisateur = auth.utilisateur_du_jeton(session, jeton)
        if utilisateur is not None:
            if porteur is None and request.method not in _SURES and request.headers.get("x-courtage") != "1":
                raise ErreurMetier("csrf", t("Requête refusée : elle ne vient pas de l'application.", "Request refused: it does not come from the application."), 403)
            return utilisateur
    if request.app.state.authentification == "entete_dev" and x_utilisateur:
        try:
            utilisateur = session.get(Utilisateur, uuid.UUID(x_utilisateur))
        except ValueError:
            utilisateur = None
        if utilisateur is not None:
            return utilisateur
    raise ErreurMetier("non_authentifie", t("Connectez-vous.", "Please sign in."), 401)


@dataclass
class Acces:
    organisation: Organisation
    utilisateur: Utilisateur
    role: str
    session: Session


def acces(*roles: str):
    """Membre de l'organisation, avec l'un des rôles donnés (tous si aucun), puis contexte RLS."""
    def dependance(organisation_id: uuid.UUID, request: Request,
                   session: Session = Depends(session_db, scope="function"),
                   moi: Utilisateur = Depends(identite)) -> Acces:
        role = session.scalar(select(Adhesion.role).where(
            Adhesion.utilisateur_id == moi.id, Adhesion.organisation_id == organisation_id))
        if role is None:
            raise ErreurMetier("acces_refuse", t("Vous n'êtes pas membre de cette organisation.", "You are not a member of this organisation."), 403)
        if roles and role not in roles:
            raise ErreurMetier("acces_refuse", t("Votre rôle ne permet pas cette action.", "Your role does not allow this action."), 403)
        organisation = session.get(Organisation, organisation_id)
        # Le cycle de vie : un dossier archivé ne s'ouvre plus ; clôturé, il se lit sans s'écrire (seuls le
        # reprendre et les calculs qui n'enregistrent rien passent).
        cycle.exiger_accessible(organisation)
        if request.method not in _SURES and not request.url.path.endswith(_SANS_ECRITURE):
            cycle.exiger_ecriture(organisation)
        contexte(session.connection(), organisation_id)
        return Acces(organisation, moi, role, session)
    return dependance
