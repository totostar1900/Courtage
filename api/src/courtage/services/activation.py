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
    libelle = APRES_CONFIRMATION.get(capacite) or SOUS_MANDAT[capacite]
    if org.activation != "confirmee":
        raise ErreurMetier("inscription_non_confirmee",
                           f"Votre inscription attend la confirmation de votre conseiller : {libelle} s'ouvre ensuite.",
                           403, {"capacite": capacite})
    if capacite in SOUS_MANDAT and not sous_mandat(session, aujourd_hui or date.today()):
        raise ErreurMetier("mandat_requis",
                           f"Sans mandat de courtage signé, {libelle} ne s'ouvre pas encore : demandez un "
                           "accompagnement.", 409, {"capacite": capacite})


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
         "libelles": APRES_CONFIRMATION | SOUS_MANDAT,
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
        rccm_depose = session.scalar(select(func.count()).select_from(Justificatif)
                                     .where(Justificatif.organisation_id == o.id, Justificatif.nature == "rccm")) > 0
        e = echeance(o.activation_demandee_le)
        sortie.append({
            "id": str(o.id), "nom": o.nom, "pays": o.pays, "secteur": o.secteur, "rccm": o.rccm, "taille": o.taille,
            "adresse": o.adresse, "ville": o.ville, "demandee_le": o.activation_demandee_le.isoformat(),
            "echeance": e.isoformat(), "en_retard": aujourd_hui > e, "rccm_depose": rccm_depose,
            "expire_le": (o.activation_demandee_le + EXPIRATION).date().isoformat(),
            "messages_non_lus": _non_lus(session),
            "demandeur": None if demandeur is None else {
                "nom": demandeur[0].nom_affiche, "fonction": demandeur[1], "telephone": demandeur[0].telephone,
                "courriel": demandeur[0].email},
        })
    session.execute(text("SELECT set_config('app.organisation_id', '', true)"))
    return sortie


def _non_lus(session: Session) -> int:
    from . import messages
    return messages.non_lus(session, "courtier")


def decider(session: Session, org: Organisation, auteur, *, decision: str, verification: dict | None,
            motif: str | None, conseiller_id=None) -> None:
    """Confirmer (ce qui a été vérifié, le conseiller désigné) ou refuser (un motif que le client lit)."""
    from courtage.db import Adhesion, Utilisateur, contexte
    from . import journaliser
    if org.activation != "en_attente":
        raise ErreurMetier("deja_decidee", "Cette inscription a déjà été traitée.", 409)
    motif = (motif or "").strip() or None
    if decision == "refuser" and not motif:
        raise ErreurMetier("motif_requis", "Dire au client pourquoi son inscription est refusée.", 422)
    if decision not in ("confirmer", "refuser"):
        raise ErreurMetier("decision_inconnue", "Confirmer ou refuser.", 422)
    org.activation = "confirmee" if decision == "confirmer" else "refusee"
    org.activation_decidee_le, org.activation_par = func.now(), auteur
    org.activation_verification, org.activation_motif = verification or {}, motif
    contexte(session.connection(), org.id)
    if decision == "confirmer":
        conseiller = conseiller_id or auteur
        if session.get(Utilisateur, conseiller) is None:
            raise ErreurMetier("conseiller_inconnu", "Conseiller introuvable.", 422)
        if not session.scalar(select(func.count()).select_from(Adhesion).where(
                Adhesion.organisation_id == org.id, Adhesion.utilisateur_id == conseiller)):
            session.add(Adhesion(utilisateur_id=conseiller, organisation_id=org.id, role="conseiller"))
    session.flush()
    journaliser(session, org.id, auteur, f"inscription.{'confirmee' if decision == 'confirmer' else 'refusee'}",
                org.id, {"verification": verification or {}, "motif": motif})


# --- Le justificatif RCCM ------------------------------------------------------------

TYPES_JUSTIFICATIF = {"application/pdf", "image/jpeg", "image/png"}
TAILLE_MAX = 10 * 1024 * 1024


def deposer_rccm(session: Session, org: Organisation, auteur, contenu: bytes, nom_fichier: str, type_contenu: str):
    import hashlib
    from courtage.db import Justificatif
    from . import journaliser
    if type_contenu not in TYPES_JUSTIFICATIF:
        raise ErreurMetier("format_refuse", "Un PDF, un JPEG ou un PNG.", 422)
    if not contenu or len(contenu) > TAILLE_MAX:
        raise ErreurMetier("taille_refusee", "Un fichier de 10 Mo au plus.", 422)
    j = Justificatif(organisation_id=org.id, nature="rccm", nom_fichier=nom_fichier[:200], type_contenu=type_contenu,
                     contenu=contenu, empreinte=hashlib.sha256(contenu).hexdigest(), depose_par=auteur)
    session.add(j)
    session.flush()
    journaliser(session, org.id, auteur, "inscription.rccm_depose", j.id, {"empreinte": j.empreinte})
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
        raise ErreurMetier("inscription_confirmee", "Un dossier confirmé ne s'efface pas ainsi : le clôturer.", 409)
    contexte(session.connection(), org.id)
    compte = {}
    for modele in (MessageDossier, Justificatif, MandatCourtage, Prestation, ExtractionTexte, Etude):
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
