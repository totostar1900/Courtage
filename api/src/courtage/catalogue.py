"""Le catalogue anonyme des régimes : ce qui se voit, et sous quel nom. Module pur, sans base.

Un régime partagé ne se montre jamais seul : dans un GROUPE d'au moins `SEUIL` entreprises distinctes. Le
découpage descend CEMAC → pays → secteur → taille, et ne descend d'un niveau que si TOUS les sous-groupes non
vides atteignent le seuil ; sinon le groupe s'affiche en entier là où il est. Masquer la taille d'une seule
entrée désignerait sa case comme la petite : les groupes affichés forment une partition, sans soustraction
possible. Conception : docs/specs/2026-09-26-catalogue-anonyme-design.md.
"""
import unicodedata
from dataclasses import dataclass

SEUIL = 5
NIVEAUX = ("pays", "secteur", "taille")

SECTEURS = {
    "agriculture": "Agriculture et agro-industrie", "banque_assurance": "Banque et assurance", "btp": "BTP",
    "commerce": "Commerce et distribution", "energie_mines": "Énergie et mines", "industrie": "Industrie",
    "services": "Services", "telecoms": "Télécommunications", "transport": "Transport et logistique",
    "administration_ong": "Administration et ONG", "autre": "Autre",
}
TAILLES = {"moins_de_50": "moins de 50 salariés", "50_a_250": "50 à 250 salariés",
           "plus_de_250": "plus de 250 salariés"}

# Les noms de catégories que toutes les entreprises emploient : ils ne désignent personne.
_COURANTES = {"*", "cadre", "cadres", "non cadre", "non cadres", "non-cadre", "non-cadres", "employe", "employes",
              "ouvrier", "ouvriers", "agent de maitrise", "agents de maitrise", "maitrise", "technicien",
              "techniciens", "direction", "dirigeant", "dirigeants", "agent", "agents", "personnel",
              "tous", "ensemble du personnel", "autres"}


@dataclass(frozen=True)
class Partage:
    id: str
    empreinte: str          # l'entreprise, sans son nom : compter les entreprises distinctes
    pays: str
    secteur: str
    taille: str
    convention_code: str
    categories: list


def _distinctes(partages: list[Partage]) -> int:
    return len({p.empreinte for p in partages})


def groupes_visibles(partages: list[Partage], seuil: int = SEUIL) -> list[tuple[dict, list[Partage]]]:
    """Les groupes que le catalogue montre : (attributs visibles, membres), chacun d'au moins `seuil`
    entreprises distinctes ; rien sous le seuil en tout."""
    if _distinctes(partages) < seuil:
        return []

    def descendre(membres: list[Partage], attributs: dict, profondeur: int) -> list[tuple[dict, list[Partage]]]:
        if profondeur == len(NIVEAUX):
            return [(attributs, membres)]
        cle = NIVEAUX[profondeur]
        sous: dict[str, list[Partage]] = {}
        for p in membres:
            sous.setdefault(getattr(p, cle), []).append(p)
        if any(_distinctes(g) < seuil for g in sous.values()):
            return [(attributs, membres)]
        return [g for valeur in sorted(sous) for g in descendre(sous[valeur], {**attributs, cle: valeur}, profondeur + 1)]

    return descendre(partages, {}, 0)


def _cle(nom: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return " ".join(sans_accents.lower().split())


def anonymiser_categories(categories: list[dict]) -> list[dict]:
    """Un nom courant reste ; un nom inhabituel (« Pilotes ») devient « Catégorie A », « B »… dans l'ordre."""
    lettres = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return [c if _cle(c["categorie"]) in _COURANTES else {**c, "categorie": f"Catégorie {next(lettres)}"}
            for c in categories]
