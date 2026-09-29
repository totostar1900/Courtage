"""Ce que tout visiteur peut lire, sans session : l'identité du cabinet et la version des conditions."""
from fastapi import APIRouter

from courtage import cabinet

routeur_public = APIRouter()


@routeur_public.get("/public/cabinet")
def lire_cabinet():
    return cabinet.identite()
