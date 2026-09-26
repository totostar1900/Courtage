"""Brancher l'expérience réelle (module `courtage.experience`) sur l'étude et le cahier des charges."""
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import DossierPriseEnCharge, Etude, EvenementDossier
from courtage.experience import (Depart, attendu_contre_reel, delais_constates, historique_publiable,
                                 paiements_du_fonds, rotation_observee)
from courtage.fichier import Anomalie

from . import prestations


def departs(session: Session) -> list[Depart]:
    return [Depart(matricule=p.matricule, date_depart=p.date_depart, motif=p.motif, du=p.du, verse=p.verse,
                   paye=p.part_fonds_payee, payee_le=p.payee_le) for p in prestations.actives(session)]


def etude_precedente(session: Session, date_evaluation: date, sauf: uuid.UUID | None = None) -> Etude | None:
    requete = (select(Etude).where(Etude.statut == "emise", Etude.date_evaluation < date_evaluation)
               .order_by(Etude.date_evaluation.desc()).limit(1))
    if sauf is not None:
        requete = requete.where(Etude.id != sauf)
    return session.scalars(requete).first()


def pour_etude(session: Session, *, date_evaluation: date, effectif: int, taux_turnover: float,
               sauf: uuid.UUID | None = None) -> dict | None:
    ds = departs(session)
    if not ds:
        return None
    precedente = etude_precedente(session, date_evaluation, sauf)
    return {
        "etude_precedente": {"date_evaluation": precedente.date_evaluation.isoformat()} if precedente else None,
        "attendu_contre_reel": attendu_contre_reel(
            ds, precedente.resultats.get("echeancier") if precedente else None, date_evaluation,
            precedente.date_evaluation.year if precedente else None),
        "rotation": rotation_observee(ds, effectif, date_evaluation, taux_turnover),
        "paiements_du_fonds": {
            "depuis": precedente.date_evaluation.isoformat() if precedente else None,
            "montant": paiements_du_fonds(ds, precedente.date_evaluation if precedente else None, date_evaluation)},
    }


def anomalies(session: Session, matricules_du_fichier: set[str], date_evaluation: date) -> list[Anomalie]:
    """Un salarié parti avant la date d'évaluation n'est plus dans l'engagement : s'il est dans le fichier, le dire."""
    partis = sorted({d.matricule for d in departs(session)
                     if d.date_depart <= date_evaluation and d.matricule in matricules_du_fichier})
    if not partis:
        return []
    return [Anomalie("avertissement", "parti_mais_dans_le_fichier",
                     f"{len(partis)} salarié(s) enregistré(s) comme parti(s) avant le {date_evaluation:%d/%m/%Y} "
                     f"figurent encore dans le fichier (matricules {', '.join(partis)}) : l'engagement les compte. "
                     "Retirez-les du fichier, ou corrigez le départ.")]


def pour_cahier(session: Session, jusqu_a: date) -> dict:
    """Ce que les assureurs reçoivent : l'historique regroupé et les délais constatés, rien d'individuel."""
    delais = []
    for d in session.scalars(select(DossierPriseEnCharge)):
        etapes = list(session.scalars(select(EvenementDossier).where(EvenementDossier.dossier_id == d.id)
                                      .order_by(EvenementDossier.cree_le)))
        envoi = next((e for e in reversed(etapes) if e.etape == "transmis"), None)
        paye = next((e for e in etapes if e.etape == "paye"), None)
        if envoi and paye and paye.le >= envoi.le:
            delais.append((paye.le - envoi.le).days)
    return {"historique": historique_publiable(departs(session), jusqu_a), "delais": delais_constates(delais)}
