"""Dépôt d'un fichier du personnel : lu, contrôlé en structure, gardé tel que lu (sans nom)."""
import hashlib
import uuid
from dataclasses import asdict
from datetime import date

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from courtage.db import Etude, FichierPersonnel
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.fichier import Anomalie, Lecture, LigneLue, anomalies_en_clair, lire_fichier
from courtage.langue import t, traduire

from . import journaliser

# Une lecture qui échoue sur ces codes ne donne rien d'exploitable : le dépôt est refusé.
_STRUCTURELS = {"format_non_pris_en_charge", "colonnes_introuvables", "periodicite_inconnue",
                "periodicite_contradictoire", "fichier_vide"}


def deposer(session: Session, organisation_id: uuid.UUID, auteur: uuid.UUID, *, contenu: bytes, nom_fichier: str,
            date_donnees: date, periodicite: str | None) -> tuple[FichierPersonnel, Lecture]:
    lecture = lire_fichier(contenu, nom_fichier, periodicite=periodicite)
    structurels = [a for a in lecture.anomalies if a.code in _STRUCTURELS]
    if structurels:
        raise ErreurMetier("fichier_illisible", traduire(structurels[0].code, structurels[0].message), 422,
                           {"anomalies": anomalies_en_clair([asdict(a) for a in lecture.anomalies])})
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
            salaire_annuel=l["salaire_annuel"], categorie=l.get("categorie"),
        ) for l in fichier.lignes],
        anomalies=[Anomalie(**a) for a in fichier.anomalies],
        periodicite=fichier.periodicite,
    )


def en_clair(f: FichierPersonnel) -> dict:
    return {
        "id": str(f.id), "nom_fichier": f.nom_fichier, "depose_le": f.depose_le.isoformat(),
        "date_donnees": f.date_donnees.isoformat(), "periodicite": f.periodicite,
        "effectif": len(f.lignes), "anomalies": anomalies_en_clair(f.anomalies),
        "vide_le": f.vide_le.isoformat() if f.vide_le else None,
    }


def _ligne_en_json(l: LigneLue) -> dict:
    return {
        "numero": l.numero, "matricule": l.matricule, "sexe": l.sexe,
        "naissance": l.naissance.isoformat() if l.naissance else None,
        "embauche": l.embauche.isoformat() if l.embauche else None,
        "salaire_annuel": l.salaire_annuel, "categorie": l.categorie,
    }


# --- Supprimer, alléger ----------------------------------------------------------

def usages(session: Session, f: FichierPersonnel) -> dict:
    """Ce qui s'appuie sur le fichier : des études émises (qui le retiennent), des brouillons (qui partent avec)."""
    etudes = session.execute(select(Etude.id, Etude.statut).where(Etude.fichier_id == f.id)).all()
    return {"etudes_emises": sum(1 for e in etudes if e.statut == "emise"),
            "brouillons": [str(e.id) for e in etudes if e.statut == "brouillon"]}


def _sans_brouillons(session: Session, f: FichierPersonnel, auteur: uuid.UUID) -> int:
    from . import etudes as service_etudes
    brouillons = usages(session, f)["brouillons"]
    for i in brouillons:
        service_etudes.supprimer(session, session.get(Etude, uuid.UUID(i)), auteur)
    return len(brouillons)


def supprimer(session: Session, f: FichierPersonnel, auteur: uuid.UUID) -> dict:
    """Le fichier disparaît, avec ses études en brouillon. Cité par une étude émise, il ne part pas : il s'allège."""
    if n := usages(session, f)["etudes_emises"]:
        raise ErreurMetier("fichier_cite", t(
            f"{n} étude{'s' if n > 1 else ''} émise{'s' if n > 1 else ''} "
            f"s'appuie{'nt' if n > 1 else ''} sur ce fichier : l'alléger (vider ses "
            "lignes) plutôt que le supprimer ; son empreinte reste.",
            f"{n} issued stud{'ies' if n > 1 else 'y'} rel{'y' if n > 1 else 'ies'} on this file: slim it down (empty its "
            "rows) rather than delete it; its fingerprint remains."), 409)
    brouillons = _sans_brouillons(session, f, auteur)
    journaliser(session, f.organisation_id, auteur, "fichier.supprime", f.id,
                {"nom_fichier": f.nom_fichier, "date_donnees": f.date_donnees.isoformat(), "brouillons": brouillons})
    session.delete(f)
    session.flush()
    return {"supprime": True, "brouillons": brouillons}


def alleger(session: Session, f: FichierPersonnel, auteur: uuid.UUID) -> dict:
    """Vider les lignes et garder le nom, la date et l'empreinte : ce qu'une étude émise cite reste prouvé. Les
    brouillons, qui auraient besoin des lignes pour se recalculer, partent."""
    if f.vide_le is not None:
        raise ErreurMetier("deja_allege", t("Ce fichier est déjà allégé.", "This file has already been slimmed down."), 409)
    brouillons = _sans_brouillons(session, f, auteur)
    effectif = len(f.lignes)
    session.execute(update(FichierPersonnel).where(FichierPersonnel.id == f.id)
                    .values(lignes=[], anomalies=[], vide_le=datetime.now(timezone.utc)))
    session.refresh(f)
    journaliser(session, f.organisation_id, auteur, "fichier.allege", f.id,
                {"effectif": effectif, "brouillons": brouillons})
    return {"allege": True, "brouillons": brouillons}
