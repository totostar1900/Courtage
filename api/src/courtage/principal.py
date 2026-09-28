"""Point d'entrée du serveur : `uvicorn courtage.principal:app`.

DATABASE_URL            connexion avec le rôle APPLICATIF (courtage_app), jamais le propriétaire ; à défaut,
                        dérivée de COURTAGE_URL_PROPRIETAIRE et COURTAGE_MOT_DE_PASSE_APP
COURTAGE_AUTH           `session` (défaut : connexion par code reçu au téléphone) ;
                        `entete_dev` en développement seulement (refusé si COURTAGE_ENV=production)
COURTAGE_CLE_AUTH       clé des codes de connexion ; obligatoire en production
TWILIO_COMPTE, TWILIO_JETON, TWILIO_EMETTEUR, TWILIO_CANAL (sms | whatsapp)
                        l'envoi des codes ; sans eux, les codes sont écrits dans le journal (développement)
COURTAGE_CLE_SCEAU      clé secrète des sceaux ; obligatoire en production, sinon les rapports sont « non probants »
COURTAGE_URL_PUBLIQUE   adresse publique, imprimée sur les rapports pour la vérification ; à défaut,
                        RENDER_EXTERNAL_URL (fournie par Render)
COURTAGE_WEB            dossier de l'interface construite (web/dist) ; l'image le fixe à /app/web
COURTAGE_ENV            `production` | `recette` (cookie sécurisé ; en recette les codes vont au journal)
COURTAGE_EXTRACTION     `regles` (défaut, aucun appel externe) | `claude` (Anthropic ; ANTHROPIC_API_KEY requis)
"""
import os

from sqlalchemy import create_engine

from courtage.api import creer_app
from courtage.deploiement import url_applicative
from courtage.messagerie import courriel_depuis_environnement, expediteur_depuis_environnement


def _octets(nom: str) -> bytes | None:
    valeur = os.environ.get(nom)
    return valeur.encode("utf-8") if valeur else None


def _extracteur():
    if os.environ.get("COURTAGE_EXTRACTION", "regles") == "claude":
        from courtage.extraction.claude import ExtracteurClaude
        return ExtracteurClaude()
    return None


app = creer_app(create_engine(url_applicative(os.environ), pool_pre_ping=True),
                authentification=os.environ.get("COURTAGE_AUTH", "session"),
                cle_sceau=_octets("COURTAGE_CLE_SCEAU"),
                url_publique=os.environ.get("COURTAGE_URL_PUBLIQUE") or os.environ.get("RENDER_EXTERNAL_URL"),
                expediteur=expediteur_depuis_environnement(os.environ),
                courriel=courriel_depuis_environnement(os.environ),
                cle_auth=_octets("COURTAGE_CLE_AUTH"),
                dossier_web=os.environ.get("COURTAGE_WEB") or None,
                extracteur=_extracteur())
