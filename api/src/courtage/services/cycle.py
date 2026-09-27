"""Le cycle de vie d'un dossier client : ouvert, suspendu, clôturé, archivé ; supprimé s'il était vide.

Comme une banque clôture un compte sans l'effacer : chaque changement d'état est motivé, daté et signé, et
réversible tant que le dossier n'est pas archivé. Le conseiller seul décide.

- **Suspendu** (impayé, litige, pièces attendues) : tout se lit et s'exporte, rien ne s'émet (ni étude, ni cahier).
- **Clôturé** (fin de mandat, changement de courtier, cessation) : lecture seule, pour tous, pendant
  `DELAI_ARCHIVAGE` ; le conseiller peut encore le reprendre.
- **Archivé**, automatiquement au terme du délai : le personnel déposé est vidé (le fichier reste, son empreinte
  aussi), l'identité des bénéficiaires est effacée, les accès se ferment. Études, rapports scellés, sceaux et journal
  restent : un numéro de document se vérifie toujours.
- **Supprimé** : seulement un dossier vide, ouvert par erreur. Rien n'est effacé du journal ; le dossier disparaît
  des listes et ses membres le quittent.

Les durées de conservation au-delà de l'archivage sont à valider par un juriste (docs/specs, cycle de vie).
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from courtage.db import (Adhesion, Beneficiaire, Contrat, DossierPriseEnCharge, EtatDossier, Etude, FicheRegime,
                         FichierPersonnel, Organisation, PieceDossier, Prestation, Regime, contexte)
from courtage.erreurs import ErreurMetier

from . import journaliser

DELAI_ARCHIVAGE = timedelta(days=90)

MOTIFS = {
    "suspendre": {"impaye": "Impayé", "litige": "Litige", "attente_pieces": "Pièces attendues", "autre": "Autre motif"},
    "cloturer": {"fin_mandat": "Fin du mandat", "changement_courtier": "Changement de courtier",
                 "cessation_activite": "Cessation d'activité", "autre": "Autre motif"},
    "reprendre": {},
    "supprimer": {"ouvert_par_erreur": "Ouvert par erreur", "doublon": "Doublon", "autre": "Autre motif"},
}
# action : (états d'où elle part, état où elle mène)
TRANSITIONS = {
    "suspendre": ({"ouvert"}, "suspendu"),
    "cloturer": ({"ouvert", "suspendu"}, "cloture"),
    "reprendre": ({"suspendu", "cloture"}, "ouvert"),
    "supprimer": ({"ouvert", "suspendu"}, "supprime"),
}
LIBELLES = {"ouvert": "Ouvert", "suspendu": "Suspendu", "cloture": "Clôturé", "archive": "Archivé",
            "supprime": "Supprimé"}


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


# --- Ce que l'état permet ------------------------------------------------------

def exiger_ecriture(org: Organisation) -> None:
    """Toute écriture dans le dossier : refusée s'il est clôturé (ou au-delà)."""
    if org.etat == "cloture":
        raise ErreurMetier("dossier_cloture", "Ce dossier est clôturé : il se lit et s'exporte, il ne se modifie "
                                              "plus. Le conseiller peut le reprendre.", 409)
    if org.etat in ("archive", "supprime"):
        raise ErreurMetier("dossier_archive", "Ce dossier est archivé.", 409)


def exiger_emission(org: Organisation) -> None:
    """Émettre une étude, envoyer un cahier : refusé aussi quand le dossier est suspendu."""
    exiger_ecriture(org)
    if org.etat == "suspendu":
        raise ErreurMetier("dossier_suspendu", "Ce dossier est suspendu : rien ne s'émet tant qu'il n'est pas "
                                               "repris.", 409)


def exiger_accessible(org: Organisation) -> None:
    """Un dossier archivé ou supprimé ne s'ouvre plus ; ses documents se vérifient toujours par leur numéro."""
    if org.etat == "archive":
        raise ErreurMetier("dossier_archive", "Ce dossier est archivé : il ne s'ouvre plus. Ses documents se "
                                              "vérifient toujours par leur numéro.", 410)
    if org.etat == "supprime":
        raise ErreurMetier("dossier_supprime", "Ce dossier a été supprimé.", 410)


# --- Changer d'état ------------------------------------------------------------

def vide(session: Session) -> bool:
    """Rien n'a été déposé ni produit : ni personnel, ni régime, ni étude, ni cahier, ni contrat, ni départ."""
    for modele in (FichierPersonnel, Regime, Etude, FicheRegime, Contrat, Prestation, DossierPriseEnCharge):
        if session.scalar(select(func.count()).select_from(modele)):
            return False
    return True


