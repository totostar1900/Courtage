"""Migrations Alembic, écrites à la main (voir versions/).

Elles s'exécutent avec le rôle PROPRIÉTAIRE, jamais avec `courtage_app` : un
rôle qui crée une table en devient propriétaire, et un propriétaire contourne
la RLS.
"""
from pathlib import Path

from alembic import command
from alembic.config import Config


def migrer(url: str, cible: str = "head") -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, cible)
