"""Contrats suivis (spec prestations §1) : le service rendu au client, daté.

En **courtage**, la plateforme est mandatée : elle portera les prestations
auprès de l'assureur et collectera, pour cela seulement, l'identité d'un
bénéficiaire. En **comparaison**, elle a éclairé le choix ; le client traite
seul avec son assureur et aucune identité n'est jamais demandée.

Un contrat ne se modifie pas : un nouveau s'ajoute avec sa date d'effet. Sans
contrat, le client est en comparaison — la plateforme ne suppose jamais un
mandat qu'elle n'a pas. Le service se lit ICI, jamais sur la rémunération.
"""
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from courtage.db import Contrat, DossierPriseEnCharge, Prestation
from courtage.erreurs import ErreurMetier

from . import journaliser, remuneration

Service = Literal["courtage", "comparaison"]


@dataclass(frozen=True)
class ServiceEnVigueur:
    service: Service
    contrat: Contrat | None


def enregistrer(session: Session, organisation_id: uuid.UUID, auteur: uuid.UUID, *, en_vigueur_du: date,
                service: Service, assureur: str | None = None, numero_police: str | None = None,
                date_effet_police: date | None = None, mandat_reference: str | None = None,
                note: str | None = None) -> Contrat:
    assureur = (assureur or "").strip() or None
    mandat_reference = (mandat_reference or "").strip() or None
    if service == "courtage" and not (assureur and mandat_reference):
        raise ErreurMetier("mandat_requis", "Un courtage suppose un assureur et un mandat signé par le client : "
                           "indiquez l'un et la référence de l'autre.", 422)
    contrat = Contrat(organisation_id=organisation_id, en_vigueur_du=en_vigueur_du, service=service, assureur=assureur,
                      numero_police=(numero_police or "").strip() or None, date_effet_police=date_effet_police,
                      mandat_reference=mandat_reference, note=note, cree_par=auteur)
    session.add(contrat)
    try:
        session.flush()
    except IntegrityError as e:
        if "contrats_organisation_id_en_vigueur_du_key" in str(e.orig):
            raise ErreurMetier("contrat_deja_enregistre",
                               f"Un contrat prend déjà effet le {en_vigueur_du:%d/%m/%Y}.", 409) from None
        raise
    journaliser(session, organisation_id, auteur, "contrat.enregistre", contrat.id,
                {"service": service, "en_vigueur_du": en_vigueur_du.isoformat()})
    return contrat


def historique(session: Session) -> list[Contrat]:
    return list(session.scalars(select(Contrat).order_by(Contrat.en_vigueur_du.desc())))


def service_a_la_date(session: Session, jour: date) -> ServiceEnVigueur:
    contrat = session.scalars(select(Contrat).where(Contrat.en_vigueur_du <= jour)
                              .order_by(Contrat.en_vigueur_du.desc()).limit(1)).first()
    return ServiceEnVigueur(contrat.service if contrat else "comparaison", contrat)


def constats(session: Session, jour: date) -> list[dict]:
    """Ce que le conseiller doit voir : une rémunération qui ne va pas avec le service."""
    service = service_a_la_date(session, jour).service
    conditions = remuneration.en_vigueur(session, jour)
    if conditions and conditions.commission_bps > 0 and service != "courtage":
        return [{"niveau": "avertit", "code": "commission_sans_mandat",
                 "message": "La rémunération prévoit une commission, mais aucun mandat de courtage n'est enregistré : "
                            "une commission se perçoit sur un contrat placé. Enregistrez le mandat, ou revoyez la "
                            "rémunération."}]
    return []


def en_clair(c: Contrat) -> dict:
    return {"id": str(c.id), "en_vigueur_du": c.en_vigueur_du.isoformat(), "service": c.service,
            "assureur": c.assureur, "numero_police": c.numero_police,
            "date_effet_police": c.date_effet_police.isoformat() if c.date_effet_police else None,
            "mandat_reference": c.mandat_reference, "note": c.note}


def raison_de_garder(session: Session, c: Contrat) -> str | None:
    """Un contrat qu'un dossier de prise en charge cite, ou dont la période couvre un départ enregistré, reste : il dit
    sous quel service ce départ a été traité. Sinon, saisi par erreur, il se supprime."""
    if session.scalar(select(func.count()).select_from(DossierPriseEnCharge).where(DossierPriseEnCharge.contrat_id == c.id)):
        return "Un dossier de prise en charge s'appuie sur ce contrat : il reste."
    suivant = session.scalar(select(func.min(Contrat.en_vigueur_du)).where(Contrat.en_vigueur_du > c.en_vigueur_du))
    requete = select(func.count()).select_from(Prestation).where(Prestation.date_depart >= c.en_vigueur_du)
    if suivant is not None:
        requete = requete.where(Prestation.date_depart < suivant)
    if session.scalar(requete):
        return "Des départs enregistrés tombent dans sa période : il dit sous quel service ils ont été traités."
    return None


def supprimer(session: Session, c: Contrat, auteur: uuid.UUID) -> None:
    if raison := raison_de_garder(session, c):
        raise ErreurMetier("contrat_utilise", raison, 409)
    journaliser(session, c.organisation_id, auteur, "contrat.supprime", c.id,
                {"en_vigueur_du": c.en_vigueur_du.isoformat(), "service": c.service})
    session.delete(c)
    session.flush()
