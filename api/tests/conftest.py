"""Base de test : une base PostgreSQL remise à zéro puis migrée une fois par session.

`TEST_DATABASE_URL` pointe sur la base de test avec un rôle PROPRIÉTAIRE (les
migrations s'y exécutent). Les tests applicatifs se connectent avec le rôle
`courtage_app`, qui n'est propriétaire de rien : c'est la condition pour que
les politiques RLS s'appliquent à lui. Sans `TEST_DATABASE_URL`, les tests de
base sont ignorés, pas échoués.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

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
