"""Ce que tout visiteur peut lire, sans session : l'identité du cabinet et la version des conditions."""
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from courtage import cabinet
from courtage.db import Utilisateur
from courtage.langue import t
from courtage.services import demandes_rappel, mesure

from . import session_db
from .inscription import _plateforme
from .limites import limite

routeur_public = APIRouter()
routeur_racine = APIRouter()   # à la racine du site, hors /api/v1 : ce que lisent les moteurs de recherche

# Les pages qui s'indexent ; les dossiers, le profil, les liens d'assureurs et l'API, non.
PAGES_PUBLIQUES = ("/", "/ifc", "/ifc/cameroun", "/essai", "/inscription", "/guide", "/verifier", "/mentions-legales",
                   "/conditions", "/confidentialite")
NON_INDEXEES = ("/api/", "/dossier/", "/profil", "/offre/", "/connexion")


@routeur_public.get("/public/cabinet")
def lire_cabinet():
    return cabinet.identite()


@routeur_public.get("/public/besoins")
def lire_besoins():
    """Ce qu'une entreprise peut attendre de l'accompagnement : les cases de l'inscription et de la page Accompagnement."""
    from courtage.services import mandats
    return {"besoins": [{"code": c, "libelle": l} for c, l in mandats._libelles(mandats.BESOINS, mandats.BESOINS_EN).items()]}


def _base(request: Request) -> str:
    return (request.app.state.sceau.url_publique or str(request.base_url)).rstrip("/")


@routeur_racine.get("/robots.txt", include_in_schema=False)
def robots(request: Request):
    lignes = ["User-agent: *", *[f"Disallow: {c}" for c in NON_INDEXEES], "Allow: /", "",
              f"Sitemap: {_base(request)}/sitemap.xml", ""]
    return PlainTextResponse("\n".join(lignes))


@routeur_racine.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request):
    base = _base(request)
    urls = "".join(f"<url><loc>{base}{p}</loc></url>" for p in PAGES_PUBLIQUES)
    return Response('<?xml version="1.0" encoding="UTF-8"?>'
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                    media_type="application/xml")


# --- Être rappelé ---------------------------------------------------------------------------------

class DemandeRappel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nom: str = Field(min_length=1, max_length=120)
    entreprise: str = Field(min_length=1, max_length=200)
    telephone: str = Field(min_length=3, max_length=30)
    courriel: str | None = Field(default=None, max_length=200)
    creneau: str = Field(max_length=20)
    message: str | None = Field(default=None, max_length=1000)
    accord: bool = False
    site_web: str | None = Field(default=None, max_length=200)   # le champ piège : invisible pour une personne


class Traitement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statut: str = Field(max_length=20)
    note: str | None = Field(default=None, max_length=1000)


@routeur_public.post("/public/rappel", status_code=201, dependencies=[Depends(limite("rappel"))])
def demander_rappel(corps: DemandeRappel, session: Session = Depends(session_db, scope="function")):
    d = corps.model_dump()
    demandes_rappel.deposer(session, piege=d.pop("site_web"), **d)
    return {"message": t("Merci : le courtier vous rappelle au créneau choisi.",
                          "Thank you: the broker will call you back in the chosen time slot.")}


@routeur_public.get("/rappels")
def lire_rappels(session: Session = Depends(session_db, scope="function"), _: Utilisateur = Depends(_plateforme)):
    return demandes_rappel.lister(session)


@routeur_public.put("/rappels/{demande_id}")
def traiter_rappel(demande_id: uuid.UUID, corps: Traitement, session: Session = Depends(session_db, scope="function"),
                   moi: Utilisateur = Depends(_plateforme)):
    return demandes_rappel.en_clair(session, demandes_rappel.traiter(session, moi.id, demande_id, corps.statut, corps.note))


# --- La mesure d'audience (sans témoin, sans identifiant) ------------------------------------------

class Evenement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evenement: str = Field(max_length=40)
    referent: str | None = Field(default=None, max_length=500)


@routeur_public.post("/public/mesure", status_code=204, dependencies=[Depends(limite("mesure"))])
def mesurer(corps: Evenement, request: Request, session: Session = Depends(session_db, scope="function")):
    if corps.evenement not in mesure.EVENEMENTS_PAGE:           # la page ne compte pas ce que compte le serveur
        return Response(status_code=204)
    mesure.compter(session, corps.evenement, mesure.source(corps.referent, request.url.hostname))
    return Response(status_code=204)


@routeur_public.get("/mesures")
def lire_mesures(jours: int = 30, session: Session = Depends(session_db, scope="function"),
                 _: Utilisateur = Depends(_plateforme)):
    from datetime import date
    return mesure.tableau(session, date.today(), max(1, min(jours, 365)))
