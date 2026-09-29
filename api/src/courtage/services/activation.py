"""Ce que l'état d'une inscription permet : tout le travail dès l'inscription ; ce qui sort de la plateforme après
confirmation par le courtier ; ce qui touche aux assureurs sous mandat.

Le contrôle est ici, côté serveur, pour chaque route concernée (`exiger`) ; l'écran grise l'action et dit pourquoi
avec les mêmes libellés (`en_clair`). Spécification : docs/specs/2026-09-28-inscription-et-courtage-seul-design.md.
"""
import re
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from courtage.db import MandatCourtage, Organisation
from courtage.erreurs import ErreurMetier
from courtage.langue import t

from . import contrats

DELAI_JOURS_OUVRES = 2
EXPIRATION = timedelta(days=30)

# Ce qui sort de la plateforme ou engage l'entreprise : après confirmation.
APRES_CONFIRMATION = {
    "rapport_scelle": "l'émission d'un rapport scellé",
    "export_etude": "l'export Excel d'une étude",
    "notes_regime": "les notes de régime scellées",
    "fiche_de_calcul": "la fiche de calcul scellée",
    "equipe": "l'invitation de collègues et leurs droits",
    "catalogue": "le catalogue anonyme",
    "extraction_claude": "la lecture d'un texte par Claude",
    "mandat": "la proposition et la signature du mandat",
}
# Ce qui touche aux assureurs : sous mandat.
SOUS_MANDAT = {
    "cahier": "le cahier des charges et la consultation des assureurs",
}
# Les mêmes libellés pour l'écran anglais : lus au moment de la requête (`libelle`, `libelles`), jamais figés.
_EN = {
    "rapport_scelle": "issuing a sealed report",
    "export_etude": "the Excel export of a study",
    "notes_regime": "the sealed plan notes",
    "fiche_de_calcul": "the sealed calculation sheet",
    "equipe": "inviting colleagues and setting their rights",
    "catalogue": "the anonymous catalogue",
    "extraction_claude": "having Claude read a text",
    "mandat": "proposing and signing the mandate",
    "cahier": "the tender specifications and the consultation of insurers",
}


def libelle(capacite: str) -> str:
    fr = APRES_CONFIRMATION.get(capacite) or SOUS_MANDAT[capacite]
    return t(fr, _EN[capacite])


def libelles() -> dict[str, str]:
    return {c: libelle(c) for c in APRES_CONFIRMATION | SOUS_MANDAT}


def normaliser_rccm(saisi: str) -> str:
    """Pour l'unicité seulement : majuscules, sans espaces ni séparateurs. Les registres ont des formats différents :
    on ne valide pas un format, on compare des numéros."""
    return re.sub(r"[^A-Z0-9]", "", (saisi or "").upper())


def sous_mandat(session: Session, aujourd_hui: date) -> bool:
    """Un mandat signé sur la plateforme, ou un contrat de courtage en vigueur (enregistré par le conseiller)."""
    if session.scalar(select(func.count()).select_from(MandatCourtage).where(MandatCourtage.statut == "signe")):
        return True
    return contrats.service_a_la_date(session, aujourd_hui).service == "courtage"


def exiger(session: Session, org: Organisation, capacite: str, aujourd_hui: date | None = None) -> None:
    if capacite not in APRES_CONFIRMATION and capacite not in SOUS_MANDAT:
        raise ValueError(f"capacité inconnue : {capacite}")
    quoi = libelle(capacite)
    if org.activation != "confirmee":
        raise ErreurMetier("inscription_non_confirmee",
                           t(f"Votre inscription attend la confirmation de votre conseiller : {quoi} s'ouvre ensuite.",
                             f"Your sign-up is awaiting your adviser's confirmation: {quoi} opens after that."),
                           403, {"capacite": capacite})
    if capacite in SOUS_MANDAT and not sous_mandat(session, aujourd_hui or date.today()):
        raise ErreurMetier("mandat_requis",
                           t(f"Sans mandat de courtage signé, {quoi} ne s'ouvre pas encore : demandez un "
                             "accompagnement.",
                             f"Without a signed brokerage mandate, {quoi} is not available yet: ask for support."),
                           409, {"capacite": capacite})


