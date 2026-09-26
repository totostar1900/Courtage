"""L'interface construite, servie par l'API : une image, une origine.

`/assets/*` porte un nom qui change avec le contenu : il se garde un an. Tout
autre chemin hors `/api` rend `index.html`, que le routeur de la page
interprète (`/etudes/…`, `/verifier/RL-…`) ; il ne se garde pas, pour qu'une
nouvelle version soit vue au prochain chargement. Un chemin `/api` inconnu
reste un 404 JSON, jamais une page.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

GARDER_UN_AN = "public, max-age=31536000, immutable"
NE_PAS_GARDER = "no-cache"


def servir_interface(app: FastAPI, dossier: Path) -> None:
    dossier = dossier.resolve()
    index = dossier / "index.html"
    if not index.is_file():
        raise RuntimeError(f"Interface introuvable : {index} (construire web/ avec `npm run build`).")

    @app.get("/{chemin:path}", include_in_schema=False)
    def page(chemin: str, request: Request):
        if chemin == "api" or chemin.startswith("api/"):
            return JSONResponse({"code": "introuvable", "message": "Route inconnue.", "details": {}}, status_code=404)
        fichier = (dossier / chemin).resolve()
        if chemin and fichier.is_file() and fichier.is_relative_to(dossier):
            cache = GARDER_UN_AN if chemin.startswith("assets/") else NE_PAS_GARDER
            return FileResponse(fichier, headers={"Cache-Control": cache})
        return FileResponse(index, headers={"Cache-Control": NE_PAS_GARDER})