def changer(session: Session, org: Organisation, auteur: uuid.UUID, action: str, motif_code: str | None,
            motif: str | None) -> EtatDossier:
    if action not in TRANSITIONS:
        raise ErreurMetier("action_inconnue", f"Action inconnue : {action}.", 422)
    depart, arrivee = TRANSITIONS[action]
    if org.etat not in depart:
        raise ErreurMetier("transition_impossible",
                           f"Un dossier {LIBELLES[org.etat].lower()} ne peut pas être {_participe(action)}.", 409)
    motif = (motif or "").strip() or None
    if MOTIFS[action]:
        if motif_code not in MOTIFS[action]:
            raise ErreurMetier("motif_requis", "Choisir un motif.", 422, {"motifs": list(MOTIFS[action])})
        if motif_code == "autre" and not motif:
            raise ErreurMetier("motif_requis", "Préciser le motif.", 422)
    else:
        motif_code = None
        if not motif:
            raise ErreurMetier("motif_requis", "Dire pourquoi le dossier reprend.", 422)
    if action == "supprimer" and not vide(session):
        raise ErreurMetier("dossier_non_vide", "Seul un dossier vide se supprime. Celui-ci a déjà des données ou des "
                                               "documents : le clôturer.", 409)
    org.etat, org.etat_depuis = arrivee, _maintenant()
    e = EtatDossier(organisation_id=org.id, etat=arrivee, action=action, motif_code=motif_code, motif=motif, par=auteur)
    session.add(e)
    if action == "supprimer":
        session.execute(delete(Adhesion).where(Adhesion.organisation_id == org.id))
    session.flush()
    journaliser(session, org.id, auteur, f"dossier.{arrivee}", org.id, {"motif_code": motif_code, "motif": motif})
    return e


def _participe(action: str) -> str:
    return {"suspendre": "suspendu", "cloturer": "clôturé", "reprendre": "repris", "supprimer": "supprimé"}[action]


# --- Archivage -----------------------------------------------------------------

def archivage_prevu(org: Organisation) -> date | None:
    return (org.etat_depuis + DELAI_ARCHIVAGE).date() if org.etat == "cloture" else None


def archiver_si_echu(session: Session, org: Organisation, aujourd_hui: date) -> bool:
    """Archive un dossier clôturé depuis le délai (le contexte RLS de l'organisation est posé par l'appelant)."""
    prevu = archivage_prevu(org)
    if prevu is None or prevu > aujourd_hui:
        return False
    maintenant = _maintenant()
    fichiers = session.execute(update(FichierPersonnel).where(FichierPersonnel.vide_le.is_(None))
                               .values(lignes=[], anomalies=[], vide_le=maintenant)).rowcount
    session.execute(delete(PieceDossier))
    session.execute(delete(Beneficiaire))
    org.etat, org.etat_depuis = "archive", maintenant
    session.add(EtatDossier(organisation_id=org.id, etat="archive", action="archiver", par=None,
                            motif=f"Clôturé depuis {DELAI_ARCHIVAGE.days} jours"))
    session.flush()
    journaliser(session, org.id, None, "dossier.archive", org.id, {"fichiers_vides": fichiers})
    return True


def archiver_echus_partout(moteur: Engine, aujourd_hui: date) -> int:
    """Pour la tâche programmée : chaque dossier clôturé, dans son propre contexte."""
    with moteur.connect() as c:
        clotures = list(c.execute(text("SELECT id FROM organisations WHERE etat = 'cloture'")).scalars())
    n = 0
    for org_id in clotures:
        with Session(moteur) as session, session.begin():
            contexte(session.connection(), org_id)
            n += archiver_si_echu(session, session.get(Organisation, org_id), aujourd_hui)
    return n


# --- Lire ----------------------------------------------------------------------

def en_clair(session: Session, org: Organisation) -> dict:
    from .rapport import nom_de
    from courtage.db import Utilisateur
    historique = [{
        "etat": e.etat, "libelle": LIBELLES[e.etat], "action": e.action, "motif_code": e.motif_code,
        "motif_libelle": MOTIFS.get(e.action, {}).get(e.motif_code) if e.motif_code else None, "motif": e.motif,
        "par": nom_de(session.get(Utilisateur, e.par)) if e.par else "la plateforme (automatique)",
        "le": e.le.isoformat(),
    } for e in session.scalars(select(EtatDossier).order_by(EtatDossier.le.desc()))]
    prevu = archivage_prevu(org)
    return {
        "etat": org.etat, "libelle": LIBELLES[org.etat], "depuis": org.etat_depuis.isoformat(),
        "archivage_prevu": prevu.isoformat() if prevu else None,
        "actions": [a for a, (depart, _) in TRANSITIONS.items() if org.etat in depart],
        "supprimable": org.etat in TRANSITIONS["supprimer"][0] and vide(session),
        "motifs": {a: [{"code": c, "libelle": l} for c, l in m.items()] for a, m in MOTIFS.items()},
        "historique": historique,
    }
