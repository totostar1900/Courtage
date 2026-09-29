"""Connexion par téléphone : un code à usage unique, puis une session.

- Un code : 6 chiffres, 10 minutes, 5 essais, une seule utilisation. Stocké
  sous forme de HMAC (clé de la plateforme, numéro, code), jamais en clair.
- Une demande écrit une ligne de code même pour un numéro inconnu (rien n'est
  envoyé) : la réponse et la limite (3 demandes par quart d'heure) sont les
  mêmes, et l'on ne peut pas deviner qui est client.
- Une session : un jeton aléatoire, dont seule l'empreinte est gardée ; 30
  jours ; révocable. Le navigateur le reçoit dans un cookie HttpOnly.
- Chaque demande et chaque essai laissent une ligne dans le journal
  (`courtage.connexion`), le numéro masqué : l'exploitant, qui ne voit pas
  l'écran, y lit pourquoi un code n'est pas venu ou n'a pas été accepté.
"""
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from courtage.db import CodeConnexion, SessionUtilisateur, Utilisateur
from courtage.erreurs import ErreurMetier
from courtage.langue import t

journal = logging.getLogger("courtage.connexion")

DUREE_CODE = timedelta(minutes=10)
ESSAIS = 5
LIMITE_DEMANDES = 3
FENETRE_DEMANDES = timedelta(minutes=15)
DUREE_SESSION = timedelta(days=30)
CLE_DE_DEVELOPPEMENT = b"courtage-cle-auth-de-developpement"

MESSAGE = ("Courtage : votre code de connexion est {code}. Il expire dans 10 minutes. "
           "Ne le communiquez à personne, pas même à votre conseiller.")


def masquer(telephone: str) -> str:
    """Les trois derniers chiffres : assez pour reconnaître son numéro, pas pour le lire."""
    return "•" * max(len(telephone) - 3, 0) + telephone[-3:]


def demander_code(session: Session, telephone: str, expediteur, cle: bytes) -> None:
    recentes = session.scalar(select(func.count()).select_from(CodeConnexion).where(
        CodeConnexion.telephone == telephone, CodeConnexion.cree_le > func.now() - FENETRE_DEMANDES))
    if recentes >= LIMITE_DEMANDES:
        journal.warning("[connexion] %s : limite atteinte (%d demandes en 15 min), aucun code — attendre un quart "
                        "d'heure", masquer(telephone), LIMITE_DEMANDES)
        raise ErreurMetier("trop_de_demandes", t("Trop de demandes pour ce numéro : réessayez dans un quart d'heure.",
                                                   "Too many requests for this number: try again in fifteen minutes."), 429)
    code = f"{secrets.randbelow(10**6):06d}"
    session.add(CodeConnexion(telephone=telephone, code_hash=_hmac(cle, telephone, code), canal=expediteur.canal,
                              expire_le=func.now() + DUREE_CODE))
    session.flush()
    if session.scalar(select(Utilisateur.id).where(Utilisateur.telephone == telephone)) is None:
        journal.warning("[connexion] %s : numéro inconnu, rien envoyé (aucune personne inscrite à ce numéro)",
                        masquer(telephone))
        return
    expediteur.envoyer(telephone, MESSAGE.format(code=code))
    journal.warning("[connexion] %s : code envoyé par %s (seul le dernier code demandé est valable, 10 min)",
                    masquer(telephone), expediteur.canal)


def verifier_code(session: Session, telephone: str, code: str, cle: bytes) -> Utilisateur | None:
    """L'utilisateur si le code est bon ; None sinon, l'essai étant compté (l'appelant ne lève pas :
    une erreur annulerait la transaction, et avec elle le compte des essais)."""
    ligne = session.scalars(
        select(CodeConnexion).where(
            CodeConnexion.telephone == telephone, CodeConnexion.utilise_le.is_(None),
            CodeConnexion.expire_le > func.now(), CodeConnexion.tentatives < ESSAIS)
        .order_by(CodeConnexion.cree_le.desc()).limit(1).with_for_update()).first()
    if ligne is None:
        journal.warning("[connexion] %s : code refusé — aucun code en cours (expiré, déjà utilisé ou 5 essais "
                        "manqués) : en demander un nouveau", masquer(telephone))
        return None
    utilisateur = session.scalars(select(Utilisateur).where(Utilisateur.telephone == telephone)).first()
    if utilisateur is None or not hmac.compare_digest(ligne.code_hash.strip(), _hmac(cle, telephone, code.strip())):
        ligne.tentatives += 1
        session.flush()
        journal.warning("[connexion] %s : code refusé — ce n'est pas le dernier code demandé (essai %d sur %d)",
                        masquer(telephone), ligne.tentatives, ESSAIS)
        return None
    ligne.utilise_le = func.now()
    session.flush()
    journal.warning("[connexion] %s : connecté", masquer(telephone))
    return utilisateur


def ouvrir_session(session: Session, utilisateur: Utilisateur, agent: str | None) -> str:
    jeton = secrets.token_urlsafe(32)
    session.add(SessionUtilisateur(utilisateur_id=utilisateur.id, jeton_hash=_empreinte(jeton),
                                   expire_le=func.now() + DUREE_SESSION, agent=(agent or "")[:300]))
    session.flush()
    return jeton


def utilisateur_du_jeton(session: Session, jeton: str) -> Utilisateur | None:
    s = session.scalars(select(SessionUtilisateur).where(
        SessionUtilisateur.jeton_hash == _empreinte(jeton), SessionUtilisateur.revoquee_le.is_(None),
        SessionUtilisateur.expire_le > func.now())).first()
    if s is None:
        return None
    s.derniere_activite = func.now()
    return session.get(Utilisateur, s.utilisateur_id)


def revoquer(session: Session, jeton: str) -> None:
    s = session.scalars(select(SessionUtilisateur).where(SessionUtilisateur.jeton_hash == _empreinte(jeton))).first()
    if s is not None and s.revoquee_le is None:
        s.revoquee_le = func.now()
        session.flush()


def _hmac(cle: bytes, telephone: str, code: str) -> str:
    return hmac.new(cle, f"{telephone}|{code}".encode(), hashlib.sha256).hexdigest()


def _empreinte(jeton: str) -> str:
    return hashlib.sha256(jeton.encode()).hexdigest()

