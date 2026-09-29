"""Les avis par courriel : un événement qui attend quelqu'un l'en prévient, avec le lien de la page.

- **Après la validation.** `prevoir` range l'avis dans la session ; il part quand la transaction est validée
  (`after_commit`), et disparaît avec elle si elle est annulée : un acte refusé ne prévient personne.
- **Jamais bloquant.** Un envoi qui échoue s'écrit au journal du serveur ; l'acte, lui, est fait.
- **Rien du dossier dans le courriel** : ni donnée du personnel, ni montant, ni nom de bénéficiaire, ni le texte
  d'un message — « un message vous attend », et le lien. Le motif d'un refus d'inscription fait exception : il est
  écrit par le courtier pour le client, qui n'a pas encore accès à autre chose.
- **Qui ne reçoit pas** : l'auteur de l'acte, un compte sans adresse, un compte qui a coupé les avis dans son profil.
- En français, comme les SMS, les documents et le mandat.
- Ce sont des avis d'événement ; l'envoi hebdomadaire des alertes reste suspendu (décision antérieure).
- **Sur WhatsApp aussi**, pour qui l'a demandé dans son profil (désactivé par défaut), au numéro vérifié du compte :
  un modèle approuvé, avec le sujet et le lien seulement. Sans modèle ni émetteur WhatsApp (`session.info["whatsapp"]`),
  rien n'y part. Conception : docs/specs/2026-09-29-contenu-mesure-portefeuille-whatsapp-design.md §4.

La session reçoit l'expéditeur et l'adresse publique de `session_db` (`session.info`). Sans expéditeur (une tâche
programmée, un script), `prevoir` ne fait rien.

Conception : docs/specs/2026-09-29-plateforme-ouverte-p1-design.md §5.
"""
import logging
import threading
import uuid
from collections.abc import Iterable

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from courtage.db import Adhesion, Utilisateur

journal = logging.getLogger("courtage.avis")