def echeance(demandee_le: datetime) -> date:
    """Deux jours ouvrés après la demande : samedi et dimanche ne comptent pas."""
    jour, restants = demandee_le.date(), DELAI_JOURS_OUVRES
    while restants:
        jour += timedelta(days=1)
        if jour.weekday() < 5:
            restants -= 1
    return jour


def en_clair(session: Session, org: Organisation, aujourd_hui: date) -> dict:
    confirmee = org.activation == "confirmee"
    mandat = confirmee and sous_mandat(session, aujourd_hui)
    capacites = {c: confirmee for c in APRES_CONFIRMATION} | {c: mandat for c in SOUS_MANDAT}
    d = {"etat": org.activation, "capacites": capacites,
         "libelles": libelles(),
         "rccm": org.rccm, "taille": org.taille, "adresse": org.adresse, "ville": org.ville,
         "demandee_le": org.activation_demandee_le.isoformat() if org.activation_demandee_le else None,
         "decidee_le": org.activation_decidee_le.isoformat() if org.activation_decidee_le else None,
         "motif": org.activation_motif}
    if org.activation == "en_attente" and org.activation_demandee_le:
        d["echeance"] = echeance(org.activation_demandee_le).isoformat()
        d["expire_le"] = (org.activation_demandee_le + EXPIRATION).date().isoformat()
    return d


# --- La file du courtier -----------------------------------------------------------

def file_d_attente(session: Session, aujourd_hui: date) -> list[dict]:
    """Les inscriptions à vérifier, la plus ancienne d'abord. `organisations` est hors RLS : la plateforme lit tout."""
    from courtage.db import Adhesion, Justificatif, Utilisateur
    from sqlalchemy import text
    rangs = session.scalars(select(Organisation).where(Organisation.activation == "en_attente",
                                                       Organisation.etat.not_in(("archive", "supprime")))
                            .order_by(Organisation.activation_demandee_le))
    sortie = []
    for o in rangs:
        demandeur = session.execute(
            select(Utilisateur, Adhesion.fonction).join(Adhesion, Adhesion.utilisateur_id == Utilisateur.id)
            .where(Adhesion.organisation_id == o.id, Adhesion.role == "admin_client")
            .order_by(Adhesion.cree_le).limit(1)).first()
        session.execute(text("SELECT set_config('app.organisation_id', :o, true)"), {"o": str(o.id)})
        pieces = [{"id": str(j.id), "nom_fichier": j.nom_fichier, "depose_le": j.depose_le.isoformat()}
                  for j in session.scalars(select(Justificatif).where(Justificatif.organisation_id == o.id)
                                           .order_by(Justificatif.depose_le.desc()))]
        rccm_depose = bool(pieces)
        accompagnement = session.scalar(select(func.count()).select_from(MandatCourtage).where(
            MandatCourtage.organisation_id == o.id, MandatCourtage.statut.in_(("demande", "propose"))))
        e = echeance(o.activation_demandee_le)
        sortie.append({
            "id": str(o.id), "nom": o.nom, "pays": o.pays, "secteur": o.secteur, "rccm": o.rccm, "taille": o.taille,
            "adresse": o.adresse, "ville": o.ville, "demandee_le": o.activation_demandee_le.isoformat(),
            "echeance": e.isoformat(), "en_retard": aujourd_hui > e, "rccm_depose": rccm_depose, "justificatifs": pieces,
            "expire_le": (o.activation_demandee_le + EXPIRATION).date().isoformat(),
            "messages_non_lus": _non_lus(session), "accompagnement_demande": bool(accompagnement),
            "demandeur": None if demandeur is None else {
                "nom": demandeur[0].nom_affiche, "fonction": demandeur[1], "telephone": demandeur[0].telephone,
                "courriel": demandeur[0].email},
        })
    session.execute(text("SELECT set_config('app.organisation_id', '', true)"))
    return sortie


