"""Ce que tout visiteur peut lire, sans session : l'identité du cabinet et la version des conditions."""
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response

from courtage import cabinet

routeur_public = APIRouter()
routeur_racine = APIRouter()   # à la racine du site, hors /api/v1 : ce que lisent les moteurs de recherche

# Les pages qui s'indexent ; les dossiers, le profil, les liens d'assureurs et l'API, non.
PAGES_PUBLIQUES = ("/", "/essai", "/inscription", "/guide", "/verifier", "/mentions-legales", "/conditions",
                   "/confidentialite")
NON_INDEXEES = ("/api/", "/dossier/", "/profil", "/offre/", "/connexion")


@routeur_public.get("/public/cabinet")
def lire_cabinet():
    return cabinet.identite()


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
