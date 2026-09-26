"""Point d'entrée du serveur : `uvicorn courtage.principal:app`.

DATABASE_URL            connexion avec le rôle APPLICATIF (courtage_app), jamais le propriétaire
COURTAGE_AUTH           `session` (défaut : connexion par code reçu au téléphone) ;
                        `entete_dev` en développement seulement (refusé si COURTAGE_ENV=production)
COURTAGE_CLE_AUTH       clé des codes de connexion ; obligatoire en production
TWILIO_COMPTE, TWILIO_JETON, TWILIO_EMETTEUR, TWILIO_CANAL (sms | whatsapp)
                        l'envoi des codes ; sans eux, les codes sont écrits dans le journal (développement)
COURTAGE_CLE_SCEAU      clé secrète des sceaux ; obligatoire en production, sinon les rapports sont « non probants »
COURTAGE_URL_PUBLIQUE   adresse publique, imprimée sur les rapports pour la vérification
"""
import os

from sqlalchemy import create_engine

from courtage.api import creer_app
from courtage.messagerie import expediteur_depuis_environnement


def _octets(nom: str) -> bytes | None:
    valeur = os.environ.get(nom)
    return valeur.encode("utf-8") if valeur else None


app = creer_app(create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True),
                authentification=os.environ.get("COURTAGE_AUTH", "session"),
                cle_sceau=_octets("COURTAGE_CLE_SCEAU"),
                url_publique=os.environ.get("COURTAGE_URL_PUBLIQUE"),
                expediteur=expediteur_depuis_environnement(os.environ),
                cle_auth=_octets("COURTAGE_CLE_AUTH"))
