"""Point d'entrée du serveur : `uvicorn courtage.principal:app`.

DATABASE_URL    connexion avec le rôle APPLICATIF (courtage_app), jamais le propriétaire
COURTAGE_AUTH   `aucune` (défaut, tout est refusé) tant que la tâche 8 n'a pas livré l'authentification ;
                `entete_dev` en développement uniquement (refusé si COURTAGE_ENV=production)
"""
import os

from sqlalchemy import create_engine

from courtage.api import creer_app

app = creer_app(create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True),
                authentification=os.environ.get("COURTAGE_AUTH", "aucune"))
