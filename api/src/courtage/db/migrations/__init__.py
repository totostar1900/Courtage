"""Migrations Alembic, écrites à la main (voir versions/).

Elles s'exécutent avec le rôle PROPRIÉTAIRE, jamais avec `courtage_app` : un
rôle qui crée une table en devient propriétaire, et un propriétaire contourne
la RLS.
"""
from pathlib import Path

from functools import cache

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


def _config(url: str | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent))
    if url:
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def migrer(url: str, cible: str = "head") -> None:
    command.upgrade(_config(url), cible)


@cache
def revision_attendue() -> str:
    """La dernière migration que ce code connaît : celle que la base doit porter."""
    return ScriptDirectory.from_config(_config()).get_current_head()
