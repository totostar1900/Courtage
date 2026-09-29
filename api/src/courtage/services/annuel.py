"""Le cycle annuel : l'engagement se remesure chaque année, à la même date (spec 2026-09-29, cycle annuel).

Le cycle part de la dernière étude émise : sa date d'évaluation D fixe la prochaine, N = D + 1 an. Chaque étape se
LIT dans les données — rien n'est coché, rien n'est stocké : un fichier du personnel daté de N ou après, une étude
émise au N ou après, un relevé de l'assureur daté de N ou après ; et, pour une police en vigueur, un rappel de revue
avant son anniversaire. Quand l'évaluation de N est émise, le cycle passe à N + 1 de lui-même.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from courtage.db import Etude, FichierPersonnel, PiecePolice, Police
from courtage.langue import t

from . import placement

BIENTOT = 30          # jours avant l'échéance où une étape devient « bientôt »
TRES_EN_RETARD = 30   # jours de retard au-delà desquels l'alerte devient grave
REVUE_AVANT = 60      # jours avant l'anniversaire de la police
# Le retard de ces étapes est déjà dit par `services.alertes` (« une nouvelle étude s'impose », « données anciennes ») :
# le calendrier n'ajoute que leur annonce, pas un second avertissement.
DEJA_ALERTES = ("personnel", "evaluation")


@dataclass(frozen=True)
class Etape:
    code: str
    libelle: str
    echeance: date
    fait_le: date | None
    etat: str             # fait | a_venir | bientot | en_retard
    pour: str             # entreprise | conseiller
    lien: str
    cle: str              # l'étape de CETTE année, pour les rappels


def _etat(echeance: date, fait_le: date | None, aujourd_hui: date) -> str:
    if fait_le is not None:
        return "fait"
    if aujourd_hui > echeance:
        return "en_retard"
    return "bientot" if (echeance - aujourd_hui).days <= BIENTOT else "a_venir"


def prochaine_evaluation(session: Session) -> tuple[date, date] | None:
    """(D, N) : la date de la dernière étude émise et celle de la suivante ; None sans étude émise."""
    d = session.scalar(select(func.max(Etude.date_evaluation)).where(Etude.statut == "emise"))
    return None if d is None else (d, d + relativedelta(years=1))


def calendrier(session: Session, aujourd_hui: date) -> dict:
    dn = prochaine_evaluation(session)
    if dn is None:
        return {"derniere": None, "prochaine": None, "etapes": []}
    derniere, n = dn
    fichier = session.scalar(select(func.min(FichierPersonnel.date_donnees)).where(
        FichierPersonnel.date_donnees >= n, FichierPersonnel.vide_le.is_(None)))
    etapes = [
        Etape("personnel", t("Mettre à jour le personnel", "Update the staff list"), n + timedelta(days=30),
              fichier, _etat(n + timedelta(days=30), fichier, aujourd_hui), "entreprise", "personnel",
              f"personnel:{n.isoformat()}"),
        # Une étude émise au N ou après : son émission vaut évaluation de l'année (le cycle passe alors à N + 1).
        Etape("evaluation", t("Émettre l'évaluation de l'année", "Issue the year's valuation"), n + timedelta(days=60),
              None, _etat(n + timedelta(days=60), None, aujourd_hui), "conseiller", "etudes",
              f"evaluation:{n.isoformat()}"),
    ]
    for p in session.scalars(select(Police)):
        if placement.statut(session, p, aujourd_hui)["code"] != "en_vigueur":
            continue
        releve = session.scalar(select(func.min(PiecePolice.releve_le)).where(
            PiecePolice.police_id == p.id, PiecePolice.nature == "releve", PiecePolice.releve_le >= n))
        echeance = n + timedelta(days=45)
        etapes.append(Etape("releve", t(f"Recevoir le relevé annuel de {p.assureur}", f"Receive {p.assureur}'s annual statement"),
                            echeance, releve, _etat(echeance, releve, aujourd_hui), "conseiller", "placement",
                            f"releve:{p.id}:{n.isoformat()}"))
        anniversaire = p.date_effet
        while anniversaire <= aujourd_hui:
            anniversaire += relativedelta(years=1)
        revue = anniversaire - timedelta(days=REVUE_AVANT)
        etat = "bientot" if aujourd_hui >= revue - timedelta(days=BIENTOT) else "a_venir"
        etapes.append(Etape("revue", t(f"Revoir le contrat {p.assureur} avant son anniversaire du {anniversaire:%d/%m/%Y}",
                                       f"Review the {p.assureur} contract before its anniversary on {anniversaire:%d/%m/%Y}"),
                            revue, None, etat, "conseiller", "placement", f"revue:{p.id}:{anniversaire.isoformat()}"))
    return {"derniere": derniere.isoformat(), "prochaine": n.isoformat(),
            "etapes": [{"code": e.code, "libelle": e.libelle, "echeance": e.echeance.isoformat(),
                        "fait_le": e.fait_le.isoformat() if e.fait_le else None, "etat": e.etat, "pour": e.pour,
                        "lien": e.lien, "cle": e.cle}
                       for e in sorted(etapes, key=lambda e: e.echeance)]}


def alertes(session: Session, aujourd_hui: date) -> list[tuple[str, str, str, str, str, str]]:
    """(niveau, code, titre, détail, lien, pour) — lues par `services.alertes`."""
    c = calendrier(session, aujourd_hui)
    sortie = []
    for e in c["etapes"]:
        echeance = date.fromisoformat(e["echeance"])
        if e["etat"] == "bientot":
            sortie.append(("info", f"annuel_{e['code']}", e["libelle"],
                           t(f"À faire d'ici le {echeance:%d/%m/%Y} : l'évaluation de l'année est au {date.fromisoformat(c['prochaine']):%d/%m/%Y}.",
                             f"To do by {echeance:%d/%m/%Y}: the year's valuation date is {date.fromisoformat(c['prochaine']):%d/%m/%Y}."),
                           e["lien"], e["pour"]))
        elif e["etat"] == "en_retard" and e["code"] not in DEJA_ALERTES:
            retard = (aujourd_hui - echeance).days
            sortie.append(("grave" if retard > TRES_EN_RETARD else "attention", f"annuel_{e['code']}", e["libelle"],
                           t(f"Attendu le {echeance:%d/%m/%Y}, en retard de {retard} jour(s).",
                             f"Due on {echeance:%d/%m/%Y}, {retard} day(s) late."), e["lien"], e["pour"]))
    return sortie
