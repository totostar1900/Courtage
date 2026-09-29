"""Ce qu'un testeur d'intrusion essaierait d'abord, écrit comme des tests (docs/securite/test-intrusion.md) :

- chaque route d'un dossier refuse une personne étrangère au dossier ;
- aucune route ne répond sans connexion, hors la liste publique déclarée ici ;
- chaque route publique qui écrit, ou qui devine (un numéro, un jeton), est limitée en fréquence ;
- chaque écriture par cookie exige l'en-tête anti-CSRF ;
- une route publique ne rend rien d'un dossier.

Les routes sont lues dans l'application elle-même : une route ajoutée demain entre dans ces tests sans qu'on y pense.
"""
import re
import uuid

import pytest
from sqlalchemy import create_engine

from courtage.api import creer_app
from courtage.api.limites import Limiteur
from tests.outils import V1, en_tant_que
from tests.test_auth import abonne, boite, se_connecter, web  # noqa: F401 — fixtures

_APP = creer_app(create_engine("postgresql+psycopg://nul@localhost/nul"), authentification="entete_dev")
ROUTES = sorted((m.upper(), p) for p, ops in _APP.openapi()["paths"].items() for m in ops)
ECRITURES = ("POST", "PUT", "PATCH", "DELETE")

# Ce qui répond sans connexion, et pourquoi. Tout le reste exige une session.
PUBLIQUES = {
    ("GET", "/api/v1/sante"),                           # la sonde de l'hébergeur
    ("GET", "/api/v1/referentiel/conventions"),         # le référentiel : public, daté, sourcé
    ("GET", "/api/v1/referentiel/modeles"),
    ("GET", "/api/v1/referentiel/hypotheses"),
    ("GET", "/api/v1/referentiel/canevas-personnel"),
    ("GET", "/api/v1/catalogue/regimes"),
    ("GET", "/api/v1/public/cabinet"),                  # l'identité du cabinet (mentions légales)
    ("POST", "/api/v1/public/rappel"),                  # la demande de rappel de la vitrine
    ("POST", "/api/v1/public/mesure"),                  # la mesure d'audience, sans témoin
    ("GET", "/api/v1/auth/mode"),
    ("POST", "/api/v1/auth/code"),                      # se connecter
    ("POST", "/api/v1/auth/verification"),
    ("POST", "/api/v1/inscription/code"),               # s'inscrire
    ("POST", "/api/v1/inscription/verification"),
    ("POST", "/api/v1/inscription"),
    ("POST", "/api/v1/essai/etude"),                    # l'essai sans compte
    ("GET", "/api/v1/extraction/mode"),
    ("GET", "/api/v1/offre/{jeton}"),                   # le lien d'un assureur : le jeton est l'accès
    ("GET", "/api/v1/offre/{jeton}/cahier"),
    ("POST", "/api/v1/offre/{jeton}"),
    ("GET", "/api/v1/verifier/{numero}"),               # la vérification d'un document scellé
    ("POST", "/api/v1/verifier/{numero}"),
}
# Parmi elles, celles qui écrivent ou qui devinent : chacune a sa limite par adresse.
LIMITEES = {r for r in PUBLIQUES if r[0] == "POST" or "{" in r[1]}


def _chemin(p: str, org: str) -> str:
    return re.sub(r"\{[^}]+\}", lambda m: org if m.group(0) == "{organisation_id}" else str(uuid.uuid4()), p)


def _appel(client, methode, chemin, **kw):
    return client.request(methode, chemin, json={} if methode in ECRITURES else None, **kw)


def test_la_liste_publique_est_a_jour():
    """Une route publique retirée du code doit sortir de la liste : sinon la liste ment."""
    assert PUBLIQUES <= set(ROUTES)


@pytest.mark.parametrize("methode,chemin", [r for r in ROUTES if "{organisation_id}" in r[1]])
def test_une_route_de_dossier_refuse_l_etranger(client, azito, methode, chemin):
    r = _appel(client, methode, _chemin(chemin, azito["org"]), headers=en_tant_que(azito["etranger"]))
    assert r.status_code in (403, 404), (r.status_code, r.text[:200])
    assert "AZITO" not in r.text


@pytest.mark.parametrize("methode,chemin", [r for r in ROUTES if r not in PUBLIQUES and not r[1].startswith("/api/v1/dev")])
def test_sans_connexion_rien_ne_repond(client, azito, methode, chemin):
    r = _appel(client, methode, _chemin(chemin, azito["org"]))
    assert r.status_code == 401, (r.status_code, r.text[:200])


@pytest.mark.parametrize("methode,chemin", sorted(LIMITEES))
def test_une_route_publique_qui_ecrit_ou_devine_est_limitee(client, methode, chemin):
    for nom in client.app.state.limites:
        client.app.state.limites[nom] = Limiteur(0, 60)       # tout est déjà épuisé
    r = _appel(client, methode, _chemin(chemin, str(uuid.uuid4())))
    assert r.status_code == 429, (r.status_code, r.text[:200])


def test_chaque_ecriture_par_cookie_exige_l_en_tete_anti_csrf(web, boite, abonne):  # noqa: F811
    se_connecter(web, boite, abonne["telephone"])
    ecritures = [r for r in ROUTES if r[0] in ECRITURES and r not in PUBLIQUES
                 and not r[1].startswith("/api/v1/dev") and r[1] != "/api/v1/auth/deconnexion"]
    assert len(ecritures) > 50
    for methode, chemin in ecritures:
        r = _appel(web, methode, _chemin(chemin, str(abonne["org"])))
        assert r.status_code == 403 and r.json()["code"] == "csrf", (methode, chemin, r.status_code)


def test_une_route_publique_ne_rend_rien_d_un_dossier(client, azito):
    lus = [client.get(f"{V1}{p}") for p in ("/sante", "/public/cabinet", "/referentiel/conventions", "/auth/mode",
                                              "/catalogue/regimes")]
    lus += [client.get("/robots.txt"), client.get("/sitemap.xml")]
    for r in lus:
        assert "AZITO" not in r.text and azito["org"] not in r.text
    # Un jeton ou un numéro deviné : la même réponse, qu'il existe quelque chose derrière ou non.
    a, b = client.get(f"{V1}/offre/{uuid.uuid4().hex}"), client.get(f"{V1}/offre/x")
    assert a.status_code == b.status_code == 404 and a.json()["code"] == b.json()["code"]
    v = client.get(f"{V1}/verifier/RI-0000-0000")
    assert v.status_code == 404 and "AZITO" not in v.text
