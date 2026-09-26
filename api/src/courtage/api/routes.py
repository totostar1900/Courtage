"""Routes de l'API. Les droits se lisent sur la signature : `acces(...)` nomme les rôles admis."""
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import Adhesion, Organisation, Utilisateur, contexte
from courtage.erreurs import ErreurMetier
from courtage.services import etudes, fichiers, journaliser, remuneration

from . import Acces, acces, identite, session_db

routeur = APIRouter()

CLIENT = ("admin_client", "conseiller")      # déposer, lancer une étude
CONSEIL = ("conseiller",)                    # émettre, fixer la rémunération
TOUS: tuple[str, ...] = ()                   # lire


class _Corps(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Moi, organisations, adhésions --------------------------------------------

@routeur.get("/moi")
def moi(session: Session = Depends(session_db), utilisateur: Utilisateur = Depends(identite)):
    rangs = session.execute(
        select(Organisation, Adhesion.role).join(Adhesion, Adhesion.organisation_id == Organisation.id)
        .where(Adhesion.utilisateur_id == utilisateur.id).order_by(Organisation.nom)).all()
    return {
        "id": str(utilisateur.id), "email": utilisateur.email, "telephone": utilisateur.telephone,
        "admin_plateforme": utilisateur.admin_plateforme,
        "organisations": [{"id": str(o.id), "nom": o.nom, "pays": o.pays, "role": r} for o, r in rangs],
    }


class NouvelleOrganisation(_Corps):
    nom: str = Field(min_length=1)
    pays: str = Field(pattern=r"^[A-Z]{2}$")
    secteur: str | None = None


@routeur.post("/organisations", status_code=201)
def creer_organisation(corps: NouvelleOrganisation, session: Session = Depends(session_db),
                       utilisateur: Utilisateur = Depends(identite)):
    if not utilisateur.admin_plateforme:
        raise ErreurMetier("acces_refuse", "Seule la plateforme ouvre un dossier client.", 403)
    org = Organisation(nom=corps.nom.strip(), pays=corps.pays, secteur=corps.secteur)
    session.add(org)
    session.flush()
    journaliser(session, None, utilisateur.id, "organisation.creee", org.id, {"nom": org.nom, "pays": org.pays})
    return {"id": str(org.id), "nom": org.nom, "pays": org.pays, "secteur": org.secteur}


class NouvelleAdhesion(_Corps):
    utilisateur_id: uuid.UUID
    role: Literal["admin_client", "lecteur_client", "conseiller"]


@routeur.post("/organisations/{organisation_id}/adhesions", status_code=201)
def ajouter_adhesion(organisation_id: uuid.UUID, corps: NouvelleAdhesion, session: Session = Depends(session_db),
                     utilisateur: Utilisateur = Depends(identite)):
    role_appelant = session.scalar(select(Adhesion.role).where(
        Adhesion.utilisateur_id == utilisateur.id, Adhesion.organisation_id == organisation_id))
    if not (utilisateur.admin_plateforme or role_appelant == "conseiller"):
        raise ErreurMetier("acces_refuse", "Seuls la plateforme et le conseiller du dossier ajoutent un membre.", 403)
    if session.get(Organisation, organisation_id) is None or session.get(Utilisateur, corps.utilisateur_id) is None:
        raise ErreurMetier("introuvable", "Organisation ou utilisateur introuvable.", 404)
    if session.get(Adhesion, (corps.utilisateur_id, organisation_id)) is not None:
        raise ErreurMetier("deja_membre", "Cet utilisateur est déjà membre de l'organisation.", 409)
    session.add(Adhesion(utilisateur_id=corps.utilisateur_id, organisation_id=organisation_id, role=corps.role))
    adhesion = {"utilisateur_id": str(corps.utilisateur_id), "role": corps.role}
    contexte(session.connection(), organisation_id)
    journaliser(session, organisation_id, utilisateur.id, "adhesion.ajoutee", corps.utilisateur_id, adhesion)
    return adhesion


# --- Rémunération -------------------------------------------------------------

class NouvellesConditions(_Corps):
    en_vigueur_du: date
    mode: Literal["honoraires", "commission", "mixte"]
    honoraires_etude_ifc: int = Field(default=0, ge=0)
    honoraires_par_salarie: int = Field(default=0, ge=0)
    commission_bps: int = Field(default=0, ge=0, le=10000)
    note: str | None = None


@routeur.post("/organisations/{organisation_id}/remuneration", status_code=201)
def fixer_remuneration(corps: NouvellesConditions, a: Acces = Depends(acces(*CONSEIL))):
    c = remuneration.fixer(a.session, a.organisation.id, a.utilisateur.id, **corps.model_dump())
    return remuneration.en_clair(c)


@routeur.get("/organisations/{organisation_id}/remuneration")
def lire_remuneration(a: Acces = Depends(acces(*TOUS))):
    courantes = remuneration.en_vigueur(a.session, date.today())
    return {
        "en_vigueur": remuneration.en_clair(courantes) if courantes else None,
        "historique": [remuneration.en_clair(c) for c in remuneration.historique(a.session)],
    }


# --- Fichiers -----------------------------------------------------------------

@routeur.post("/organisations/{organisation_id}/fichiers", status_code=201)
async def deposer_fichier(fichier: UploadFile = File(...), date_donnees: date = Form(...),
                          periodicite: Literal["mensuel", "annuel"] | None = Form(default=None),
                          a: Acces = Depends(acces(*CLIENT))):
    contenu = await fichier.read()
    f, lecture = fichiers.deposer(a.session, a.organisation.id, a.utilisateur.id, contenu=contenu,
                                  nom_fichier=fichier.filename or "fichier", date_donnees=date_donnees,
                                  periodicite=periodicite)
    return {**fichiers.en_clair(f), "colonnes": lecture.colonnes, "colonnes_ignorees": lecture.colonnes_ignorees}


@routeur.get("/organisations/{organisation_id}/fichiers")
def lister_fichiers(a: Acces = Depends(acces(*TOUS))):
    return [fichiers.en_clair(f) for f in fichiers.lister(a.session)]


# --- Études -------------------------------------------------------------------

class ParametresEtude(_Corps):
    fichier_id: uuid.UUID
    date_evaluation: date
    convention_code: str
    fonds_disponible: int = Field(ge=0)
    hypotheses: dict[str, float] = {}
    justification: str | None = None


def _saisie(p: ParametresEtude) -> etudes.Saisie:
    return etudes.Saisie(**p.model_dump())


@routeur.post("/organisations/{organisation_id}/etudes", status_code=201)
def creer_etude(corps: ParametresEtude, a: Acces = Depends(acces(*CLIENT))):
    e = etudes.creer(a.session, a.organisation, a.utilisateur.id, _saisie(corps))
    return etudes.en_clair(a.session, a.organisation, e, date.today())


@routeur.get("/organisations/{organisation_id}/etudes")
def lister_etudes(a: Acces = Depends(acces(*TOUS))):
    return [
        {"id": str(e.id), "statut": e.statut, "date_evaluation": e.date_evaluation.isoformat(),
         "convention_code": e.convention_code, "dette": e.resultats["totaux"]["dette"],
         "emise_le": e.emise_le.isoformat() if e.emise_le else None}
        for e in etudes.lister(a.session)
    ]


@routeur.get("/organisations/{organisation_id}/etudes/{etude_id}")
def lire_etude(etude_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    return etudes.en_clair(a.session, a.organisation, etudes.obtenir(a.session, etude_id), date.today())


@routeur.put("/organisations/{organisation_id}/etudes/{etude_id}")
def recalculer_etude(etude_id: uuid.UUID, corps: ParametresEtude, a: Acces = Depends(acces(*CLIENT))):
    e = etudes.recalculer(a.session, a.organisation, etudes.obtenir(a.session, etude_id), a.utilisateur.id,
                          _saisie(corps))
    return etudes.en_clair(a.session, a.organisation, e, date.today())


@routeur.delete("/organisations/{organisation_id}/etudes/{etude_id}", status_code=204)
def supprimer_etude(etude_id: uuid.UUID, a: Acces = Depends(acces(*CLIENT))):
    etudes.supprimer(a.session, etudes.obtenir(a.session, etude_id), a.utilisateur.id)
    return Response(status_code=204)


@routeur.post("/organisations/{organisation_id}/etudes/{etude_id}/emission")
def emettre_etude(etude_id: uuid.UUID, a: Acces = Depends(acces(*CONSEIL))):
    e = etudes.emettre(a.session, a.organisation, etudes.obtenir(a.session, etude_id), a.utilisateur.id, date.today())
    return etudes.en_clair(a.session, a.organisation, e, date.today())
