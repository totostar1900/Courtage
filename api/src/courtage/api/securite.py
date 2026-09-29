"""Les en-têtes de sécurité de chaque réponse, et l'erreur inattendue qui répond sans rien dire de l'intérieur.

- CSP : tout vient de la plateforme (les polices aussi, `@fontsource`) ; aucun script tiers ni en ligne. Les styles
  en ligne restent permis (les attributs `style` de React). `frame-ancestors 'none'` : la plateforme ne s'affiche
  dans le cadre d'aucun autre site.
- HSTS en production seulement : en recette et en développement, le site peut être servi en HTTP.
- Une erreur inattendue répond 500 avec un numéro d'incident, que le journal du serveur porte aussi, avec la pile.
  Si `COURTAGE_ALERTE_URL` est posée, un POST JSON court part vers elle (au plus un par minute) : le numéro, la
  route, le type d'erreur — jamais le message, qui peut contenir des données.
"""
import logging
import os
import secrets
import threading
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from courtage.langue import t

journal = logging.getLogger("courtage.incidents")

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
       "font-src 'self'; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; "
       "form-action 'self'; frame-ancestors 'none'")
ENTETES = {
    "content-security-policy": CSP,
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "cross-origin-opener-policy": "same-origin",
}
HSTS = "max-age=31536000; includeSubDomains"


class EntetesSecurite:
    """Middleware ASGI : ajoute les en-têtes qu'une réponse ne pose pas elle-même."""

    def __init__(self, app, production: bool = False):
        self.app = app
        self.entetes = [(k.encode(), v.encode()) for k, v in (ENTETES | ({"strict-transport-security": HSTS}
                                                                          if production else {})).items()]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def envoyer(message):
            if message["type"] == "http.response.start":
                presents = {k.lower() for k, _ in message.get("headers", [])}
                message["headers"] = list(message.get("headers", [])) + [
                    (k, v) for k, v in self.entetes if k not in presents]
            await send(message)

        return await self.app(scope, receive, envoyer)


class Alerte:
    """Au plus une alerte par minute vers `COURTAGE_ALERTE_URL` ; un envoi qui échoue ne fait rien d'autre."""

    def __init__(self, url: str | None, intervalle: float = 60.0):
        self.url, self.intervalle, self.derniere = url, intervalle, 0.0
        self.verrou = threading.Lock()

    def lancer(self, corps: dict) -> bool:
        if not self.url:
            return False
        with self.verrou:
            maintenant = time.monotonic()
            if maintenant - self.derniere < self.intervalle:
                return False
            self.derniere = maintenant
        threading.Thread(target=self._poster, args=(corps,), daemon=True).start()
        return True

    def _poster(self, corps: dict) -> None:
        import httpx
        try:
            httpx.post(self.url, json={**corps, "text": f"[courtage] incident {corps['incident']} : "
                                                       f"{corps['erreur']} sur {corps['route']}"}, timeout=5)
        except Exception as e:                                    # noqa: BLE001
            journal.warning("[incident] alerte non envoyée : %s", type(e).__name__)


def installer(app, production: bool) -> None:
    app.add_middleware(EntetesSecurite, production=production)
    app.state.alerte = Alerte(os.environ.get("COURTAGE_ALERTE_URL"))

    @app.exception_handler(Exception)
    async def _inattendue(request: Request, e: Exception):
        numero = secrets.token_hex(4).upper()
        route = f"{request.method} {request.scope.get('route').path if request.scope.get('route') else request.url.path}"
        journal.error("[incident] %s — %s — %s", numero, route, type(e).__name__, exc_info=e)
        request.app.state.alerte.lancer({"incident": numero, "route": route, "erreur": type(e).__name__})
        return JSONResponse({"code": "erreur_interne",
                             "message": t(f"Une erreur inattendue s'est produite. Numéro d'incident : {numero}.",
                                          f"An unexpected error occurred. Incident number: {numero}."),
                             "details": {"incident": numero}}, status_code=500)
