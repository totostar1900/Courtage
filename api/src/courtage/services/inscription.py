"""L'inscription en libre-service : un téléphone et un courriel vérifiés, une personne, une entreprise.

1. Un code à 6 chiffres par canal (SMS/WhatsApp pour le téléphone, courriel pour l'adresse) : 10 minutes, 5 essais,
   3 demandes par quart d'heure, gardé en HMAC — les règles de la connexion.
2. Un code juste rend une PREUVE : un jeton signé (nature, cible, échéance), sans état, valable 30 minutes. L'écran
   la garde et la présente à la création.
3. La création : l'utilisateur (téléphone et courriel vérifiés), le dossier `en_attente`, l'adhésion
   `admin_client`. Le RCCM est obligatoire et unique : une entreprise, un dossier vivant.

Le courtier vérifie ensuite l'entreprise (`services/activation`, la file des inscriptions).
"""
import hashlib
import hmac
import logging
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from courtage.auth import masquer
from courtage.db import Adhesion, CodeVerification, Organisation, Utilisateur, contexte
from courtage.erreurs import ErreurMetier

from . import journaliser
from .activation import normaliser_rccm

journal = logging.getLogger("courtage.inscription")

DUREE_CODE = timedelta(minutes=10)
DUREE_PREUVE = timedelta(minutes=30)
ESSAIS = 5
LIMITE_DEMANDES = 3
FENETRE_DEMANDES = timedelta(minutes=15)
TAILLES = {"moins_de_50": "Moins de 50 salariés", "50_a_250": "50 à 250 salariés", "plus_de_250": "Plus de 250 salariés"}
COURRIEL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SMS = "Courtage : votre code d'inscription est {code}. Il expire dans 10 minutes. Ne le communiquez à personne."
SUJET = "Votre code d'inscription"
TEXTE_COURRIEL = ("Bonjour,\n\nVotre code pour vérifier cette adresse est {code}. Il expire dans 10 minutes.\n\n"
                  "Si vous n'avez pas demandé à vous inscrire, ignorez ce message.\n")


def normaliser_courriel(saisi: str) -> str:
    adresse = (saisi or "").strip().lower()
    if not COURRIEL.match(adresse) or len(adresse) > 200:
        raise ErreurMetier("courriel_invalide", "Adresse électronique invalide.", 422)
    return adresse


# --- Les codes -----------------------------------------------------------------

def demander_code(session: Session, nature: str, cible: str, *, sms, courriel, cle: bytes) -> None:
    recentes = session.scalar(select(func.count()).select_from(CodeVerification).where(
        CodeVerification.nature == nature, CodeVerification.cible == cible,
        CodeVerification.cree_le > func.now() - FENETRE_DEMANDES))
    if recentes >= LIMITE_DEMANDES:
        raise ErreurMetier("trop_de_demandes", "Trop de demandes : réessayez dans un quart d'heure.", 429)
    code = f"{secrets.randbelow(10**6):06d}"
    session.add(CodeVerification(nature=nature, cible=cible, code_hash=_hmac(cle, nature, cible, code),
                                 expire_le=func.now() + DUREE_CODE))
    session.flush()
    if nature == "telephone":
        sms.envoyer(cible, SMS.format(code=code))
    else:
        courriel.envoyer(cible, SUJET, TEXTE_COURRIEL.format(code=code))
    journal.warning("[inscription] code %s envoyé à %s", nature, masquer(cible) if nature == "telephone" else cible[:2] + "…")


def verifier_code(session: Session, nature: str, cible: str, code: str, cle: bytes) -> str | None:
    """La preuve si le code est bon ; None sinon, l'essai compté (l'appelant ne lève pas : une erreur annulerait la
    transaction, et avec elle le compte des essais)."""
    ligne = session.scalars(select(CodeVerification).where(
        CodeVerification.nature == nature, CodeVerification.cible == cible, CodeVerification.utilise_le.is_(None),
        CodeVerification.expire_le > func.now(), CodeVerification.tentatives < ESSAIS)
        .order_by(CodeVerification.cree_le.desc()).limit(1).with_for_update()).first()
    if ligne is None:
        return None
    if not hmac.compare_digest(ligne.code_hash, _hmac(cle, nature, cible, (code or "").strip())):
        ligne.tentatives += 1
        session.flush()
        return None
    ligne.utilise_le = func.now()
    session.flush()
    return preuve(cle, nature, cible)


