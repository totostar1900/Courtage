"""Une sauvegarde ne se prouve qu'en la restaurant : lire, dans une copie restaurée, ce que la production doit porter.

    python -m courtage.sauvegarde <url du propriétaire de la base restaurée>

Imprime les contrôles du démarrage (schéma, RLS, déclencheurs…), le nombre de lignes des tables qui comptent et la
date du dernier acte au journal — à comparer avec la production le jour de la copie. Sort en erreur si un contrôle
échoue ou si la base est vide. `deploiement/verifier_sauvegarde.sh` fait la copie, la restauration et cet appel.
"""
import sys

from sqlalchemy import create_engine, text

from courtage.deploiement import Controle, _psycopg, controler

TABLES = ("organisations", "utilisateurs", "etudes", "documents", "sceaux", "mandats_courtage", "prestations",
          "journal")


def verifier(url_proprio: str) -> tuple[list[Controle], dict[str, int], str | None]:
    moteur = create_engine(_psycopg(url_proprio))
    try:
        # « peut se connecter » dépend du rôle dans le cluster de restauration, pas de la sauvegarde.
        controles = [c for c in controler(moteur) if "peut se connecter" not in c.nom]
        with moteur.connect() as c:
            comptes = {t: c.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in TABLES}
            dernier = c.execute(text("SELECT max(quand) FROM journal")).scalar()
        return controles, comptes, dernier.isoformat() if dernier else None
    finally:
        moteur.dispose()


if __name__ == "__main__":
    controles, comptes, dernier = verifier(sys.argv[1])
    for c in controles:
        print(f"[sauvegarde] {c}", flush=True)
    for t, n in comptes.items():
        print(f"[sauvegarde] {t:<18} {n:>8} ligne(s)")
    print(f"[sauvegarde] dernier acte au journal : {dernier or 'aucun'}")
    vide = comptes["organisations"] == 0 and comptes["journal"] == 0
    if vide:
        print("[sauvegarde] FAIL  la base restaurée est vide")
    sys.exit(0 if all(c.ok for c in controles) and not vide else 1)