def _non_lus(session: Session) -> int:
    from . import messages
    return messages.non_lus(session, "courtier")


def conseillers(session: Session, moi) -> list[dict]:
    """Qui peut suivre un dossier : les administrateurs de la plateforme et quiconque est déjà conseiller d'un dossier,
    avec le nombre de dossiers qu'il suit (pour répartir). `adhesions` est hors RLS : la plateforme lit tout."""
    from courtage.db import Adhesion, Utilisateur
    suivis = (select(Adhesion.utilisateur_id, func.count().label("n")).where(Adhesion.role == "conseiller")
              .group_by(Adhesion.utilisateur_id).subquery())
    rangs = session.execute(
        select(Utilisateur, func.coalesce(suivis.c.n, 0)).outerjoin(suivis, suivis.c.utilisateur_id == Utilisateur.id)
        .where((Utilisateur.admin_plateforme.is_(True)) | (suivis.c.n > 0)).order_by(Utilisateur.nom_affiche))
    return [{"id": str(u.id), "nom": u.nom_affiche or u.email or u.telephone, "courriel": u.email,
             "dossiers": n, "moi": u.id == moi} for u, n in rangs]


def decider(session: Session, org: Organisation, auteur, *, decision: str, verification: dict | None,
            motif: str | None, conseiller_id=None) -> None:
    """Confirmer (ce qui a été vérifié, le conseiller désigné) ou refuser (un motif que le client lit)."""
    from courtage.db import Adhesion, Utilisateur, contexte
    from . import journaliser
    if org.activation != "en_attente":
        raise ErreurMetier("deja_decidee", t("Cette inscription a déjà été traitée.", "This sign-up has already been processed."), 409)
    motif = (motif or "").strip() or None
    if decision == "refuser" and not motif:
        raise ErreurMetier("motif_requis", t("Dire au client pourquoi son inscription est refusée.", "Tell the client why their sign-up is refused."), 422)
    if decision not in ("confirmer", "refuser"):
        raise ErreurMetier("decision_inconnue", t("Confirmer ou refuser.", "Confirm or refuse."), 422)
    org.activation = "confirmee" if decision == "confirmer" else "refusee"
    org.activation_decidee_le, org.activation_par = func.now(), auteur
    org.activation_verification, org.activation_motif = verification or {}, motif
    contexte(session.connection(), org.id)
    if decision == "confirmer":
        conseiller = conseiller_id or auteur
        if str(conseiller) not in {c["id"] for c in conseillers(session, auteur)}:
            raise ErreurMetier("conseiller_inconnu", t("Choisir un conseiller de la plateforme.", "Choose an adviser from the platform."), 422)
        if not session.scalar(select(func.count()).select_from(Adhesion).where(
                Adhesion.organisation_id == org.id, Adhesion.utilisateur_id == conseiller)):
            session.add(Adhesion(utilisateur_id=conseiller, organisation_id=org.id, role="conseiller"))
    session.flush()
    from . import avis
    avis.prevoir(session, "inscription_confirmee" if decision == "confirmer" else "inscription_refusee",
                 avis.entreprise(session, org.id), auteur=auteur, org=org.id, entreprise=org.nom, motif=motif or "")
    journaliser(session, org.id, auteur, f"inscription.{'confirmee' if decision == 'confirmer' else 'refusee'}",
                org.id, {"verification": verification or {}, "motif": motif})


# --- Les justificatifs : le RCCM (inscription), la délégation de pouvoir (mandat) ---------------

TYPES_JUSTIFICATIF = {"application/pdf", "image/jpeg", "image/png"}
TAILLE_MAX = 10 * 1024 * 1024


NATURES_JUSTIFICATIF = ("rccm", "delegation")


