"""Les demandes de rappel de la vitrine : un visiteur laisse son numéro, le courtier le rappelle.

Gardées hors RLS (aucune organisation n'existe encore), effacées douze mois après leur réception. Le courtier est
prévenu par courriel sans le contenu de la demande. Un champ piège, invisible pour une personne, écarte les robots :
la réponse est la même, rien n'est gardé.

Spécification : docs/specs/2026-09-29-site-public-design.md §2.
"""
import uuid
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from sqlalchemy import case, delete, select
from sqlalchemy.orm import Session

from courtage.auth.telephone import normaliser
from courtage.db import DemandeRappel, Utilisateur
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.langue import t

from . import avis, journaliser
from .inscription import normaliser_courriel

CRENEAUX = ("matin", "apres_midi", "indifferent")
STATUTS = ("a_rappeler", "rappelee", "sans_suite")
CONSERVATION = relativedelta(months=12)


def deposer(session: Session, *, nom: str, entreprise: str, telephone: str, courriel: str | None, creneau: str,
            message: str | None, accord: bool, piege: str | None = None) -> DemandeRappel | None:
    if (piege or "").strip():
        return None                     # un robot a rempli le champ caché : même réponse, rien de gardé
    nom, entreprise = (nom or "").strip(), (entreprise or "").strip()
    if len(nom) < 2 or len(entreprise) < 2:
        raise ErreurMetier("champs_requis", t("Votre nom et celui de l'entreprise.", "Your name and the company's."), 422)
    if not accord:
        raise ErreurMetier("accord_requis", t("Cocher l'accord pour être rappelé.", "Tick your consent to be called back."), 422)
    if creneau not in CRENEAUX:
        raise ErreurMetier("creneau_inconnu", t("Choisir un créneau.", "Choose a time slot."), 422)
    try:
        numero = normaliser(telephone)
    except ValueError:
        raise ErreurMetier("telephone_invalide", t("Numéro de téléphone invalide.", "Invalid phone number."), 422) from None
    d = DemandeRappel(nom=nom, entreprise=entreprise, telephone=numero,
                      courriel=normaliser_courriel(courriel) if (courriel or "").strip() else None, creneau=creneau,
                      message=(message or "").strip()[:1000] or None, accord=True)
    session.add(d)
    session.flush()
    journaliser(session, None, None, "rappel.demande", d.id, {})
    avis.prevoir(session, "demande_rappel", avis.plateforme(session), auteur=None)
    return d


def lister(session: Session) -> list[dict]:
    """À rappeler d'abord, les plus anciennes en tête ; puis les traitées, les plus récentes en tête."""
    ordre = case((DemandeRappel.statut == "a_rappeler", 0), else_=1)
    lignes = session.scalars(select(DemandeRappel).order_by(ordre, DemandeRappel.recue_le))
    return [en_clair(session, d) for d in lignes]


def traiter(session: Session, auteur: uuid.UUID, demande_id: uuid.UUID, statut: str, note: str | None) -> DemandeRappel:
    if statut not in STATUTS:
        raise ErreurMetier("statut_inconnu", t("Rappelée, sans suite, ou à rappeler.", "Called back, no follow-up, or to call."), 422)
    d = session.get(DemandeRappel, demande_id)
    if d is None:
        raise Introuvable("Demande de rappel")
    d.statut, d.note = statut, (note or "").strip() or None
    d.traitee_par, d.traitee_le = (auteur, datetime.now(timezone.utc)) if statut != "a_rappeler" else (None, None)
    session.flush()
    journaliser(session, None, auteur, "rappel.traite", d.id, {"statut": statut})
    return d


def en_clair(session: Session, d: DemandeRappel) -> dict:
    qui = session.get(Utilisateur, d.traitee_par) if d.traitee_par else None
    return {"id": str(d.id), "nom": d.nom, "entreprise": d.entreprise, "telephone": d.telephone, "courriel": d.courriel,
            "creneau": d.creneau, "message": d.message, "recue_le": d.recue_le.isoformat(), "statut": d.statut,
            "note": d.note, "traitee_le": d.traitee_le.isoformat() if d.traitee_le else None,
            "traitee_par": (qui.nom_affiche if qui else None)}


def effacer_anciennes(moteur, maintenant: datetime) -> int:
    """Pour la tâche quotidienne : les demandes reçues il y a plus de douze mois."""
    with Session(moteur) as session, session.begin():
        return session.execute(delete(DemandeRappel).where(DemandeRappel.recue_le < maintenant - CONSERVATION)).rowcount


