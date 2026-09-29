"""Le cabinet de courtage qui exploite la plateforme : son identité, par la configuration, jamais inventée.

Une valeur absente se lit entre crochets, comme sur le mandat : la vitrine et les pages légales disent ce qui
manque plutôt que de le supposer.

COURTAGE_COURTIER_NOM, _AGREMENT, _ADRESSE (déjà sur le mandat), _RCCM, _COURRIEL, _TELEPHONE.
"""
import os

# La version des conditions d'utilisation et de la politique de confidentialité. Changer le texte (web/src/pages/
# Legal.tsx), c'est changer cette version : l'inscription enregistre celle que la personne a acceptée.
CONDITIONS_VERSION = "conditions-2026-09-29"   # + les demandes de rappel (confidentialité)

_CHAMPS = {
    "nom": ("COURTAGE_COURTIER_NOM", "[raison sociale du cabinet]"),
    "agrement": ("COURTAGE_COURTIER_AGREMENT", "[numéro d'agrément]"),
    "adresse": ("COURTAGE_COURTIER_ADRESSE", "[adresse du siège]"),
    "rccm": ("COURTAGE_COURTIER_RCCM", "[numéro RCCM du cabinet]"),
    "courriel": ("COURTAGE_COURTIER_COURRIEL", "[adresse de contact]"),
    "telephone": ("COURTAGE_COURTIER_TELEPHONE", "[téléphone]"),
}


def identite() -> dict:
    """Chaque champ, et `manquants` : ceux que la configuration ne donne pas encore."""
    d, manquants = {}, []
    for cle, (variable, defaut) in _CHAMPS.items():
        valeur = (os.environ.get(variable) or "").strip()
        d[cle] = valeur or defaut
        if not valeur:
            manquants.append(cle)
    return {**d, "manquants": manquants, "hebergeur": "Render Services, Inc. (render.com)",
            "conditions_version": CONDITIONS_VERSION}
