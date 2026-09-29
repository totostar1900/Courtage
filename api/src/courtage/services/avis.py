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
    """Range un avis par destinataire ; rend leur nombre. Il part après la validation de la transaction."""
    courriel = session.info.get("courriel")
    if courriel is None:
        return 0
    sujet, texte, chemin = EVENEMENTS[evenement]
    valeurs = {"org": org, **valeurs}
    ids = {d for d in destinataires if d and d != auteur}
    if not ids:
        return 0
    adresses = [u.email for u in session.scalars(select(Utilisateur).where(Utilisateur.id.in_(ids)))
                if u.email and u.avis_courriel]
    lien = f"{(session.info.get('url_publique') or '').rstrip('/')}{chemin.format(**valeurs)}"
    corps = f"Bonjour,\n\n{texte.format(**valeurs)}\n\nOuvrir : {lien}{PIED}"
    en_attente = session.info.setdefault("avis", [])
    if not en_attente:
        event.listen(session, "after_commit", _envoyer, once=True)
        event.listen(session, "after_rollback", _oublier, once=True)
    en_attente.extend((a, sujet, corps, evenement) for a in adresses)
    return len(adresses)


def _oublier(session: Session) -> None:
    session.info.pop("avis", None)


def _envoyer(session: Session) -> None:
    avis, courriel = session.info.pop("avis", []), session.info.get("courriel")
    if not avis or courriel is None:
        return
    if getattr(courriel, "envoyes", None) is not None:      # le journal du développement et des tests : tout de suite
        _expedier(courriel, avis)
    else:                                                   # un vrai serveur : sans faire attendre la réponse
        threading.Thread(target=_expedier, args=(courriel, avis), daemon=True).start()


def _expedier(courriel, avis: list[tuple[str, str, str, str]]) -> None:
    for adresse, sujet, corps, evenement in avis:
        try:
            courriel.envoyer(adresse, sujet, corps)
        except Exception as e:                              # noqa: BLE001 — un avis manqué ne défait pas l'acte
            journal.warning("[avis] %s non envoyé à %s… : %s", evenement, adresse[:2], type(e).__name__)
