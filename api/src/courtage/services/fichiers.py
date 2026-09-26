"""Dépôt d'un fichier du personnel : lu, contrôlé en structure, gardé tel que lu (sans nom)."""
import hashlib
import uuid
from dataclasses import asdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import FichierPersonnel
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.fichier import Anomalie, Lecture, LigneLue, lire_fichier

from . import journaliser

# Une lecture qui échoue sur ces codes ne donne rien d'exploitable : le dépôt est refusé.
_STRUCTURELS = {"format_non_pris_en_charge", "colonnes_introuvables", "periodicite_inconnue",
                "periodicite_contradictoire", "fichier_vide"}


def deposer(session: Session, organisation_id: uuid.UUID, auteur: uuid.UUID, *, contenu: bytes, nom_fichier: str,
            date_donnees: date, periodicite: str | None) -> tuple[FichierPersonnel, Lecture]:
    lecture = lire_fichier(contenu, nom_fichier, periodicite=periodicite)
    structurels = [a for a in lecture.anomalies if a.code in _STRUCTURELS]
    if structurels:
        raise ErreurMetier("fichier_illisible", structurels[0].message, 422,
                           {"anomalies": [asdict(a) for a in lecture.anomalies]})
    fichier = FichierPersonnel(
        organisation_id=organisation_id, depose_par=auteur, nom_fichier=nom_fichier,
        empreinte=hashlib.sha256(contenu).hexdigest(), date_donnees=date_donnees,
        periodicite=lecture.periodicite,
        lignes=[_ligne_en_json(l) for l in lecture.lignes],
        anomalies=[asdict(a) for a in lecture.anomalies],
    )
    session.add(fichier)
    session.flush()
    journaliser(session, organisation_id, auteur, "fichier.depose", fichier.id,
                {"nom_fichier": nom_fichier, "effectif": len(lecture.lignes)})
    return fichier, lecture


def lister(session: Session) -> list[FichierPersonnel]:
    return list(session.scalars(select(FichierPersonnel).order_by(FichierPersonnel.depose_le.desc())))


def obtenir(session: Session, fichier_id: uuid.UUID) -> FichierPersonnel:
    fichier = session.get(FichierPersonnel, fichier_id)
    if fichier is None:
        raise Introuvable("Fichier")
    return fichier


def relire(fichier: FichierPersonnel) -> Lecture:
    """La lecture telle qu'enregistrée au dépôt, pour les contrôles et le calcul."""
    return Lecture(
        lignes=[LigneLue(
            numero=l["numero"], matricule=l["matricule"], sexe=l["sexe"],
            naissance=date.fromisoformat(l["naissance"]) if l["naissance"] else None,
            embauche=date.fromisoformat(l["embauche"]) if l["embauche"] else None,
            salaire_annuel=l["salaire_annuel"],
        ) for l in fichier.lignes],
        anomalies=[Anomalie(**a) for a in fichier.anomalies],
        periodicite=fichier.periodicite,
    )


def en_clair(f: FichierPersonnel) -> dict:
    return {
        "id": str(f.id), "nom_fichier": f.nom_fichier, "depose_le": f.depose_le.isoformat(),
        "date_donnees": f.date_donnees.isoformat(), "periodicite": f.periodicite,
        "effectif": len(f.lignes), "anomalies": f.anomalies,
    }


def _ligne_en_json(l: LigneLue) -> dict:
    return {
        "numero": l.numero, "matricule": l.matricule, "sexe": l.sexe,
        "naissance": l.naissance.isoformat() if l.naissance else None,
        "embauche": l.embauche.isoformat() if l.embauche else None,
        "salaire_annuel": l.salaire_annuel,
    }
