# Déploiement

Une image, une origine : l'API (FastAPI) sert l'interface construite (`web/dist`).
Le cookie de session reste sur un seul domaine, sans CORS.

## 1. Construire et essayer en recette

```bash
docker compose -f deploiement/recette.yml up --build        # http://localhost:8000
docker compose -f deploiement/recette.yml exec app python -m courtage.demo \
    postgresql+psycopg://postgres:recette@base/courtage \
    postgresql+psycopg://courtage_app:recette-app@base/courtage
docker compose -f deploiement/recette.yml logs app | grep "code de connexion"
```

La recette (`COURTAGE_ENV=recette`) écrit les codes de connexion dans le journal au
lieu de les envoyer : on se connecte avec `690 00 00 01` (DRH), `02` (conseillère) ou
`03` (admin), puis on lit le code dans les logs. Sans le cas AZITO (absent de l'image),
le jeu sème « Société Démo SA » et 40 salariés inventés.

## 2. Ce que fait le conteneur au démarrage (`deploiement/demarrer.sh`)

1. `python -m courtage.deploiement` :
   - applique les migrations avec le rôle **propriétaire** (`COURTAGE_URL_PROPRIETAIRE`) ;
   - autorise `courtage_app` à se connecter, avec le mot de passe de `DATABASE_URL` ;
   - imprime sept contrôles lus dans la base, `[base] PASS …` / `[base] FAIL …`.
   Un seul FAIL arrête le démarrage.
2. `uvicorn` avec `--proxy-headers`, qui donne l'adresse du vrai client aux limites de fréquence.

**« Migrations appliquées » n'est pas une preuve.** La preuve, c'est la ligne
`PASS schéma à jour — base 00NN, code 00NN` et `GET /api/v1/sante`. Cette sonde
répond 503 dès que la base ne porte pas la révision attendue par le code.

## 3. Variables

| Variable | |
|---|---|
| `COURTAGE_URL_PROPRIETAIRE` | rôle propriétaire : migrations, contrôles (jamais utilisé pour servir) |
| `DATABASE_URL` | rôle `courtage_app`, obligatoirement ; `postgres://` accepté |
| `COURTAGE_ENV` | `production` \| `recette` |
| `COURTAGE_CLE_SCEAU` | clé des sceaux ; **ne jamais la changer** : les rapports déjà émis ne se vérifieraient plus |
| `COURTAGE_CLE_AUTH` | clé des codes de connexion (la changer invalide seulement les codes en cours) |
| `COURTAGE_URL_PUBLIQUE` | `https://…`, imprimée sur les rapports pour la vérification |
| `TWILIO_COMPTE`, `TWILIO_JETON`, `TWILIO_EMETTEUR`, `TWILIO_CANAL` | envoi des codes (`whatsapp` ou `sms`) |
| `COURTAGE_PROXYS` | adresses de proxy de confiance pour `X-Forwarded-For` (défaut `*`) |

En production, l'application **refuse de démarrer** dans trois cas : pas de clé de
sceau, pas de clé d'authentification, pas de vrai fournisseur d'envoi. Elle refuse
aussi le mode `entete_dev`.

## 4. Un hébergeur (Render, Railway, un VPS…)

- Un service Docker construit depuis `Dockerfile` ; contrôle de santé sur `/api/v1/sante`.
- PostgreSQL 16. Le propriétaire est l'utilisateur fourni par l'hébergeur. Il doit
  pouvoir `ALTER ROLE` : la migration 0001 crée `courtage_app`, qu'il possède donc.
- Choisir un mot de passe pour `courtage_app` et l'écrire dans `DATABASE_URL`.
  Le démarrage l'applique.
- Une seule instance tant que les limites de fréquence vivent en mémoire. Avec deux
  instances, elles doublent, mais restent des limites.

Après chaque déploiement : lire les sept `[base] PASS` dans les logs, puis
`curl https://…/api/v1/sante`.

## 5. La tâche quotidienne : effacer les identités échues

En courtage, l'identité d'un bénéficiaire et les pièces de son dossier sont effacées
douze mois après le paiement. C'est fait à chaque lecture d'un dossier et à chaque
démarrage. Pour un client qui ne se connecte plus, une tâche programmée le garantit,
une fois par jour, avec le rôle applicatif (Render : un *Cron Job* sur la même
image ; un VPS : `cron`) :

```bash
python -m courtage.purge        # DATABASE_URL = rôle courtage_app ; imprime « [purge] N identité(s) effacée(s) »
```

## 6. Ce qui n'a pas pu être vérifié ici

L'image a été construite et parcourue de bout en bout (migrations, contrôles, sonde,
connexion par code, interface, polices servies par la plateforme) **sans** la couche
`apt-get`. L'environnement de construction bloquait les dépôts Debian. Les
bibliothèques de WeasyPrint (Pango, HarfBuzz, DejaVu) n'y ont donc pas été
installées, ni le rendu PDF vérifié dans l'image. Premier geste sur l'hébergeur :
émettre une étude et ouvrir son rapport.
