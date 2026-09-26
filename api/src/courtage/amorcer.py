"""Le premier administrateur de la plateforme : `python -m courtage.amorcer +237690000000 "Prénom Nom"`.

Une plateforme neuve n'a personne pour ouvrir le premier dossier : cette
commande inscrit (ou promeut) UNE personne administratrice, par son numéro de
téléphone, avec le rôle propriétaire (`COURTAGE_URL_PROPRIETAIRE`). Elle se
connecte ensuite par code, comme tout le monde, et ouvre les dossiers clients
depuis l'interface. À lancer une fois, depuis le shell de l'hébergeur.

Sans shell (l'offre gratuite de Render n'en a pas, et sa base est fermée à
Internet), `COURTAGE_ADMIN_TELEPHONE` et `COURTAGE_ADMIN_NOM` déclarent la même
personne et le démarrage la crée (`--depuis-env`, dans demarrer.sh). Une
personne déjà administratrice n'est pas touchée : un redémarrage n'écrit rien.
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


def depuis_environnement(env) -> str | None:
    """L'administrateur déclaré par l'environnement ; None si rien n'est déclaré."""
    telephone = (env.get("COURTAGE_ADMIN_TELEPHONE") or "").strip()
    if not telephone:
        return None
    url = env["COURTAGE_URL_PROPRIETAIRE"]
    with create_engine(_psycopg(url)).connect() as c:
        deja = c.execute(text("SELECT id FROM utilisateurs WHERE telephone = :t AND admin_plateforme"),
                         {"t": normaliser(telephone)}).scalar()
    if deja:
        return f"administrateur déjà en place : {deja}"
    identifiant, cree = amorcer(url, telephone, (env.get("COURTAGE_ADMIN_NOM") or "Administrateur").strip())
    return f"administrateur {'créé' if cree else 'promu'} : {identifiant}"


if __name__ == "__main__":
    if sys.argv[1:] == ["--depuis-env"]:
        message = depuis_environnement(os.environ)
        if message:
            print(f"[amorcer] {message}")
        sys.exit(0)
    if len(sys.argv) != 3:
        sys.exit('Usage : python -m courtage.amorcer +237690000000 "Prénom Nom"')
    identifiant, cree = amorcer(os.environ["COURTAGE_URL_PROPRIETAIRE"], sys.argv[1], sys.argv[2])
    print(f"[amorcer] {'administrateur créé' if cree else 'administrateur promu'} : {identifiant}")
