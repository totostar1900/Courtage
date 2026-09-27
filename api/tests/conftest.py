"""Base de test : une base PostgreSQL remise à zéro puis migrée une fois par session.

`TEST_DATABASE_URL` pointe sur la base de test avec un rôle PROPRIÉTAIRE (les
migrations s'y exécutent). Les tests applicatifs se connectent avec le rôle
`courtage_app`, qui n'est propriétaire de rien : c'est la condition pour que
les politiques RLS s'appliquent à lui. Sans `TEST_DATABASE_URL`, les tests de
base sont ignorés, pas échoués.
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from courtage.api import creer_app
from tests.outils import V1, deposer, en_tant_que, fichier_azito

MOT_DE_PASSE_APP = "app-test"


@pytest.fixture(scope="session")
def bases():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL non défini : tests de base ignorés")
    proprio = create_engine(url, future=True)
    with proprio.begin() as c:
        c.execute(text("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"))
        c.execute(text(f"""
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'courtage_app') THEN
                CREATE ROLE courtage_app LOGIN PASSWORD '{MOT_DE_PASSE_APP}';
              ELSE
                ALTER ROLE courtage_app LOGIN PASSWORD '{MOT_DE_PASSE_APP}';
              END IF;
            END $$;"""))

    from courtage.db.migrations import migrer
    migrer(url)

    url_app = make_url(url).set(username="courtage_app", password=MOT_DE_PASSE_APP)
    app = create_engine(url_app, future=True)
    yield proprio, app
    app.dispose()
    proprio.dispose()


# --- Fixtures de l'API --------------------------------------------------------

@pytest.fixture
def client(bases):
    return TestClient(creer_app(moteur=bases[1], authentification="entete_dev"))


@pytest.fixture
def personnes(bases):
    """Un administrateur de plateforme, un conseiller, une DRH, et un étranger au dossier."""
    ids = {}
    with bases[0].begin() as c:
        for nom, admin in (("admin", True), ("conseiller", False), ("drh", False), ("etranger", False)):
            ids[nom] = c.execute(text("INSERT INTO utilisateurs (email, admin_plateforme, nom_affiche) "
                                      "VALUES (:e, :a, :n) RETURNING id"),
                                 {"e": f"{nom}-{uuid.uuid4().hex[:8]}@exemple.cm", "a": admin,
                                  "n": nom.capitalize()}).scalar_one()
    return ids


@pytest.fixture
def azito(client, personnes):
    """Le client AZITO, son conseiller, sa DRH, ses conditions et son fichier déposé."""
    r = client.post(f"{V1}/organisations", json={"nom": "AZITO", "pays": "CI"}, headers=en_tant_que(personnes["admin"]))
    assert r.status_code == 201, r.text
    org = r.json()["id"]
    for qui, role in (("conseiller", "conseiller"), ("drh", "admin_client")):
        r = client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": str(personnes[qui]), "role": role},
                        headers=en_tant_que(personnes["admin"]))
        assert r.status_code == 201, r.text
    fichier = deposer(client, org, personnes["drh"], fichier_azito())
    return {"org": org, "fichier": fichier["id"], **personnes}
