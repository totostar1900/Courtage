"""Erreurs métier : un code stable (snake_case), un message pour l'utilisateur, un statut HTTP."""
from courtage.langue import t


class ErreurMetier(Exception):
    def __init__(self, code: str, message: str, statut: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.statut = statut
        self.details = details or {}


# Le nom de ce qui manque, en anglais pour l'écran (le français reste la clé et le message par défaut).
_QUOI_EN = {
    "Barème": "Scale", "Cahier des charges": "Tender specifications", "Contrat": "Contract", "Document": "Document",
    "Dossier": "File", "Étude": "Study", "Fiche": "Sheet", "Fichier": "File", "Inscription": "Sign-up",
    "Justificatif": "Supporting document", "Mandat": "Mandate", "Partage": "Share", "Pièce": "Document",
    "Prestation": "Benefit payment", "Régime": "Plan", "Version du régime": "Plan version",
    "Organisation": "Organisation", "Utilisateur": "User", "Réponse": "Response", "Note": "Note",
}


class Introuvable(ErreurMetier):
    def __init__(self, quoi: str):
        super().__init__("introuvable", t(f"{quoi} introuvable.", f"{_QUOI_EN.get(quoi, quoi)} not found."), 404)
