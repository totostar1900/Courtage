"""Routes du placement : le registre des comptes d'assureurs (courtier), la police, les appels de prime, les
virements déclarés et les relevés (dossier, sous mandat). La plateforme ne paie rien : elle trace.

Spécification : docs/specs/2026-09-29-cloture-du-placement-design.md.
"""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from courtage.db import Utilisateur
from courtage.services import comptes_assureurs

from . import session_db
from .inscription import _plateforme

routeur_placement = APIRouter()


class _Corps(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Le registre des comptes d'assureurs (administrateur de la plateforme) ---------------------------

class NouveauCompte(_Corps):
    assureur: str = Field(min_length=2, max_length=200)
    banque: str = Field(min_length=2, max_length=200)
    titulaire: str = Field(min_length=2, max_length=200)
    iban: str = Field(min_length=10, max_length=60)
    bic: str | None = Field(default=None, max_length=20)
    verifie_aupres: str = Field(min_length=1, max_length=200)
    verifie_telephone: str = Field(min_length=1, max_length=40)
    verifie_le: date
    note: str | None = Field(default=None, max_length=1000)


@routeur_placement.get("/assureurs/comptes")
def lire_registre(session: Session = Depends(session_db, scope="function"), _: Utilisateur = Depends(_plateforme)):
    return {"assureurs": comptes_assureurs.registre(session)}


@routeur_placement.post("/assureurs/comptes", status_code=201)
def enregistrer_compte(corps: NouveauCompte, session: Session = Depends(session_db, scope="function"),
                       moi: Utilisateur = Depends(_plateforme)):
    c = comptes_assureurs.enregistrer(session, moi.id, **corps.model_dump(), aujourd_hui=date.today())
    return comptes_assureurs.en_clair(session, c)
