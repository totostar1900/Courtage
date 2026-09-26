"""Erreurs métier : un code stable (snake_case), un message pour l'utilisateur, un statut HTTP."""


class ErreurMetier(Exception):
    def __init__(self, code: str, message: str, statut: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.statut = statut
        self.details = details or {}


class Introuvable(ErreurMetier):
    def __init__(self, quoi: str):
        super().__init__("introuvable", f"{quoi} introuvable.", 404)
