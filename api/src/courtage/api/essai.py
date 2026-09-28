"""L'essai sans compte : public, sans état. Voir services/essai.py."""
import json
from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from courtage.erreurs import ErreurMetier
from courtage.services import essai, regimes

from .limites import limite

routeur_essai = APIRouter()


class Categorie(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categorie: str = Field(min_length=1, max_length=60)
    convention_code: str
    bareme: dict
    anciennete_minimale: int = Field(default=0, ge=0, le=40)
    plafond_mois: float | None = Field(default=None, gt=0)


class Parametres(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pays: str = Field(pattern=r"^[A-Z]{2}$")
    date_evaluation: date
    fonds_disponible: int = Field(default=0, ge=0)
    convention_code: str
    categories: list[Categorie] | None = Field(default=None, max_length=6)


@routeur_essai.post("/essai/etude", dependencies=[Depends(limite("essai"))])
async def etude_d_essai(fichier: UploadFile = File(...), parametres: str = Form(...)):
    contenu = await fichier.read()
    if len(contenu) > 2 * 1024 * 1024:
        raise ErreurMetier("fichier_trop_lourd", "Un fichier de 2 Mo au plus pour l'essai.", 422)
    try:
        p = Parametres.model_validate(json.loads(parametres))
    except (ValueError, ValidationError):
        raise ErreurMetier("parametres_invalides", "Paramètres de l'essai invalides.", 422) from None
    categories = None if not p.categories else [
        regimes.SaisieCategorie(**c.model_dump()) for c in p.categories]
    return essai.evaluer_essai(contenu=contenu, nom_fichier=fichier.filename or "personnel.xlsx", pays=p.pays,
                               date_evaluation=p.date_evaluation, fonds_disponible=p.fonds_disponible,
                               convention_code=p.convention_code, categories=categories)
