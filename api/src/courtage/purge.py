"""L'effacement programmé des identités échues et l'archivage des dossiers clôturés depuis 90 jours, et les rappels du
cycle annuel (au plus un par étape, état et année) :
`python -m courtage.purge` (une fois par jour, et à chaque démarrage) ; et les inscriptions jamais confirmées
depuis 30 jours.

Chaque lecture d'un dossier efface déjà ce qui est échu ; cette tâche garantit
l'effacement même pour un client qui ne se connecte plus. Rôle applicatif
(`DATABASE_URL`, ou dérivée de l'URL du propriétaire) : il ne peut supprimer que dans `beneficiaires` et
`pieces_dossier`, chaque organisation dans son propre contexte.
"""
import os
from datetime import date

from sqlalchemy import create_engine

from courtage.deploiement import url_applicative
from datetime import datetime, timezone

from courtage.messagerie import courriel_depuis_environnement, whatsapp_depuis_environnement
from courtage.services.activation import effacer_expirees_partout
from courtage.services.annuel import rappeler_partout
from courtage.services.demandes_rappel import effacer_anciennes
from courtage.services.cycle import archiver_echus_partout
from courtage.services.dossiers import effacer_echus_partout

if __name__ == "__main__":
    moteur = create_engine(url_applicative(os.environ))
    n = effacer_echus_partout(moteur, date.today())
    print(f"[purge] {n} identité(s) effacée(s)", flush=True)
    a = archiver_echus_partout(moteur, date.today())
    print(f"[purge] {a} dossier(s) archivé(s)", flush=True)
    i = effacer_expirees_partout(moteur, datetime.now(timezone.utc))
    print(f"[purge] {i} inscription(s) non confirmée(s) effacée(s)", flush=True)
    d = effacer_anciennes(moteur, datetime.now(timezone.utc))
    print(f"[purge] {d} demande(s) de rappel de plus de douze mois effacée(s)", flush=True)
    courriel = courriel_depuis_environnement(os.environ)
    if courriel is None:
        print("[rappels] pas d'envoi de courriel configuré (COURTAGE_SMTP_URL) : aucun rappel du cycle annuel", flush=True)
    else:
        r = rappeler_partout(moteur, courriel, os.environ.get("COURTAGE_URL_PUBLIQUE") or os.environ.get("RENDER_EXTERNAL_URL"),
                             date.today(), whatsapp_depuis_environnement(os.environ))
        print(f"[rappels] {r} rappel(s) du cycle annuel", flush=True)
