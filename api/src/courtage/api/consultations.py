"""Routes de la consultation des assureurs : envoyer, relancer, annuler (dossier, sous mandat) ; et le côté de
l'assureur, par son lien personnel, sans compte (`/offre/{jeton}`, limité en fréquence).

Spécification : docs/specs/2026-09-29-lien-assureur-design.md.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from courtage.services import activation, consultations, reponses

from . import Acces, acces, session_db
from .limites import limite
from .routes import _donnees, _offre, _piece_jointe

routeur_consultations = APIRouter()


class _Corps(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NouvelleConsultation(_Corps):
    assureur: str = Field(min_length=2, max_length=200)
    contact_nom: str | None = Field(default=None, max_length=200)
    contact_courriel: str = Field(min_length=3, max_length=200)


class DepotOffre(_Corps):
    """La grille de l'assureur : les champs de la saisie du conseiller, sans le nom (celui de la consultation) ni la
    date (celle du dépôt)."""
    taux_garanti: float = Field(ge=-0.05, le=0.2)
    participation_benefices: float = Field(ge=0, le=1)
    frais_sur_cotisations: float = Field(ge=0, le=0.2)
    frais_sur_encours: float = Field(ge=0, le=0.2)
    delai_paiement_jours: int | None = Field(default=None, ge=1, le=365)
    transfert_preavis_mois: int | None = Field(default=None, ge=0, le=60)
    transfert_penalite: float | None = Field(default=None, ge=0, le=1)
    accepte_etude_plateforme: bool | None = None
    reporting_annuel: bool | None = None
    historique_participation: str | None = Field(default=None, max_length=500)
    commentaire: str | None = Field(default=None, max_length=2000)


# --- Le dossier : le conseiller consulte ------------------------------------------------------

@routeur_consultations.get("/organisations/{organisation_id}/fiches/{fiche_id}/consultations")
def lire_consultations(fiche_id: uuid.UUID, a: Acces = Depends(acces())):
    return consultations.lister(a.session, reponses.obtenir_fiche(a.session, fiche_id), date.today())


@routeur_consultations.post("/organisations/{organisation_id}/fiches/{fiche_id}/consultations", status_code=201)
def consulter(fiche_id: uuid.UUID, corps: NouvelleConsultation, a: Acces = Depends(acces("conseiller"))):
    activation.exiger(a.session, a.organisation, "cahier")
    c = consultations.envoyer(a.session, a.organisation, a.utilisateur.id, reponses.obtenir_fiche(a.session, fiche_id),
                              **corps.model_dump(), aujourd_hui=date.today())
    return consultations.en_clair(a.session, c, date.today())


@routeur_consultations.post("/organisations/{organisation_id}/consultations/{consultation_id}/relance")
def relancer(consultation_id: uuid.UUID, a: Acces = Depends(acces("conseiller"))):
    activation.exiger(a.session, a.organisation, "cahier")
    c = consultations.relancer(a.session, a.organisation, a.utilisateur.id,
                               consultations.obtenir(a.session, consultation_id), date.today())
    return consultations.en_clair(a.session, c, date.today())


@routeur_consultations.post("/organisations/{organisation_id}/consultations/{consultation_id}/annulation")
def annuler(consultation_id: uuid.UUID, a: Acces = Depends(acces("conseiller"))):
    c = consultations.annuler(a.session, a.organisation, a.utilisateur.id,
                              consultations.obtenir(a.session, consultation_id))
    return consultations.en_clair(a.session, c, date.today())


# --- L'assureur, par son lien (sans compte) ------------------------------------------------------

@routeur_consultations.get("/offre/{jeton}", dependencies=[Depends(limite("offre"))])
def lire_offre(jeton: str, session: Session = Depends(session_db, scope="function")):
    return consultations.pour_l_assureur(session, jeton, date.today())


@routeur_consultations.get("/offre/{jeton}/cahier", dependencies=[Depends(limite("offre"))])
def telecharger_cahier(jeton: str, session: Session = Depends(session_db, scope="function")):
    nom, contenu, type_contenu = consultations.cahier(session, jeton)
    return Response(contenu, media_type=type_contenu, headers=_piece_jointe(nom))


@routeur_consultations.post("/offre/{jeton}", status_code=201, dependencies=[Depends(limite("offre"))])
async def deposer_offre(jeton: str, donnees: str = Form(...), offre: UploadFile | None = File(default=None),
                        session: Session = Depends(session_db, scope="function")):
    consultations.deposer(session, jeton, _donnees(donnees, DepotOffre), await _offre(offre), date.today())
    return consultations.pour_l_assureur(session, jeton, date.today())
