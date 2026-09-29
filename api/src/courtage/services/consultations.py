"""La consultation des assureurs : le cahier part depuis la plateforme, l'offre revient par un lien personnel.

- **Tracer qui a été consulté, quand.** Une consultation par assureur et par cahier : envoyée, ouverte, répondue,
  relancée, annulée. C'est la preuve d'une mise en concurrence loyale.
- **Le lien** est un jeton aléatoire envoyé par courriel à l'adresse donnée par le conseiller, gardé seulement sous
  forme d'empreinte (`liens_assureurs`, hors RLS : lu avant qu'une organisation soit connue). Relancer émet un lien
  neuf et révoque l'ancien ; annuler révoque. Il vaut jusqu'à la date limite de réponse du cahier.
- **L'offre déposée** entre dans les réponses du cahier comme les autres : confrontée aux conditions, classée,
  marquée « déposée par l'assureur » ; le conseiller la relit, la corrige ou la retire avec motif.

Spécification : docs/specs/2026-09-29-lien-assureur-design.md.
"""
import hashlib
import secrets
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from courtage import cabinet
from courtage.db import (ConsultationAssureur, Document, FicheRegime, LienAssureur, Organisation, ReponseFiche,
                         Utilisateur, contexte)
from courtage.erreurs import ErreurMetier
from courtage.langue import t

from . import avis, comptes_assureurs, journaliser, reponses
from .inscription import normaliser_courriel


def _empreinte(jeton: str) -> str:
    return hashlib.sha256(("lien-assureur:" + jeton).encode()).hexdigest()


def _numero(session: Session, fiche: FicheRegime) -> str:
    return session.scalars(select(Document.numero).where(Document.fiche_id == fiche.id)).one()


def _lier(session: Session, c: ConsultationAssureur) -> str:
    """Révoque les liens en cours de la consultation et en émet un neuf ; rend le jeton, qui n'est gardé nulle part."""
    session.execute(update(LienAssureur).where(LienAssureur.consultation_id == c.id, LienAssureur.revoque_le.is_(None))
                    .values(revoque_le=datetime.now(timezone.utc)))
    jeton = secrets.token_urlsafe(32)
    session.add(LienAssureur(jeton_hash=_empreinte(jeton), consultation_id=c.id, organisation_id=c.organisation_id))
    session.flush()
    return jeton


def _courriel(session: Session, org: Organisation, c: ConsultationAssureur, fiche: FicheRegime, jeton: str,
              relance: bool) -> None:
    nom_cabinet = cabinet.identite()["nom"]
    lien = f"{(session.info.get('url_publique') or '').rstrip('/')}/offre/{jeton}"
    bonjour = f"Bonjour{' ' + c.contact_nom if c.contact_nom else ''},"
    corps = (f"{bonjour}\n\n{'Rappel : ' if relance else ''}{nom_cabinet}, courtier en assurance, vous consulte pour le "
             f"compte de son client {org.nom} sur la couverture de ses indemnités de fin de carrière.\n\n"
             f"Cahier des charges N° {_numero(session, fiche)} — réponse attendue au plus tard le "
             f"{fiche.date_limite_reponse:%d/%m/%Y}.\n\n"
             f"Lire le cahier et déposer votre offre : {lien}\n\n"
             "Ce lien vous est personnel : il ne demande pas de compte et ne sert qu'à cette consultation. Ne le "
             "transférez pas.\n")
    avis.prevoir_adresse(session, c.contact_courriel, f"Consultation — cahier des charges {org.nom}", corps,
                         "consultation_assureur")