def deposer_justificatif(session: Session, org: Organisation, auteur, contenu: bytes, nom_fichier: str,
                         type_contenu: str, nature: str = "rccm"):
    import hashlib
    from courtage.db import Justificatif
    from . import journaliser
    if nature not in NATURES_JUSTIFICATIF:
        raise ErreurMetier("nature_inconnue", t("Un justificatif RCCM ou une délégation de pouvoir.",
                                                "An RCCM document or a delegation of authority."), 422)
    if type_contenu not in TYPES_JUSTIFICATIF:
        raise ErreurMetier("format_refuse", t("Un PDF, un JPEG ou un PNG.", "A PDF, JPEG or PNG."), 422)
    if not contenu or len(contenu) > TAILLE_MAX:
        raise ErreurMetier("taille_refusee", t("Un fichier de 10 Mo au plus.", "A file of 10 MB at most."), 422)
    j = Justificatif(organisation_id=org.id, nature=nature, nom_fichier=nom_fichier[:200], type_contenu=type_contenu,
                     contenu=contenu, empreinte=hashlib.sha256(contenu).hexdigest(), depose_par=auteur)
    session.add(j)
    session.flush()
    journaliser(session, org.id, auteur,
                "inscription.rccm_depose" if nature == "rccm" else "mandat.delegation_deposee", j.id,
                {"empreinte": j.empreinte})
    return j


def justificatifs(session: Session) -> list[dict]:
    from courtage.db import Justificatif
    return [{"id": str(j.id), "nature": j.nature, "nom_fichier": j.nom_fichier, "depose_le": j.depose_le.isoformat()}
            for j in session.scalars(select(Justificatif).order_by(Justificatif.depose_le.desc()))]


# --- L'effacement d'une inscription jamais confirmée --------------------------------------

def effacer(session: Session, org: Organisation, auteur, raison: str) -> dict:
    """Tout ce que le dossier contient part ; le journal (quelques lignes, sans donnée du personnel) reste, et le
    dossier est marqué supprimé. Refusé pour un dossier confirmé (et la base le refuse aussi)."""
    from courtage.db import (Adhesion, Etude, ExtractionTexte, FichierPersonnel, Justificatif,
                             MandatCourtage, MessageDossier, Prestation, Regime, VersionRegime, contexte)
    from sqlalchemy import delete
    from . import journaliser, regimes
    if org.activation == "confirmee":
        raise ErreurMetier("inscription_confirmee", t("Un dossier confirmé ne s'efface pas ainsi : le clôturer.", "A confirmed file cannot be erased this way: close it instead."), 409)
    contexte(session.connection(), org.id)
    compte = {}
    for modele in (MessageDossier, MandatCourtage, Justificatif, Prestation, ExtractionTexte, Etude):
        compte[modele.__tablename__] = session.execute(delete(modele)).rowcount
    for v in list(session.scalars(select(VersionRegime))):
        regimes.supprimer(session, v, auteur, "admin_client", raison)
    session.execute(delete(Regime))
    compte["fichiers_personnel"] = session.execute(delete(FichierPersonnel)).rowcount
    session.execute(delete(Adhesion).where(Adhesion.organisation_id == org.id))
    org.etat, org.etat_depuis = "supprime", func.now()
    session.flush()
    journaliser(session, org.id, auteur, "inscription.effacee", org.id, {"raison": raison, **compte})
    return compte


def effacer_expirees_partout(moteur, maintenant: datetime) -> int:
    """Pour la tâche programmée : chaque inscription en attente ou refusée depuis plus de 30 jours."""
    from sqlalchemy import text
    from sqlalchemy.orm import Session as S
    from courtage.db import contexte
    with moteur.connect() as c:
        ids = list(c.execute(text(
            "SELECT id FROM organisations WHERE activation <> 'confirmee' AND etat <> 'supprime' "
            "AND activation_demandee_le < :limite"), {"limite": maintenant - EXPIRATION}).scalars())
    for org_id in ids:
        with S(moteur) as session, session.begin():
            contexte(session.connection(), org_id)
            effacer(session, session.get(Organisation, org_id), None, "inscription non confirmée depuis 30 jours")
    return len(ids)
