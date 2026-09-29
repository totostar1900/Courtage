"""La mesure d'audience, respectueuse de la vie privée : combien de visiteurs, d'où, et jusqu'où ils vont.

Un compteur par jour, par événement et par source (`mesures`) : ni témoin, ni identifiant, ni adresse IP, ni tiers.
La page envoie les événements publics (et rien si le navigateur demande à ne pas être suivi) ; le serveur compte
lui-même l'inscription faite et le mandat signé. La source est une catégorie du référent, jamais l'adresse.

Spécification : docs/specs/2026-09-29-contenu-mesure-portefeuille-whatsapp-design.md §2.
"""
from datetime import date, timedelta
from urllib.parse import urlparse

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from courtage.db import Mesure
from courtage.erreurs import ErreurMetier
from courtage.langue import t

EVENEMENTS_PAGE = ("vitrine", "contenu_ifc", "contenu_cameroun", "essai_ouvert", "essai_calcule", "inscription_ouverte")
EVENEMENTS_SERVEUR = ("inscription_faite", "mandat_signe")
# L'entonnoir, dans l'ordre du parcours.
ENTONNOIR = ("vitrine", "essai_ouvert", "essai_calcule", "inscription_ouverte", "inscription_faite", "mandat_signe")
SOURCES = ("direct", "recherche", "reseau_social", "autre")
_RECHERCHE = ("google.", "bing.", "duckduckgo.", "yahoo.", "qwant.", "ecosia.", "yandex.", "baidu.")
_SOCIAL = ("facebook.", "fb.", "linkedin.", "lnkd.in", "t.co", "twitter.", "x.com", "whatsapp.", "wa.me", "instagram.",
           "tiktok.", "youtube.")


def source(referent: str | None, notre_hote: str | None) -> str:
    hote = (urlparse(referent or "").hostname or "").lower()
    if not hote or (notre_hote and hote == notre_hote.lower()):
        return "direct"
    if any(m in hote for m in _RECHERCHE):
        return "recherche"
    if any(hote == m or hote.startswith(m) or f".{m}" in f".{hote}" for m in _SOCIAL):
        return "reseau_social"
    return "autre"


def compter(session: Session, evenement: str, source_: str = "direct", jour: date | None = None) -> None:
    if evenement not in EVENEMENTS_PAGE + EVENEMENTS_SERVEUR or source_ not in SOURCES:
        raise ErreurMetier("mesure_inconnue", t("Événement de mesure inconnu.", "Unknown measurement event."), 422)
    session.execute(text(
        "INSERT INTO mesures (jour, evenement, source, n) VALUES (:j, :e, :s, 1) "
        "ON CONFLICT (jour, evenement, source) DO UPDATE SET n = mesures.n + 1"),
        {"j": jour or date.today(), "e": evenement, "s": source_})


def tableau(session: Session, aujourd_hui: date, jours: int = 30) -> dict:
    depuis = aujourd_hui - timedelta(days=jours - 1)
    lignes = session.execute(select(Mesure.evenement, Mesure.source, func.sum(Mesure.n))
                             .where(Mesure.jour >= depuis).group_by(Mesure.evenement, Mesure.source)).all()
    total = {e: 0 for e in EVENEMENTS_PAGE + EVENEMENTS_SERVEUR}
    par_source = {s: 0 for s in SOURCES}
    for e, s, n in lignes:
        total[e] += n
        if e == "vitrine":
            par_source[s] += n
    etapes, precedent = [], None
    for e in ENTONNOIR:
        etapes.append({"evenement": e, "n": total[e],
                       "taux": round(total[e] / precedent, 3) if precedent else None})
        precedent = total[e] or None
    return {"depuis": depuis.isoformat(), "jusqu_au": aujourd_hui.isoformat(), "entonnoir": etapes,
            "contenus": {"contenu_ifc": total["contenu_ifc"], "contenu_cameroun": total["contenu_cameroun"]},
            "sources_vitrine": par_source}
