#!/usr/bin/env bash
# Restaurer une sauvegarde dans une base JETABLE et y lire ce que la production doit porter (DEPLOY.md §7).
#
#   SOURCE_URL=<url propriétaire de la production>  CIBLE_URL=<url propriétaire d'une base jetable> \
#     deploiement/verifier_sauvegarde.sh [copie.dump]
#
# Sans fichier, une copie est prise de SOURCE_URL (pg_dump, format custom) ; avec un fichier (la sauvegarde
# téléchargée depuis l'hébergeur), c'est lui qui est restauré. La base CIBLE est VIDÉE : jamais la production.
set -euo pipefail

: "${CIBLE_URL:?CIBLE_URL : la base jetable où restaurer}"
if [[ -n "${SOURCE_URL:-}" && "${CIBLE_URL}" == "${SOURCE_URL}" ]]; then
  echo "[sauvegarde] refus : la cible est la source." >&2; exit 2
fi

copie="${1:-}"
if [[ -z "$copie" ]]; then
  : "${SOURCE_URL:?SOURCE_URL, ou un fichier de sauvegarde en argument}"
  copie="$(mktemp --suffix=.dump)"
  trap 'rm -f "$copie"' EXIT
  pg_dump --format=custom --no-owner --dbname="$SOURCE_URL" --file="$copie"
  echo "[sauvegarde] copie prise : $(du -h "$copie" | cut -f1)"
fi

psql "$CIBLE_URL" -v ON_ERROR_STOP=1 -qc "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
pg_restore --no-owner --exit-on-error --dbname="$CIBLE_URL" "$copie"
echo "[sauvegarde] restaurée dans la base jetable"

cd "$(dirname "$0")/../api"
PYTHONPATH=src python -m courtage.sauvegarde "$CIBLE_URL"