def envoyer(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime, *, assureur: str,
            contact_nom: str | None, contact_courriel: str, aujourd_hui: date) -> ConsultationAssureur:
    reponses._ouverte(session, fiche)
    if fiche.date_limite_reponse < aujourd_hui:
        raise ErreurMetier("consultation_close", t("La date limite de réponse du cahier est passée.",
                                                   "The response deadline of these specifications has passed."), 409)
    assureur = (assureur or "").strip()
    if len(comptes_assureurs.cle(assureur)) < 2:
        raise ErreurMetier("assureur_requis", t("Nommer l'assureur consulté.", "Name the insurer consulted."), 422)
    c = ConsultationAssureur(organisation_id=org.id, fiche_id=fiche.id, assureur=assureur,
                             assureur_cle=comptes_assureurs.cle(assureur),
                             contact_nom=(contact_nom or "").strip() or None,
                             contact_courriel=normaliser_courriel(contact_courriel), expire_le=fiche.date_limite_reponse,
                             envoyee_par=auteur)
    session.add(c)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raise ErreurMetier("consultation_existante", t(f"{assureur} est déjà consulté sur ce cahier : le relancer.",
                                                       f"{assureur} is already consulted on these specifications: send "
                                                       "a reminder."), 409) from None
    jeton = _lier(session, c)
    _courriel(session, org, c, fiche, jeton, relance=False)
    journaliser(session, org.id, auteur, "consultation.envoyee", c.id, {"fiche": str(fiche.id), "assureur": assureur})
    return c


def obtenir(session: Session, consultation_id: uuid.UUID) -> ConsultationAssureur:
    c = session.get(ConsultationAssureur, consultation_id)
    if c is None:
        raise ErreurMetier("introuvable", t("Consultation introuvable.", "Consultation not found."), 404)
    return c


def relancer(session: Session, org: Organisation, auteur: uuid.UUID, c: ConsultationAssureur,
             aujourd_hui: date) -> ConsultationAssureur:
    fiche = session.get(FicheRegime, c.fiche_id)
    if etat(session, c, aujourd_hui) in ("annulee", "repondue", "close"):
        raise ErreurMetier("consultation_close", t("Cette consultation n'attend plus de réponse.",
                                                   "This consultation is no longer awaiting a response."), 409)
    c.relances += 1
    c.relancee_le = datetime.now(timezone.utc)
    jeton = _lier(session, c)
    _courriel(session, org, c, fiche, jeton, relance=True)
    journaliser(session, org.id, auteur, "consultation.relancee", c.id, {"relances": c.relances})
    return c


def annuler(session: Session, org: Organisation, auteur: uuid.UUID, c: ConsultationAssureur) -> ConsultationAssureur:
    if c.annulee_le is not None or c.repondue_le is not None:
        raise ErreurMetier("consultation_close", t("Cette consultation n'attend plus de réponse.",
                                                   "This consultation is no longer awaiting a response."), 409)
    c.annulee_le = datetime.now(timezone.utc)
    session.execute(update(LienAssureur).where(LienAssureur.consultation_id == c.id, LienAssureur.revoque_le.is_(None))
                    .values(revoque_le=c.annulee_le))
    session.flush()
    journaliser(session, org.id, auteur, "consultation.annulee", c.id, {})
    return c


def etat(session: Session, c: ConsultationAssureur, aujourd_hui: date) -> str:
    if c.annulee_le:
        return "annulee"
    if c.repondue_le:
        return "repondue"
    if c.expire_le < aujourd_hui or reponses.choix(session, session.get(FicheRegime, c.fiche_id)) is not None:
        return "close"
    return "ouverte" if c.ouverte_le else "envoyee"


def en_clair(session: Session, c: ConsultationAssureur, aujourd_hui: date) -> dict:
    qui = session.get(Utilisateur, c.envoyee_par)
    iso = lambda d: d.isoformat() if d else None  # noqa: E731
    return {"id": str(c.id), "assureur": c.assureur, "contact_nom": c.contact_nom, "contact_courriel": c.contact_courriel,
            "envoyee_le": c.envoyee_le.isoformat(), "envoyee_par": (qui.nom_affiche if qui else None) or "—",
            "ouverte_le": iso(c.ouverte_le), "repondue_le": iso(c.repondue_le), "relances": c.relances,
            "relancee_le": iso(c.relancee_le), "annulee_le": iso(c.annulee_le), "expire_le": c.expire_le.isoformat(),
            "etat": etat(session, c, aujourd_hui)}


