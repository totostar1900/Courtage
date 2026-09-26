"""Routes de connexion : demander un code, le vérifier, se déconnecter. Publiques, sauf la déconnexion."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from courtage import auth
from courtage.auth.telephone import normaliser
from courtage.db import Utilisateur
from courtage.erreurs import ErreurMetier
from courtage.services import journaliser

from . import COOKIE, identite, session_db

routeur_connexion = APIRouter()

REPONSE_DEMANDE = {"message": "Si ce numéro est inscrit, un code vient d'être envoyé. Il expire dans 10 minutes."}


class DemandeCode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    telephone: str = Field(min_length=1, max_length=30)


class Verification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    telephone: str = Field(min_length=1, max_length=30)
    code: str = Field(min_length=1, max_length=10)
    application: bool = False      # une application garde le jeton ; un navigateur n'a que le cookie


@routeur_connexion.get("/mode")
def mode(request: Request):
    return {"mode": request.app.state.authentification}


@routeur_connexion.post("/code")
def demander_code(corps: DemandeCode, request: Request, session: Session = Depends(session_db)):
    telephone = _numero(corps.telephone)
    auth.demander_code(session, telephone, request.app.state.expediteur, request.app.state.cle_auth)
    return REPONSE_DEMANDE


@routeur_connexion.post("/verification")
def verifier(corps: Verification, request: Request, session: Session = Depends(session_db)):
    telephone = _numero(corps.telephone)
    utilisateur = auth.verifier_code(session, telephone, corps.code, request.app.state.cle_auth)
    if utilisateur is None:
        # Pas d'exception : elle annulerait la transaction, et avec elle le compte des essais.
        return JSONResponse({"code": "code_invalide", "message": "Code incorrect ou expiré. Demandez-en un nouveau.",
                             "details": {}}, status_code=401)
    jeton = auth.ouvrir_session(session, utilisateur, request.headers.get("user-agent"))
    journaliser(session, None, utilisateur.id, "connexion", utilisateur.id)
    corps_reponse = {"utilisateur": {"id": str(utilisateur.id), "nom_affiche": utilisateur.nom_affiche}}
    if corps.application:
        corps_reponse["jeton"] = jeton
    reponse = JSONResponse(corps_reponse)
    reponse.set_cookie(COOKIE, jeton, max_age=int(auth.DUREE_SESSION.total_seconds()), httponly=True,
                       samesite="lax", secure=request.app.state.cookie_securise, path="/")
    return reponse


@routeur_connexion.post("/deconnexion")
def deconnexion(request: Request, session: Session = Depends(session_db), _: Utilisateur = Depends(identite)):
    jeton = request.cookies.get(COOKIE)
    en_tete = request.headers.get("authorization", "")
    if en_tete.lower().startswith("bearer "):
        jeton = en_tete[7:].strip()
    if jeton:
        auth.revoquer(session, jeton)
    reponse = JSONResponse({"message": "Déconnecté."})
    reponse.delete_cookie(COOKIE, path="/")
    return reponse


def _numero(saisi: str) -> str:
    try:
        return normaliser(saisi)
    except ValueError:
        raise ErreurMetier("telephone_invalide", "Numéro de téléphone invalide.", 422) from None
