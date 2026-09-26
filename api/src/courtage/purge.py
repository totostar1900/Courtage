"""L'effacement programmé des identités échues : `python -m courtage.purge` (une fois par jour).

Chaque lecture d'un dossier efface déjà ce qui est échu ; cette tâche garantit
l'effacement même pour un client qui ne se connecte plus. Rôle applicatif
(`DATABASE_URL`, ou dérivée de l'URL du propriétaire) : il ne peut supprimer que dans `beneficiaires` et
`pieces_dossier`, chaque organisation dans son propre contexte.
"""
import os
from datetime import date

from sqlalchemy import create_engine

from courtage.deploiement import url_applicative
from courtage.services.dossiers import effacer_echus_partout

if __name__ == "__main__":
    n = effacer_echus_partout(create_engine(url_applicative(os.environ)), date.today())
    print(f"[purge] {n} identité(s) effacée(s)", flush=True)
