"""`GET /api/v1/sante` : la base répond-elle, et porte-t-elle le schéma que ce code attend ?

« Migrations appliquées » dans un journal de démarrage n'est pas une preuve :
la preuve est la révision lue DANS la base, comparée à la dernière que ce code
connaît. Un écart répond 503, et l'hébergeur ne bascule pas le trafic.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from courtage.db.migrations import revision_attendue

routeur_sante = APIRouter()


@routeur_sante.get("/sante")
def sante(request: Request):
    attendue = revision_attendue()
    try:
        with request.app.state.moteur.connect() as c:
            en_base = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception as e:                                   # noqa: BLE001 — la sonde dit ce qui manque
        return JSONResponse({"statut": "base_injoignable", "erreur": type(e).__name__}, status_code=503)
    corps = {"statut": "ok" if en_base == attendue else "schema_en_retard",
             "migration": en_base, "attendue": attendue, "version": request.app.version}
    return JSONResponse(corps, status_code=200 if en_base == attendue else 503)
