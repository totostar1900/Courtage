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
| `COURTAGE_MOT_DE_PASSE_APP` | à la place de `DATABASE_URL` : l'URL applicative est celle du propriétaire, avec `courtage_app` et ce mot de passe (le plan Render) |
| `COURTAGE_ENV` | `production` \| `recette` |
| `COURTAGE_CLE_SCEAU` | clé des sceaux ; **ne jamais la changer** : les rapports déjà émis ne se vérifieraient plus |
| `COURTAGE_CLE_AUTH` | clé des codes de connexion (la changer invalide seulement les codes en cours) |
| `COURTAGE_URL_PUBLIQUE` | `https://…`, imprimée sur les rapports pour la vérification |
| `TWILIO_COMPTE`, `TWILIO_JETON`, `TWILIO_EMETTEUR`, `TWILIO_CANAL` | envoi des codes (`whatsapp` ou `sms`) |
| `COURTAGE_ADMIN_TELEPHONE`, `COURTAGE_ADMIN_NOM` | le premier administrateur, créé au démarrage s'il ne l'est pas déjà (§4c). Facultatives |
| `COURTAGE_EXTRACTION` | `regles` (défaut : lecture sur la plateforme, aucun envoi) \| `claude` (lecture par Claude, l'accord de la personne est demandé avant chaque envoi) |
| `ANTHROPIC_API_KEY` | avec `COURTAGE_EXTRACTION=claude` seulement |
| `COURTAGE_PROXYS` | adresses de proxy de confiance pour `X-Forwarded-For` (défaut `*`) |

En production, l'application **refuse de démarrer** dans trois cas : pas de clé de
sceau, pas de clé d'authentification, pas de vrai fournisseur d'envoi. Elle refuse
aussi le mode `entete_dev`.

## 4. En ligne : Render et courtage.purposecapital.africa

### 4a. Créer le tout (une fois)

1. Render, puis **New**, puis **Blueprint**. Choisir le dépôt GitHub `courtage` et la branche à déployer. Render lit
   `render.yaml` et propose trois ressources :
   - `courtage-db` : PostgreSQL 16, à Francfort, sans accès depuis Internet ;
   - `courtage` : le site, une image Docker ;
   - `courtage-purge` : la tâche quotidienne d'effacement.
2. Renseigner ce que le plan ne peut pas inventer, marqué `sync: false`. On peut le laisser vide pour commencer :
   - `TWILIO_COMPTE`, `TWILIO_JETON`, `TWILIO_EMETTEUR` : l'envoi des codes par WhatsApp ou SMS ;
   - `ANTHROPIC_API_KEY` : seulement si `COURTAGE_EXTRACTION=claude`.
3. **Apply**. Render génère une fois pour toutes, sans que personne ne les voie :
   - `COURTAGE_CLE_SCEAU`, `COURTAGE_CLE_AUTH` ;
   - `COURTAGE_MOT_DE_PASSE_APP`, le mot de passe du rôle `courtage_app`, dont l'URL est dérivée de celle du
     propriétaire.
4. Lire le journal du premier démarrage. Les sept lignes `[base] PASS …` doivent apparaître, puis
   `Uvicorn running`. Un seul FAIL arrête le démarrage, et le journal dit lequel.

**À surveiller au premier démarrage.** La migration 0001 crée le rôle `courtage_app`, et le démarrage lui donne
son mot de passe. L'utilisateur que Render fournit doit en avoir le droit (`CREATEROLE`). S'il ne l'a pas, le
journal dit `permission denied to create role`. Dans ce cas, créer le rôle depuis l'onglet **Shell** de la base
avec un utilisateur qui en a le droit, ou demander au support de Render, puis redéployer.

### 4b. Le domaine

1. Render, puis le service `courtage`, puis **Settings**, puis **Custom Domains**. Le domaine
   `courtage.purposecapital.africa` y est déjà, déclaré par le plan. Render indique la cible,
   `courtage.onrender.com` (ou le nom exact affiché).
2. Chez le gestionnaire DNS de `purposecapital.africa`, ajouter l'enregistrement suivant :

   | Type | Nom | Valeur |
   |---|---|---|
   | CNAME | `courtage` | la cible indiquée par Render |

3. Render vérifie l'enregistrement et émet le certificat HTTPS, en quelques minutes à quelques heures selon le DNS.
   `COURTAGE_URL_PUBLIQUE` vaut déjà `https://courtage.purposecapital.africa`. Les rapports y renvoient pour la
   vérification.

### 4c. Le premier administrateur

Sur le service, onglet **Environment**, renseigner deux variables (le Blueprint les demande déjà) :

| Variable | Exemple |
|---|---|
| `COURTAGE_ADMIN_TELEPHONE` | `+237690000000` |
| `COURTAGE_ADMIN_NOM` | `Prénom Nom` |

puis **Save, rebuild and deploy**. Au démarrage, le journal écrit `[amorcer] administrateur créé : …`. Aux
démarrages suivants, `administrateur déjà en place` : rien n'est réécrit. Aucun Shell n'est nécessaire, ce qui
compte sur l'offre gratuite, qui n'en a pas.

Avec un Shell (offres payantes), la commande directe fait la même chose, pour un autre numéro par exemple :

```bash
python -m courtage.amorcer +237690000000 "Prénom Nom"
```

La personne se connecte ensuite avec ce numéro, par code. Elle ouvre les dossiers clients, inscrit conseillers et
DRH par leur numéro, et fixe les contrats. La commande peut être relancée sans risque : elle promeut, elle ne duplique
pas.

### 4d. De la recette à la production

Le plan démarre en `COURTAGE_ENV=recette`. Les codes de connexion s'écrivent alors dans le journal de Render, que
seul l'exploitant lit : c'est ainsi qu'on se connecte avant que Twilio soit branché. Pour ouvrir aux clients :

1. Renseigner les quatre `TWILIO_*` : le numéro émetteur WhatsApp ou SMS, avec son canal.
2. Passer `COURTAGE_ENV` à `production` et redéployer. L'application **refuse de démarrer** s'il manque la clé de
   sceau, la clé d'authentification ou un vrai fournisseur d'envoi. C'est voulu.

### 4e. Après chaque déploiement

- `curl https://courtage.purposecapital.africa/api/v1/sante` doit répondre `"statut":"ok"`, avec la migration du code.
- Le journal doit montrer les sept `[base] PASS`.
- Au premier déploiement seulement : émettre une étude et ouvrir son rapport PDF (les bibliothèques PDF de l'image,
  §6).

### 4f. Essayer gratuitement : `render.essai.yaml`

La même plateforme sur les offres gratuites de Render, pour un essai en ligne sans rien payer.

1. Render, puis **New**, puis **Blueprint**, puis ce dépôt, branche `main`. Dans **Blueprint Path**, saisir
   `render.essai.yaml`. Si le champ n'est pas proposé, copier ce fichier sur `render.yaml` dans une branche d'essai.
2. **Apply**. Le site répond à l'adresse `https://courtage-essai….onrender.com` affichée par Render. Les rapports
   l'impriment d'eux-mêmes, par `RENDER_EXTERNAL_URL`.
3. Premier administrateur : l'offre gratuite n'a ni Shell ni accès à la base depuis Internet. Renseigner
   `COURTAGE_ADMIN_TELEPHONE` et `COURTAGE_ADMIN_NOM` (§4c), puis redéployer.
4. Connexion : les codes s'écrivent dans l'onglet **Logs** du service. L'essai tourne en recette, sans Twilio.
   Chercher `[connexion]` dans les Logs : chaque demande y dit ce qu'il en est (numéro masqué) — « code
   envoyé », « numéro inconnu » (ce n'est pas le numéro de `COURTAGE_ADMIN_TELEPHONE`), « limite atteinte »
   (3 demandes en 15 minutes : attendre), et à chaque essai « code refusé » avec sa raison ou « connecté ».
   Seul le **dernier** code demandé est valable.

Ce que l'offre gratuite ne fait pas :

| | Offre gratuite | Conséquence pour l'essai |
|---|---|---|
| Veille | Le site s'endort après 15 min sans visite | La première visite prend environ une minute |
| Base | Expire au bout de 30 jours | Refaire l'essai, ou passer en production avant |
| Tâche programmée | Aucune | L'effacement des identités se fait au démarrage et à chaque lecture d'un dossier |
| Domaine | Adresse `onrender.com` | `courtage.purposecapital.africa` reste pour la production |

Rien de ce qui est saisi pendant l'essai ne passe en production : la production a sa propre base.

## 5. La tâche quotidienne : effacer les identités échues

Sur Render, c'est le service `courtage-purge` du plan : rien à faire.

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
