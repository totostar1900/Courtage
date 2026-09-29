"""Routes du placement : le registre des comptes d'assureurs (courtier), la police, les appels de prime, les
virements déclarés et les relevés (dossier, sous mandat). La plateforme ne paie rien : elle trace.

Spécification : docs/specs/2026-09-29-cloture-du-placement-design.md.
"""
import uuid
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from courtage.db import Utilisateur
from courtage.erreurs import ErreurMetier
from courtage.langue import t
from courtage.services import activation, comptes_assureurs, placement

from . import Acces, acces, session_db
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


# --- Le placement d'un dossier (sous mandat) -------------------------------------------------------

TOUS: tuple[str, ...] = ()        # tout membre du dossier
# Qui dépose quelle pièce : le conseiller range ce que l'assureur envoie ; l'entreprise, sa copie signée et ses avis
# de virement.
DEPOSANTS = {"police": ("conseiller",), "avenant": ("conseiller",), "appel": ("conseiller",),
             "quittance": ("conseiller",), "releve": ("conseiller",),
             "police_signee": ("conseiller", "admin_client"),
             "avis_virement": ("conseiller", "admin_client", "contributeur_client")}


def _sous_mandat(a: Acces) -> None:
    activation.exiger(a.session, a.organisation, "cahier")


class NouvellePolice(_Corps):
    choix_id: uuid.UUID | None = None
    assureur: str | None = Field(default=None, max_length=200)
    date_effet: date
    periodicite: str = Field(max_length=20)
    numero_police: str | None = Field(default=None, max_length=100)


class Numero(_Corps):
    numero_police: str = Field(min_length=1, max_length=100)


class Signature(_Corps):
    signee_le: date


class NouvelAppel(_Corps):
    reference: str = Field(min_length=1, max_length=100)
    montant: int = Field(gt=0)
    echeance: date
    premiere: bool = False
    banque: str = Field(min_length=2, max_length=200)
    titulaire: str = Field(min_length=2, max_length=200)
    iban: str = Field(min_length=10, max_length=60)
    bic: str | None = Field(default=None, max_length=20)


class ContreAppel(_Corps):
    aupres: str = Field(min_length=1, max_length=200)
    telephone: str = Field(min_length=1, max_length=40)
    le: date


class Virement(_Corps):
    vire_le: date
    montant: int = Field(gt=0)
    reference: str | None = Field(default=None, max_length=100)


class Encaissement(_Corps):
    encaisse_le: date


def _police(a: Acces, police_id: uuid.UUID):
    return placement.obtenir(a.session, police_id)


@routeur_placement.get("/organisations/{organisation_id}/placement")
def lire_placement(a: Acces = Depends(acces(*TOUS))):
    return placement.tableau(a.session, date.today())


@routeur_placement.post("/organisations/{organisation_id}/polices", status_code=201)
def creer_police(corps: NouvellePolice, a: Acces = Depends(acces("conseiller"))):
    _sous_mandat(a)
    p = placement.creer(a.session, a.organisation, a.utilisateur.id, **corps.model_dump())
    return placement.police_en_clair(a.session, p, date.today())


@routeur_placement.put("/organisations/{organisation_id}/polices/{police_id}/numero")
def numeroter_police(police_id: uuid.UUID, corps: Numero, a: Acces = Depends(acces("conseiller"))):
    p = placement.numeroter(a.session, a.organisation, a.utilisateur.id, _police(a, police_id), corps.numero_police)
    return placement.police_en_clair(a.session, p, date.today())


@routeur_placement.post("/organisations/{organisation_id}/polices/{police_id}/pieces", status_code=201)
async def deposer_piece(police_id: uuid.UUID, nature: str = Form(...), fichier: UploadFile = File(...),
                        appel_id: uuid.UUID | None = Form(default=None), releve_le: date | None = Form(default=None),
                        montant_fonds: int | None = Form(default=None), a: Acces = Depends(acces(*TOUS))):
    if a.role not in DEPOSANTS.get(nature, ()):
        raise ErreurMetier("acces_refuse", t("Votre rôle ne dépose pas cette pièce.",
                                             "Your role does not upload this document."), 403)
    _sous_mandat(a)
    p = _police(a, police_id)
    appel = placement.obtenir_appel(a.session, appel_id) if appel_id else None
    x = placement.deposer(a.session, a.organisation, a.utilisateur.id, p, nature=nature, contenu=await fichier.read(),
                          nom_fichier=fichier.filename or nature, type_contenu=fichier.content_type or "",
                          appel=appel, releve_le=releve_le, montant_fonds=montant_fonds, aujourd_hui=date.today())
    return {"id": str(x.id), "nature": x.nature, "nom_fichier": x.nom_fichier}


@routeur_placement.get("/organisations/{organisation_id}/polices/{police_id}/pieces/{piece_id}")
def lire_piece(police_id: uuid.UUID, piece_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    x = placement.piece(a.session, _police(a, police_id), piece_id)
    return Response(x.contenu, media_type=x.type_contenu,
                    headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(x.nom_fichier)}"})


@routeur_placement.post("/organisations/{organisation_id}/polices/{police_id}/signature")
def signer_police(police_id: uuid.UUID, corps: Signature, a: Acces = Depends(acces("admin_client", "conseiller"))):
    _sous_mandat(a)
    p = placement.signer(a.session, a.organisation, a.utilisateur.id, _police(a, police_id),
                         signee_le=corps.signee_le, aujourd_hui=date.today())
    return placement.police_en_clair(a.session, p, date.today())


@routeur_placement.post("/organisations/{organisation_id}/polices/{police_id}/appels", status_code=201)
def enregistrer_appel(police_id: uuid.UUID, corps: NouvelAppel, a: Acces = Depends(acces("conseiller"))):
    _sous_mandat(a)
    x = placement.enregistrer_appel(a.session, a.organisation, a.utilisateur.id, _police(a, police_id),
                                    **corps.model_dump())
    return placement.appel_en_clair(a.session, x, date.today())


@routeur_placement.post("/organisations/{organisation_id}/appels/{appel_id}/contre-appel")
def enregistrer_contre_appel(appel_id: uuid.UUID, corps: ContreAppel, a: Acces = Depends(acces("conseiller"))):
    x = placement.contre_appel(a.session, a.organisation, a.utilisateur.id, placement.obtenir_appel(a.session, appel_id),
                               **corps.model_dump(), aujourd_hui=date.today())
    return placement.appel_en_clair(a.session, x, date.today())


@routeur_placement.post("/organisations/{organisation_id}/appels/{appel_id}/virement")
def declarer_virement(appel_id: uuid.UUID, corps: Virement,
                      a: Acces = Depends(acces("admin_client", "contributeur_client"))):
    x = placement.declarer(a.session, a.organisation, a.utilisateur.id, placement.obtenir_appel(a.session, appel_id),
                           vire_le=corps.vire_le, montant=corps.montant, reference=corps.reference,
                           aujourd_hui=date.today())
    return placement.appel_en_clair(a.session, x, date.today())


@routeur_placement.post("/organisations/{organisation_id}/appels/{appel_id}/encaissement")
def confirmer_encaissement(appel_id: uuid.UUID, corps: Encaissement, a: Acces = Depends(acces("conseiller"))):
    x = placement.confirmer(a.session, a.organisation, a.utilisateur.id, placement.obtenir_appel(a.session, appel_id),
                            encaisse_le=corps.encaisse_le, aujourd_hui=date.today())
    return placement.appel_en_clair(a.session, x, date.today())
