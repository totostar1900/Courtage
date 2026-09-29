"""L'espace personnel : qui je suis, où je suis inscrit, où je suis connecté. Ce qui concerne la personne, pas un
dossier : il se lit sans organisation choisie (tables d'identité, hors RLS)."""
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from courtage import auth
from courtage.db import Adhesion, Organisation, SessionUtilisateur, Utilisateur
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.langue import t
from courtage.services import journaliser

from . import COOKIE, identite, session_db

routeur_profil = APIRouter()


def _jeton_courant(request: Request) -> str | None:
    en_tete = request.headers.get("authorization", "")
    return en_tete[7:].strip() if en_tete.lower().startswith("bearer ") else request.cookies.get(COOKIE)


@routeur_profil.get("/moi/profil")
def lire_profil(request: Request, session: Session = Depends(session_db, scope="function"),
                moi: Utilisateur = Depends(identite)):
    courant = _jeton_courant(request)
    empreinte = auth._empreinte(courant) if courant else None
    dossiers = session.execute(
        select(Organisation, Adhesion.role, Adhesion.fonction).join(Adhesion, Adhesion.organisation_id == Organisation.id)
        .where(Adhesion.utilisateur_id == moi.id, Organisation.etat.not_in(("archive", "supprime")))
        .order_by(Organisation.nom)).all()
    sessions = session.scalars(select(SessionUtilisateur).where(
        SessionUtilisateur.utilisateur_id == moi.id, SessionUtilisateur.revoquee_le.is_(None),
        SessionUtilisateur.expire_le > func.now()).order_by(SessionUtilisateur.derniere_activite.desc()))
    return {
        "id": str(moi.id), "nom_affiche": moi.nom_affiche, "telephone": moi.telephone, "email": moi.email,
        "email_verifie_le": moi.email_verifie_le.isoformat() if moi.email_verifie_le else None,
        "admin_plateforme": moi.admin_plateforme, "cree_le": moi.cree_le.isoformat(),
        "avis_courriel": moi.avis_courriel,
        "conditions": None if not moi.conditions_version else {
            "version": moi.conditions_version, "le": moi.conditions_acceptees_le.isoformat()},
        "dossiers": [{"id": str(o.id), "nom": o.nom, "pays": o.pays, "role": r, "fonction": f, "activation": o.activation}
                     for o, r, f in dossiers],
        "sessions": [{"id": str(s.id), "cree_le": s.cree_le.isoformat(), "derniere_activite": s.derniere_activite.isoformat(),
                      "agent": s.agent, "courante": empreinte is not None and s.jeton_hash == empreinte}
                     for s in sessions],
    }


class ModificationProfil(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nom_affiche: str | None = Field(default=None, min_length=2, max_length=120)
    avis_courriel: bool | None = None


@routeur_profil.patch("/moi/profil")
def modifier_profil(corps: ModificationProfil, request: Request, session: Session = Depends(session_db, scope="function"),
                    moi: Utilisateur = Depends(identite)):
    """Le nom sous lequel on apparaît, et les avis par courriel. Le téléphone et le courriel, vérifiés à
    l'inscription, se changent avec le conseiller (ils identifient la personne)."""
    if corps.nom_affiche is not None:
        avant = moi.nom_affiche
        moi.nom_affiche = corps.nom_affiche.strip()
        journaliser(session, None, moi.id, "profil.modifie", moi.id, {"avant": avant, "apres": moi.nom_affiche})
    if corps.avis_courriel is not None and corps.avis_courriel != moi.avis_courriel:
        moi.avis_courriel = corps.avis_courriel
        journaliser(session, None, moi.id, "profil.avis", moi.id, {"avis_courriel": moi.avis_courriel})
    session.flush()
    return lire_profil(request, session, moi)


@routeur_profil.delete("/moi/sessions/{session_id}")
def fermer_session(session_id: uuid.UUID, request: Request, session: Session = Depends(session_db, scope="function"),
                   moi: Utilisateur = Depends(identite)):
    """Déconnecter un appareil (un téléphone perdu, un poste partagé)."""
    s = session.get(SessionUtilisateur, session_id)
    if s is None or s.utilisateur_id != moi.id:
        raise Introuvable(t("Session", "Session"))
    s.revoquee_le = func.now()
    session.flush()
    journaliser(session, None, moi.id, "session.fermee", s.id)
    return lire_profil(request, session, moi)


@routeur_profil.post("/moi/sessions/fermeture-des-autres")
def fermer_les_autres(request: Request, session: Session = Depends(session_db, scope="function"),
                      moi: Utilisateur = Depends(identite)):
    courant = _jeton_courant(request)
    if courant is None:
        raise ErreurMetier("session_inconnue", t("Session introuvable.", "Session not found."), 400)
    n = session.execute(update(SessionUtilisateur).where(
        SessionUtilisateur.utilisateur_id == moi.id, SessionUtilisateur.revoquee_le.is_(None),
        SessionUtilisateur.jeton_hash != auth._empreinte(courant)).values(revoquee_le=func.now())).rowcount
    journaliser(session, None, moi.id, "sessions.fermees", moi.id, {"nombre": n})
    return lire_profil(request, session, moi)
