"""La langue de la réponse : le français d'abord, l'anglais à la demande de l'écran (en-tête `X-Langue: en`).

`t("français", "English")` s'écrit là où le texte naît, comme côté web. RÈGLE : seul ce qui va à l'écran se traduit.
Ce qui s'enregistre, se scelle, s'empreinte ou se journalise reste en français (un mandat, une étude émise, le
journal) : sinon l'empreinte d'un document dépendrait de la langue de celui qui l'a calculé. Pour ces textes-là,
`traduire(code, message)` rend l'anglais au moment de l'affichage, à partir du message français enregistré.
"""
import re
from contextvars import ContextVar

_langue: ContextVar[str] = ContextVar("langue", default="fr")


def langue() -> str:
    return _langue.get()


def definir(valeur: str | None):
    return _langue.set("en" if (valeur or "").lower().startswith("en") else "fr")


def t(fr: str, en: str) -> str:
    return en if _langue.get() == "en" else fr


# Messages enregistrés en français (anomalies d'un fichier, d'une étude) : leur traduction à l'affichage, par code.
# Chaque entrée : (motif du message français, gabarit anglais qui reprend les groupes nommés).
TRADUCTIONS: dict[str, list[tuple[str, str]]] = {}


def traduire(code: str | None, message: str) -> str:
    if _langue.get() != "en" or not message:
        return message
    for motif, gabarit in TRADUCTIONS.get(code or "", []):
        m = re.fullmatch(motif, message, flags=re.S)
        if m:
            return gabarit.format(**m.groupdict())
    return message


class MiddlewareLangue:
    """ASGI pur : la langue est posée avant l'appel, dans le contexte de la requête."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        valeur = next((v.decode() for k, v in scope.get("headers", []) if k == b"x-langue"), None)
        jeton = definir(valeur)
        try:
            await self.app(scope, receive, send)
        finally:
            _langue.reset(jeton)
