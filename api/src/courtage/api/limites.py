"""Une limite de fréquence par adresse, en mémoire, pour les routes publiques.

La vérification d'un document est ouverte à tous (c'est son rôle) : sans limite,
un robot énumérerait les numéros `RL-…` pour savoir quels clients existent et
quand ils ont émis. La demande de code aussi : la limite par numéro
(`courtage.auth`) ne voit pas un robot qui essaie mille numéros.

En mémoire, donc par processus : une seule instance de l'API aujourd'hui. Le
jour où il y en a plusieurs, la limite se multiplie par leur nombre ; elle
reste une limite. L'adresse est celle du client derrière le proxy
(`uvicorn --proxy-headers`), pas celle du proxy.
"""
import threading
import time
from collections import deque

from fastapi import Request

from courtage.erreurs import ErreurMetier
from courtage.langue import t


class Limiteur:
    def __init__(self, nombre: int, fenetre_s: float, horloge=time.monotonic):
        self.nombre, self.fenetre, self.horloge = nombre, fenetre_s, horloge
        self._traces: dict[str, deque] = {}
        self._verrou = threading.Lock()

    def admettre(self, cle: str) -> bool:
        maintenant = self.horloge()
        with self._verrou:
            if len(self._traces) > 10_000:          # une mémoire bornée : on oublie les adresses calmes
                self._traces = {k: v for k, v in self._traces.items() if v and v[-1] > maintenant - self.fenetre}
            trace = self._traces.setdefault(cle, deque())
            while trace and trace[0] <= maintenant - self.fenetre:
                trace.popleft()
            if len(trace) >= self.nombre:
                return False
            trace.append(maintenant)
            return True


def limite(nom: str):
    """Dépendance FastAPI : refuse (429) au-delà de la limite `nom` de l'application, par adresse."""
    def dependance(request: Request) -> None:
        limiteur: Limiteur = request.app.state.limites[nom]
        adresse = request.client.host if request.client else "inconnue"
        if not limiteur.admettre(adresse):
            raise ErreurMetier("trop_de_requetes", t("Trop de requêtes depuis cette adresse : réessayez dans une minute.",
                                 "Too many requests from this address: try again in a minute."),
                               429)
    return dependance
