"""Le premier administrateur de la plateforme : `python -m courtage.amorcer +237690000000 "Prénom Nom"`.

Une plateforme neuve n'a personne pour ouvrir le premier dossier : cette
commande inscrit (ou promeut) UNE personne administratrice, par son numéro de
téléphone, avec le rôle propriétaire (`COURTAGE_URL_PROPRIETAIRE`). Elle se
connecte ensuite par code, comme tout le monde, et ouvre les dossiers clients
depuis l'interface. À lancer une fois, depuis le shell de l'hébergeur.
"""
import os
import sys

from sqlalchemy import create_engine, text

from courtage.auth.telephone import normaliser
from courtage.deploiement import _psycopg


def amorcer(url_proprietaire: str, telephone: str, nom: str) -> tuple[str, bool]:
    """Inscrit ou promeut ; rend (identifiant, créée ?)."""
    numero = normaliser(telephone)
    with create_engine(_psycopg(url_proprietaire)).begin() as c:
        existant = c.execute(text("SELECT id FROM utilisateurs WHERE telephone = :t"), {"t": numero}).scalar()
        if existant:
            c.execute(text("UPDATE utilisateurs SET admin_plateforme = true WHERE id = :i"), {"i": existant})
            c.execute(text("INSERT INTO journal (action, cible, details) VALUES ('plateforme.admin_promu', :i, '{}')"),
                      {"i": str(existant)})
            return str(existant), False
        nouvel = c.execute(text("INSERT INTO utilisateurs (telephone, nom_affiche, admin_plateforme) "
                                "VALUES (:t, :n, true) RETURNING id"), {"t": numero, "n": nom}).scalar_one()
        c.execute(text("INSERT INTO journal (action, cible, details) VALUES ('plateforme.admin_cree', :i, '{}')"),
                  {"i": str(nouvel)})
        return str(nouvel), True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit('Usage : python -m courtage.amorcer +237690000000 "Prénom Nom"')
    identifiant, cree = amorcer(os.environ["COURTAGE_URL_PROPRIETAIRE"], sys.argv[1], sys.argv[2])
    print(f"[amorcer] {'administrateur créé' if cree else 'administrateur promu'} : {identifiant}")
