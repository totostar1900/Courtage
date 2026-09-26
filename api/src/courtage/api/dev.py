"""Routes de développement : montées SEULEMENT en mode `entete_dev` (jamais en production,
que `creer_app` refuse dans ce mode). Elles remplacent l'écran de connexion jusqu'à la tâche 8."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import Utilisateur

from . import session_db

routeur_dev = APIRouter()


@routeur_dev.get("/utilisateurs")
def utilisateurs(session: Session = Depends(session_db, scope="function")):
    return [{"id": str(u.id), "nom_affiche": u.nom_affiche, "email": u.email, "admin_plateforme": u.admin_plateforme}
            for u in session.scalars(select(Utilisateur).order_by(Utilisateur.cree_le.desc()).limit(50))]
