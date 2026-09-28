"""Le fil d'un dossier : l'entreprise et son conseiller (le courtier, tant qu'aucun conseiller n'est désigné).

Un message ne se modifie pas ; il est « lu » quand l'autre côté ouvre le fil. Le fil part avec une inscription
effacée, et reste avec un dossier confirmé.
"""
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from courtage.db import MessageDossier, Utilisateur
from courtage.erreurs import ErreurMetier

from . import journaliser


def cote_de(role: str | None, admin_plateforme: bool) -> str:
    return "courtier" if role == "conseiller" or (role is None and admin_plateforme) else "entreprise"


def envoyer(session: Session, organisation_id: uuid.UUID, auteur: uuid.UUID, cote: str, texte: str) -> MessageDossier:
    texte = (texte or "").strip()
    if not texte:
        raise ErreurMetier("message_vide", "Écrire un message.", 422)
    if len(texte) > 4000:
        raise ErreurMetier("message_trop_long", "4 000 caractères au plus.", 422)
    m = MessageDossier(organisation_id=organisation_id, auteur=auteur, cote=cote, texte=texte)
    session.add(m)
    session.flush()
    journaliser(session, organisation_id, auteur, "message.envoye", m.id, {"cote": cote})
    return m


def lire(session: Session, cote: str) -> dict:
    """Le fil, du plus ancien au plus récent ; ce que l'autre côté a écrit devient lu."""
    autre = "entreprise" if cote == "courtier" else "courtier"
    session.execute(update(MessageDossier).where(MessageDossier.cote == autre, MessageDossier.lu_le.is_(None))
                    .values(lu_le=func.now()))
    rangs = session.execute(select(MessageDossier, Utilisateur.nom_affiche)
                            .join(Utilisateur, Utilisateur.id == MessageDossier.auteur).order_by(MessageDossier.le))
    return {"messages": [{"id": str(m.id), "cote": m.cote, "auteur": nom or "—", "texte": m.texte,
                          "le": m.le.isoformat(), "lu_le": m.lu_le.isoformat() if m.lu_le else None}
                         for m, nom in rangs], "cote": cote}


def non_lus(session: Session, cote: str) -> int:
    autre = "entreprise" if cote == "courtier" else "courtier"
    return session.scalar(select(func.count()).select_from(MessageDossier)
                          .where(MessageDossier.cote == autre, MessageDossier.lu_le.is_(None))) or 0
