"""Environnement Alembic : l'URL vient de la configuration passée par `migrer()`."""
from alembic import context
from sqlalchemy import create_engine

url = context.config.get_main_option("sqlalchemy.url")
moteur = create_engine(url)
with moteur.connect() as connexion:
    context.configure(connection=connexion, transaction_per_migration=True)
    with context.begin_transaction():
        context.run_migrations()
moteur.dispose()
