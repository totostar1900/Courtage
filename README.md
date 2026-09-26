# courtage

Courtier d'assurance digital pour le Cameroun et l'Afrique centrale (zone CIMA).
Premier produit : l'étude actuarielle des indemnités de fin de carrière (IFC).

```
api/     moteur actuariel et API (Python)
web/     interface (React, TypeScript)
docs/    spécifications, plans, contexte
```

```bash
cd api
pip install -e ".[dev]"
pytest
```

## Démonstration en local

```bash
# 1. le jeu de démonstration (URL propriétaire, puis URL du rôle applicatif)
cd api/src
python -m courtage.demo postgresql+psycopg://postgres:postgres@localhost/courtage \
                        postgresql+psycopg://courtage_app:<mot de passe>@localhost/courtage
# 2. l'API, en mode développement (identité choisie à l'écran de connexion)
DATABASE_URL=postgresql+psycopg://courtage_app:<mot de passe>@localhost/courtage \
COURTAGE_AUTH=entete_dev uvicorn courtage.principal:app --port 8000
# 3. l'interface
cd ../../web && npm install && npm run dev      # http://localhost:5173
```

Tests de l'interface : `cd web && npm test` ; typage et construction : `npm run build`.