def lister(session: Session, fiche: FicheRegime, aujourd_hui: date) -> list[dict]:
    return [en_clair(session, c, aujourd_hui) for c in session.scalars(
        select(ConsultationAssureur).where(ConsultationAssureur.fiche_id == fiche.id)
        .order_by(ConsultationAssureur.envoyee_le))]


# --- Le côté de l'assureur, par son lien (sans compte) ------------------------------------------------

def resoudre(session: Session, jeton: str) -> tuple[ConsultationAssureur, Organisation, FicheRegime]:
    """Le lien → la consultation, dans le contexte de son organisation. Un lien inconnu ou révoqué répond comme un
    lien qui n'existe pas."""
    lien = session.scalars(select(LienAssureur).where(LienAssureur.jeton_hash == _empreinte(jeton or ""),
                                                      LienAssureur.revoque_le.is_(None))).first()
    if lien is None:
        raise ErreurMetier("lien_inconnu", t("Ce lien n'est pas (ou plus) valable : demandez-en un nouveau au courtier "
                                             "qui vous a consulté.",
                                             "This link is not (or no longer) valid: ask the broker who consulted you "
                                             "for a new one."), 404)
    contexte(session.connection(), lien.organisation_id)
    c = session.get(ConsultationAssureur, lien.consultation_id)
    return c, session.get(Organisation, c.organisation_id), session.get(FicheRegime, c.fiche_id)


def pour_l_assureur(session: Session, jeton: str, aujourd_hui: date) -> dict:
    c, org, fiche = resoudre(session, jeton)
    if c.ouverte_le is None:
        c.ouverte_le = datetime.now(timezone.utc)
        session.flush()
        journaliser(session, org.id, None, "consultation.ouverte", c.id, {})
    conditions = []
    for _, libelle, cle, sens in reponses.CRITERES:
        v = fiche.conditions.get(cle)
        if v is None or (sens == "oui" and v is False):
            continue
        conditions.append({"cle": cle, "libelle": libelle, "valeur": v, "sens": sens})
    return {"cabinet": cabinet.identite()["nom"], "client": org.nom, "pays": org.pays, "assureur": c.assureur,
            "cahier": _numero(session, fiche), "date_limite": fiche.date_limite_reponse.isoformat(),
            "conditions": conditions, "etat": etat(session, c, aujourd_hui),
            "repondue_le": c.repondue_le.isoformat() if c.repondue_le else None}


def cahier(session: Session, jeton: str) -> tuple[str, bytes, str]:
    c, org, fiche = resoudre(session, jeton)
    document = session.scalars(select(Document).where(Document.fiche_id == fiche.id)).one()
    return f"cahier-des-charges-{document.numero}.pdf", document.contenu, document.type_contenu


def deposer(session: Session, jeton: str, donnees: dict, offre: tuple[str, bytes] | None,
            aujourd_hui: date) -> ReponseFiche:
    c, org, fiche = resoudre(session, jeton)
    e = etat(session, c, aujourd_hui)
    if e != "ouverte" and e != "envoyee":
        raise ErreurMetier("consultation_close" if e != "repondue" else "deja_repondu",
                           t("Votre réponse est déjà reçue." if e == "repondue" else "Cette consultation est close.",
                             "Your response has already been received." if e == "repondue"
                             else "This consultation is closed."), 409)
    if offre is None:
        raise ErreurMetier("offre_requise", t("Joindre votre offre en PDF : c'est la pièce qui vous engage.",
                                              "Attach your offer as a PDF: it is the document that commits you."), 422)
    r = reponses.enregistrer(session, org, None, fiche, {**donnees, "assureur": c.assureur, "recue_le": aujourd_hui},
                             offre=offre, consultation_id=c.id)
    c.repondue_le = datetime.now(timezone.utc)
    session.flush()
    journaliser(session, org.id, None, "consultation.repondue", c.id, {"reponse": str(r.id)})
    avis.prevoir(session, "offre_recue", avis.conseillers(session, org.id), auteur=None, org=org.id,
                 entreprise=org.nom, assureur=c.assureur, fiche=fiche.id)
    return r