# événement → (sujet, texte, chemin). Les champs entre accolades viennent de `prevoir(..., **valeurs)`.
EVENEMENTS: dict[str, tuple[str, str, str]] = {
    "inscription_nouvelle": (
        "Nouvelle inscription à vérifier",
        "{entreprise} vient de s'inscrire. Vérifiez l'entreprise et confirmez l'inscription sous deux jours ouvrés.",
        "/"),
    "inscription_confirmee": (
        "Votre inscription est confirmée",
        "L'inscription de {entreprise} est confirmée. Les documents scellés, les exports, l'équipe et le mandat de "
        "courtage vous sont ouverts.",
        "/dossier/{org}"),
    "inscription_refusee": (
        "Votre inscription n'a pas été confirmée",
        "L'inscription de {entreprise} n'a pas été confirmée. Motif : {motif}",
        "/dossier/{org}"),
    "message": (
        "Un message vous attend",
        "{qui} a écrit dans le fil du dossier {entreprise}.",
        "/dossier/{org}/messages"),
    "mandat_demande": (
        "Demande d'accompagnement",
        "{entreprise} demande un accompagnement en courtage.",
        "/dossier/{org}/accompagnement"),
    "mandat_propose": (
        "Un mandat de courtage est à signer",
        "Votre conseiller vous propose un mandat de courtage pour {entreprise}. Lisez-le, puis signez-le ou "
        "déclinez-le.",
        "/dossier/{org}/accompagnement"),
    "mandat_signe": (
        "Le mandat de courtage est signé",
        "{entreprise} a signé le mandat de courtage (N° {numero}).",
        "/dossier/{org}/accompagnement"),
    "mandat_refuse": (
        "Le mandat proposé a été décliné",
        "{entreprise} a décliné le mandat de courtage proposé.",
        "/dossier/{org}/accompagnement"),
    "offre_choisie": (
        "L'entreprise a choisi une offre",
        "{entreprise} a choisi une offre sur le cahier des charges.",
        "/dossier/{org}/cahier/{fiche}"),
    "dossier_a_verifier": (
        "Un dossier de prise en charge est à vérifier",
        "{entreprise} a déposé un dossier de prise en charge à vérifier.",
        "/dossier/{org}/dossiers/{dossier}"),
    "dossier_repondu": (
        "Votre conseiller a répondu sur un dossier de prise en charge",
        "Il y a du nouveau sur un dossier de prise en charge de {entreprise}.",
        "/dossier/{org}/dossiers/{dossier}"),
    "demande_rappel": (
        "Une demande de rappel vous attend",
        "Un visiteur de la vitrine demande à être rappelé. Son numéro et son créneau sont sur la plateforme.",
        "/"),
    "rappel_annuel": (
        "Rappel : {etape}",
        "Pour {entreprise} : « {etape} » {quand} le {echeance}. L'engagement se remesure chaque année à la même date.",
        "/dossier/{org}/{lien}"),
    "offre_recue": (
        "Une offre d'assureur est arrivée",
        "{assureur} a déposé son offre sur le cahier des charges de {entreprise} : à relire avant le classement.",
        "/dossier/{org}/cahier/{fiche}"),
    "police_recue": (
        "Votre police est arrivée",
        "La police {assureur} de {entreprise} est déposée : lisez-la, signez-la avec l'assureur, puis déclarez la "
        "date de signature.",
        "/dossier/{org}/placement"),
    # Jamais de coordonnées bancaires ni de montant dans le courriel : la page seulement, où elles sont confrontées
    # au registre des comptes (fraude au changement de RIB).
    "appel_prime": (
        "Un appel de prime vous attend",
        "Un appel de prime est enregistré pour {entreprise}. Les coordonnées bancaires et le montant sont sur la "
        "plateforme ; vérifiez-y qu'elles sont confirmées avant tout virement.",
        "/dossier/{org}/placement"),
    "virement_declare": (
        "Un virement est déclaré",
        "{entreprise} a déclaré un virement de prime : à rapprocher de la quittance de l'assureur.",
        "/dossier/{org}/placement"),
    "encaissement_confirme": (
        "Votre prime est encaissée",
        "L'assureur a confirmé l'encaissement d'une prime de {entreprise}.",
        "/dossier/{org}/placement"),
}

PIED = ("\n\nVous recevez cet avis parce que vous suivez ce dossier sur la plateforme de courtage. Pour ne plus "
        "recevoir ces avis : Mon profil, Préférences.\n")


# --- Qui prévenir ----------------------------------------------------------------------
# `adhesions` et `utilisateurs` sont lus hors RLS : la plateforme sait qui suit quel dossier.

def conseillers(session: Session, organisation_id: uuid.UUID) -> list[uuid.UUID]:
    """Les conseillers du dossier ; à défaut, les administrateurs de la plateforme (le courtier)."""
    ids = list(session.scalars(select(Adhesion.utilisateur_id).where(
        Adhesion.organisation_id == organisation_id, Adhesion.role == "conseiller")))
    return ids or plateforme(session)


def entreprise(session: Session, organisation_id: uuid.UUID,
               roles: tuple[str, ...] = ("admin_client",)) -> list[uuid.UUID]:
    return list(session.scalars(select(Adhesion.utilisateur_id).where(
        Adhesion.organisation_id == organisation_id, Adhesion.role.in_(roles))))


def plateforme(session: Session) -> list[uuid.UUID]:
    return list(session.scalars(select(Utilisateur.id).where(Utilisateur.admin_plateforme.is_(True))))


# --- Prévoir, puis envoyer à la validation ----------------------------------------------

