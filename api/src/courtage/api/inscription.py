"""Routes publiques de l'inscription : un code par canal, sa vérification, la création du compte et du dossier.
Et, pour la plateforme, la file des inscriptions à vérifier."""
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from courtage import auth
from courtage.auth.telephone import normaliser
from courtage.db import Justificatif, Organisation, Utilisateur, contexte
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.langue import t
from courtage.services import activation, inscription, journaliser, messages

from . import COOKIE, identite, session_db
from .limites import limite

routeur_inscription = APIRouter()


class _Corps(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DemandeCode(_Corps):
    nature: Literal["telephone", "courriel"]
    cible: str = Field(min_length=3, max_length=200)


class VerificationCode(DemandeCode):
    code: str = Field(min_length=1, max_length=10)


class Entreprise(_Corps):
    nom: str = Field(min_length=2, max_length=200)
    pays: str = Field(pattern=r"^[A-Z]{2}$")
    rccm: str = Field(min_length=3, max_length=80)
    taille: Literal["moins_de_50", "50_a_250", "plus_de_250"]
    secteur: str | None = Field(default=None, max_length=120)
    adresse: str | None = Field(default=None, max_length=300)
    ville: str | None = Field(default=None, max_length=120)


class Inscription(_Corps):
    telephone: str = Field(min_length=3, max_length=30)
    preuve_telephone: str = Field(max_length=200)
    courriel: str = Field(min_length=3, max_length=200)
    preuve_courriel: str = Field(max_length=200)
    nom: str = Field(min_length=2, max_length=120)
    fonction: str | None = Field(default=None, max_length=80)
    entreprise: Entreprise
    application: bool = False


def _cible(nature: str, saisie: str) -> str:
    if nature == "courriel":
        return inscription.normaliser_courriel(saisie)
    try:
        return normaliser(saisie)
    except ValueError:
        raise ErreurMetier("telephone_invalide", t("Numéro de téléphone invalide.", "Invalid phone number."), 422) from None


@routeur_inscription.post("/inscription/code", dependencies=[Depends(limite("demande_code"))])
def demander_code(corps: DemandeCode, request: Request, session: Session = Depends(session_db, scope="function")):
    inscription.demander_code(session, corps.nature, _cible(corps.nature, corps.cible), sms=request.app.state.expediteur,
                              courriel=request.app.state.courriel, cle=request.app.state.cle_auth)
    return {"message": t("Un code vient d'être envoyé. Il expire dans 10 minutes.", "A code has just been sent. It expires in 10 minutes.")}


@routeur_inscription.post("/inscription/verification", dependencies=[Depends(limite("essai_code"))])
def verifier_code(corps: VerificationCode, request: Request, session: Session = Depends(session_db, scope="function")):
    preuve = inscription.verifier_code(session, corps.nature, _cible(corps.nature, corps.cible), corps.code,
                                       request.app.state.cle_auth)
    if preuve is None:
        # Pas d'exception : elle annulerait la transaction, et avec elle le compte des essais.
        return JSONResponse({"code": "code_invalide", "message": t("Code incorrect ou expiré. Demandez-en un nouveau.", "Incorrect or expired code. Request a new one."),
                             "details": {}}, status_code=401)
    return {"preuve": preuve}


@routeur_inscription.post("/inscription", status_code=201, dependencies=[Depends(limite("inscription"))])
def inscrire(corps: Inscription, request: Request, session: Session = Depends(session_db, scope="function")):
    utilisateur, org = inscription.inscrire(
        session, telephone=_cible("telephone", corps.telephone), preuve_telephone=corps.preuve_telephone,
        courriel=_cible("courriel", corps.courriel), preuve_courriel=corps.preuve_courriel, nom=corps.nom,
        fonction=corps.fonction, entreprise=corps.entreprise.model_dump(), cle=request.app.state.cle_auth)
    jeton = auth.ouvrir_session(session, utilisateur, request.headers.get("user-agent"))
    corps_reponse = {"organisation_id": str(org.id), "utilisateur": {"id": str(utilisateur.id), "nom_affiche": utilisateur.nom_affiche},
                     "activation": activation.en_clair(session, org, date.today())}
    if corps.application:
        corps_reponse["jeton"] = jeton
    reponse = JSONResponse(corps_reponse, status_code=201)
    reponse.set_cookie(COOKIE, jeton, max_age=int(auth.DUREE_SESSION.total_seconds()), httponly=True,
                       samesite="lax", secure=request.app.state.cookie_securise, path="/")
    return reponse


# --- La file du courtier -------------------------------------------------------------

def _plateforme(utilisateur: Utilisateur = Depends(identite)) -> Utilisateur:
    if not utilisateur.admin_plateforme:
        raise ErreurMetier("acces_refuse", t("Réservé au courtier (administrateur de la plateforme).", "Reserved for the broker (platform administrator)."), 403)
    return utilisateur


class Verification(_Corps):
    rccm_recu: bool = False
    appel_le: date | None = None
    habilitation: str | None = Field(default=None, max_length=300)      # qui a été joint, à quel titre
    note: str | None = Field(default=None, max_length=2000)


class Decision(_Corps):
    decision: Literal["confirmer", "refuser"]
    verification: Verification | None = None
    motif: str | None = Field(default=None, max_length=1000)
    conseiller_id: uuid.UUID | None = None


@routeur_inscription.get("/inscriptions")
def file_des_inscriptions(session: Session = Depends(session_db, scope="function"), _: Utilisateur = Depends(_plateforme)):
    return {"inscriptions": activation.file_d_attente(session, date.today()),
            "delai_jours_ouvres": activation.DELAI_JOURS_OUVRES}


@routeur_inscription.get("/inscriptions/conseillers")
def lister_conseillers(session: Session = Depends(session_db, scope="function"), moi: Utilisateur = Depends(_plateforme)):
    """Les conseillers entre lesquels répartir les dossiers confirmés. L'entreprise ne choisit pas le sien."""
    return {"conseillers": activation.conseillers(session, moi.id)}


@routeur_inscription.post("/inscriptions/{organisation_id}/decision")
def decider(organisation_id: uuid.UUID, corps: Decision, session: Session = Depends(session_db, scope="function"),
            moi: Utilisateur = Depends(_plateforme)):
    org = session.get(Organisation, organisation_id)
    if org is None:
        raise Introuvable("Inscription")
    activation.decider(session, org, moi.id, decision=corps.decision,
                       verification=corps.verification.model_dump(mode="json") if corps.verification else None,
                       motif=corps.motif, conseiller_id=corps.conseiller_id)
    return activation.en_clair(session, org, date.today())


@routeur_inscription.get("/inscriptions/{organisation_id}/justificatifs/{justificatif_id}")
def lire_justificatif(organisation_id: uuid.UUID, justificatif_id: uuid.UUID,
                      session: Session = Depends(session_db, scope="function"), moi: Utilisateur = Depends(_plateforme)):
    contexte(session.connection(), organisation_id)
    j = session.get(Justificatif, justificatif_id)
    if j is None:
        raise Introuvable("Justificatif")
    journaliser(session, organisation_id, moi.id, "inscription.rccm_consulte", j.id)
    return Response(j.contenu, media_type=j.type_contenu,
                    headers={"Content-Disposition": f'inline; filename="rccm-{j.id}"'})


class MessageCourtier(_Corps):
    texte: str = Field(min_length=1, max_length=4000)


@routeur_inscription.get("/inscriptions/{organisation_id}/messages")
def fil_d_une_inscription(organisation_id: uuid.UUID, session: Session = Depends(session_db, scope="function"),
                          _: Utilisateur = Depends(_plateforme)):
    """Le courtier écrit à une entreprise inscrite avant d'être son conseiller."""
    contexte(session.connection(), organisation_id)
    return messages.lire(session, "courtier")


@routeur_inscription.post("/inscriptions/{organisation_id}/messages", status_code=201)
def ecrire_a_une_inscription(organisation_id: uuid.UUID, corps: MessageCourtier,
                             session: Session = Depends(session_db, scope="function"), moi: Utilisateur = Depends(_plateforme)):
    if session.get(Organisation, organisation_id) is None:
        raise Introuvable("Inscription")
    contexte(session.connection(), organisation_id)
    messages.envoyer(session, organisation_id, moi.id, "courtier", corps.texte)
    return messages.lire(session, "courtier")
