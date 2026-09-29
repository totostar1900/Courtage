"""En-têtes de sécurité, erreur inattendue numérotée, alerte limitée ; vérification d'une sauvegarde."""
import os

from fastapi.testclient import TestClient

from courtage.api import securite
from tests.outils import V1


def test_chaque_reponse_porte_les_entetes_de_securite(client):
    r = client.get(f"{V1}/public/cabinet")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "strict-transport-security" not in r.headers           # HTTPS obligatoire en production seulement
    # Une erreur métier aussi.
    assert client.get(f"{V1}/moi").headers["x-frame-options"] == "DENY"


def test_une_erreur_inattendue_repond_500_avec_un_numero_sans_detail_interne(client, monkeypatch):
    envoyees = []
    client.app.state.alerte = securite.Alerte("https://alerte.exemple", intervalle=60)
    monkeypatch.setattr(client.app.state.alerte, "_poster", envoyees.append)

    def panne():
        raise RuntimeError("mot de passe=secret dans le message")
    client.app.add_api_route(f"{V1}/test/panne", panne)
    sans_relance = TestClient(client.app, raise_server_exceptions=False)
    for _ in range(2):
        r = sans_relance.get(f"{V1}/test/panne")
        assert r.status_code == 500 and r.json()["code"] == "erreur_interne"
        assert r.json()["details"]["incident"] in r.json()["message"]
        assert "secret" not in r.text
    import time
    time.sleep(0.05)
    assert len(envoyees) == 1                                    # au plus une alerte par minute
    assert envoyees[0]["erreur"] == "RuntimeError" and "secret" not in str(envoyees[0])


def test_sans_url_d_alerte_rien_ne_part():
    assert securite.Alerte(None).lancer({"incident": "X", "route": "/", "erreur": "E"}) is False


def test_la_verification_d_une_sauvegarde_lit_les_controles_et_les_comptes(bases, azito):
    from courtage.sauvegarde import verifier
    controles, comptes, dernier = verifier(os.environ["TEST_DATABASE_URL"])
    assert all(c.ok for c in controles), [str(c) for c in controles if not c.ok]
    assert comptes["organisations"] >= 1 and comptes["journal"] >= 1 and dernier