def prevoir(session: Session, evenement: str, destinataires: Iterable[uuid.UUID], *, auteur: uuid.UUID | None,
            org: uuid.UUID | None = None, **valeurs) -> int:
    """Range un avis par destinataire ; rend le nombre de courriels. Il part après la validation de la transaction.
    Qui l'a demandé dans son profil le reçoit aussi sur WhatsApp, au numéro de son compte : le sujet et le lien."""
    courriel, whatsapp = session.info.get("courriel"), session.info.get("whatsapp")
    if courriel is None and whatsapp is None:
        return 0
    sujet, texte, chemin = EVENEMENTS[evenement]
    valeurs = {"org": org, **valeurs}
    ids = {d for d in destinataires if d and d != auteur}
    if not ids:
        return 0
    comptes = list(session.scalars(select(Utilisateur).where(Utilisateur.id.in_(ids))))
    sujet = sujet.format(**valeurs)
    lien = f"{(session.info.get('url_publique') or '').rstrip('/')}{chemin.format(**valeurs)}"
    corps = f"Bonjour,\n\n{texte.format(**valeurs)}\n\nOuvrir : {lien}{PIED}"
    adresses = [u.email for u in comptes if u.email and u.avis_courriel] if courriel is not None else []
    numeros = [u.telephone for u in comptes if u.telephone and u.avis_whatsapp] if whatsapp is not None else []
    _ranger(session, [(a, sujet, corps, evenement) for a in adresses], [(n, sujet, lien, evenement) for n in numeros])
    return len(adresses)


def prevoir_adresse(session: Session, adresse: str, sujet: str, corps: str, evenement: str) -> bool:
    """Un courriel à une adresse hors compte (un assureur consulté), aux mêmes règles : après la validation, jamais
    bloquant. Le corps est écrit par l'appelant."""
    if session.info.get("courriel") is None:
        return False
    _ranger(session, [(adresse, sujet, corps, evenement)])
    return True


def _ranger(session: Session, avis: list[tuple[str, str, str, str]],
            whatsapp: list[tuple[str, str, str, str]] = ()) -> None:
    if not avis and not whatsapp:
        return
    if "avis" not in session.info:
        event.listen(session, "after_commit", _envoyer, once=True)
        event.listen(session, "after_rollback", _oublier, once=True)
    session.info.setdefault("avis", []).extend(avis)
    session.info.setdefault("avis_whatsapp", []).extend(whatsapp)


def _oublier(session: Session) -> None:
    session.info.pop("avis", None)
    session.info.pop("avis_whatsapp", None)


def _envoyer(session: Session) -> None:
    avis, messages = session.info.pop("avis", []), session.info.pop("avis_whatsapp", [])
    courriel, whatsapp = session.info.get("courriel"), session.info.get("whatsapp")
    avis = avis if courriel is not None else []
    messages = messages if whatsapp is not None else []
    if not avis and not messages:
        return
    # Le journal du développement et des tests, ou une tâche programmée (qui se termine aussitôt) : tout de suite.
    journaux = getattr(courriel, "envoyes", None) is not None or getattr(
        getattr(whatsapp, "expediteur", None), "envoyes", None) is not None
    if journaux or session.info.get("envoi_immediat"):
        _expedier(courriel, avis, whatsapp, messages)
    else:                                                   # un vrai serveur : sans faire attendre la réponse
        threading.Thread(target=_expedier, args=(courriel, avis, whatsapp, messages), daemon=True).start()


def _expedier(courriel, avis: list[tuple[str, str, str, str]], whatsapp=None,
              messages: list[tuple[str, str, str, str]] = ()) -> None:
    for adresse, sujet, corps, evenement in avis:
        try:
            courriel.envoyer(adresse, sujet, corps)
        except Exception as e:                              # noqa: BLE001 — un avis manqué ne défait pas l'acte
            journal.warning("[avis] %s non envoyé à %s… : %s", evenement, adresse[:2], type(e).__name__)
    for numero, sujet, lien, evenement in messages:
        try:
            whatsapp.envoyer(numero, sujet, lien)
        except Exception as e:                              # noqa: BLE001
            journal.warning("[avis] %s non envoyé sur WhatsApp à …%s : %s", evenement, numero[-2:], type(e).__name__)