def preuve(cle: bytes, nature: str, cible: str, maintenant: float | None = None) -> str:
    echeance = int((maintenant or time.time()) + DUREE_PREUVE.total_seconds())
    return f"{echeance}.{_hmac(cle, 'preuve', nature, cible, str(echeance))}"


def preuve_valide(cle: bytes, jeton: str, nature: str, cible: str) -> bool:
    try:
        echeance, signature = (jeton or "").split(".", 1)
        valable = int(echeance) >= time.time()
    except ValueError:
        return False
    return valable and hmac.compare_digest(signature, _hmac(cle, "preuve", nature, cible, echeance))


# --- La création -----------------------------------------------------------------

def inscrire(session: Session, *, telephone: str, preuve_telephone: str, courriel: str, preuve_courriel: str,
             nom: str, fonction: str | None, entreprise: dict, cle: bytes) -> tuple[Utilisateur, Organisation]:
    if not preuve_valide(cle, preuve_telephone, "telephone", telephone):
        raise ErreurMetier("telephone_non_verifie", "Vérifiez d'abord votre téléphone (le code a peut-être expiré).", 422)
    if not preuve_valide(cle, preuve_courriel, "courriel", courriel):
        raise ErreurMetier("courriel_non_verifie", "Vérifiez d'abord votre adresse électronique.", 422)
    if session.scalar(select(Utilisateur.id).where(Utilisateur.telephone == telephone)):
        raise ErreurMetier("telephone_deja_inscrit", "Ce numéro a déjà un compte : connectez-vous.", 409)
    if session.scalar(select(Utilisateur.id).where(Utilisateur.email == courriel)):
        raise ErreurMetier("courriel_deja_inscrit", "Cette adresse a déjà un compte : connectez-vous.", 409)
    nom = (nom or "").strip()
    raison = (entreprise.get("nom") or "").strip()
    rccm = (entreprise.get("rccm") or "").strip()
    rccm_normalise = normaliser_rccm(rccm)
    if len(nom) < 2 or len(raison) < 2:
        raise ErreurMetier("champs_requis", "Votre nom et la raison sociale sont requis.", 422)
    if len(rccm_normalise) < 5:
        raise ErreurMetier("rccm_requis", "Le numéro RCCM de l'entreprise est requis.", 422)
    if entreprise.get("taille") not in TAILLES:
        raise ErreurMetier("taille_requise", "Choisir la taille de l'entreprise.", 422)
    if session.scalar(select(Organisation.id).where(Organisation.rccm_normalise == rccm_normalise,
                                                     Organisation.etat != "supprime")):
        raise ErreurMetier("entreprise_deja_inscrite",
                           "Cette entreprise est déjà inscrite. Demandez à son administrateur de vous ajouter à "
                           "l'équipe, ou écrivez à votre conseiller.", 409)
    maintenant = datetime.now(timezone.utc)
    utilisateur = Utilisateur(telephone=telephone, email=courriel, email_verifie_le=maintenant, nom_affiche=nom)
    org = Organisation(nom=raison, pays=entreprise["pays"], secteur=(entreprise.get("secteur") or "").strip() or None,
                       activation="en_attente", rccm=rccm, rccm_normalise=rccm_normalise, taille=entreprise["taille"],
                       adresse=(entreprise.get("adresse") or "").strip() or None,
                       ville=(entreprise.get("ville") or "").strip() or None, activation_demandee_le=maintenant)
    session.add_all([utilisateur, org])
    session.flush()
    session.add(Adhesion(utilisateur_id=utilisateur.id, organisation_id=org.id, role="admin_client",
                         fonction=(fonction or "").strip() or None))
    session.flush()
    contexte(session.connection(), org.id)
    journaliser(session, org.id, utilisateur.id, "inscription.demandee", org.id,
                {"rccm": rccm, "taille": org.taille, "pays": org.pays})
    return utilisateur, org


def _hmac(cle: bytes, *parties: str) -> str:
    return hmac.new(cle, "|".join(parties).encode(), hashlib.sha256).hexdigest()
