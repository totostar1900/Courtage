#!/bin/sh
# Au démarrage du conteneur : migrer et contrôler la base (rôle propriétaire), puis servir (rôle applicatif).
# Un contrôle en FAIL arrête ici : le conteneur ne sert rien plutôt que servir une base mal verrouillée.
set -e
python -m courtage.deploiement
exec uvicorn courtage.principal:app --host 0.0.0.0 --port "${PORT:-8000}" \
     --proxy-headers --forwarded-allow-ips="${COURTAGE_PROXYS:-*}"
