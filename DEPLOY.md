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
| `COURTAGE_SMTP_URL`, `COURTAGE_COURRIEL_EXPEDITEUR` | l'envoi du code de vérification du courriel à l'inscription : `smtp[s]://utilisateur:mot-de-passe@hôte:port` (tout fournisseur SMTP) et l'adresse d'envoi. Sans elles, le code s'écrit au journal : l'inscription ne peut pas aboutir en production |
| `COURTAGE_COURTIER_NOM`, `COURTAGE_COURTIER_AGREMENT`, `COURTAGE_COURTIER_ADRESSE` | l'identité du cabinet imprimée sur le mandat de courtage (raison sociale, n° d'agrément, siège). Sans elles, le mandat porte des crochets à compléter : les renseigner avant la première signature réelle — un mandat signé ne se modifie plus |
| `COURTAGE_COURTIER_RCCM`, `COURTAGE_COURTIER_COURRIEL`, `COURTAGE_COURTIER_TELEPHONE` | le reste de l'identité du cabinet, sur la vitrine (`/`), les mentions légales et la politique de confidentialité (`GET /api/v1/public/cabinet`). Une valeur absente s'affiche entre crochets : les renseigner avant d'ouvrir le site au public |
| `COURTAGE_ALERTE_URL` | facultative : une adresse qui reçoit un POST JSON à chaque erreur inattendue (numéro d'incident, route, type d'erreur ; champ `text` pour Slack, Teams ou Discord), au plus un par minute (§7) |
| `TWILIO_COMPTE`, `TWILIO_JETON`, `TWILIO_EMETTEUR`, `TWILIO_CANAL` | envoi des codes (`whatsapp` ou `sms`) |
| `TWILIO_WHATSAPP_MODELE`, `TWILIO_WHATSAPP_EMETTEUR` | les avis sur WhatsApp, pour qui les a demandés dans son profil. WhatsApp refuse un texte libre qu'une entreprise envoie la première : créer dans la console Twilio (Content Template Builder) **un** modèle, catégorie *Utility*, en français, `Courtage : {{1}} — {{2}}` (le sujet de l'avis, puis le lien), le faire approuver, et mettre son identifiant `HX…` ici. L'émetteur est le numéro WhatsApp Business (`TWILIO_EMETTEUR` suffit quand `TWILIO_CANAL=whatsapp`). Sans modèle, rien ne part sur WhatsApp et le profil ne le propose pas ; les avis restent par courriel. La tâche quotidienne (§5) les reçoit aussi, pour les rappels du cycle annuel |
| `COURTAGE_DEMO` | `1` : sème au premier démarrage la Société Démo SA (fictive), suivie par les administrateurs. Refusée en production. `1` dans `render.essai.yaml` |
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
- `curl -sI https://courtage.purposecapital.africa/ | grep -i content-security-policy` : les en-têtes de sécurité
  sont posés (§7).
- Au premier déploiement seulement : émettre une étude et ouvrir son rapport PDF (les bibliothèques PDF de l'image,
  §6).

### 4e bis. Être trouvé

- `COURTAGE_URL_PUBLIQUE` doit être l'adresse définitive (`https://courtage.purposecapital.africa`) : elle est posée
  dans l'adresse canonique et l'image d'aperçu de chaque page, et dans `/sitemap.xml`.
- Vérifier : `curl -s https://…/robots.txt`, `curl -s https://…/sitemap.xml`, et l'aperçu d'un lien (le coller dans
  WhatsApp, ou le débogueur de partage de LinkedIn).
- Déclarer le site et son plan dans Google Search Console (propriété de domaine, enregistrement DNS TXT).

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
5. Le dossier de démonstration : avec `COURTAGE_DEMO=1` (déjà dans `render.essai.yaml`), le premier démarrage
   sème la Société Démo SA, la même que la démonstration statique : 40 salariés inventés, l'accord et son
   projet d'avenant, des départs, un dossier de prise en charge, une étude émise, un cahier des charges et trois
   réponses d'assureurs fictifs. Le journal écrit `[demo] Société Démo SA semée`. Les administrateurs en sont
   conseillers ; ceux créés APRÈS le semis l'ouvrent depuis rien — ajouter la variable avant le premier
   démarrage, ou déclarer l'administrateur d'abord. Le semis a lieu une fois PAR VERSION (`VERSION_DEMO`
   dans `courtage/demo.py`) : les études sont figées, donc quand le code sait montrer davantage (v2 :
   l'échéancier par catégorie), une Société Démo SA neuve est semée au démarrage et l'ancienne sort de la
   liste des administrateurs — rien n'est effacé. Le journal écrit `… version 2 … ancienne(s) retirée(s)`.

Ce que l'offre gratuite ne fait pas :

| | Offre gratuite | Conséquence pour l'essai |
|---|---|---|
| Veille | Le site s'endort après 15 min sans visite | La première visite prend environ une minute |
| Base | Expire au bout de 30 jours | Refaire l'essai, ou passer en production avant |
| Tâche programmée | Aucune | L'effacement des identités et l'archivage des dossiers clôturés se font au démarrage (et l'effacement à chaque lecture d'un dossier) |
| Domaine | Adresse `onrender.com` | `courtage.purposecapital.africa` reste pour la production |

Rien de ce qui est saisi pendant l'essai ne passe en production : la production a sa propre base.

## 5. La tâche quotidienne : effacer les identités échues, archiver les dossiers clôturés

Sur Render, c'est le service `courtage-purge` du plan : rien à faire.

En courtage, l'identité d'un bénéficiaire et les pièces de son dossier sont effacées
douze mois après le paiement. C'est fait à chaque lecture d'un dossier et à chaque
démarrage. Pour un client qui ne se connecte plus, une tâche programmée le garantit,
une fois par jour, avec le rôle applicatif (Render : un *Cron Job* sur la même
image ; un VPS : `cron`) :

```bash
python -m courtage.purge        # DATABASE_URL = rôle courtage_app ; imprime « [purge] N identité(s) effacée(s) »
                                #   puis « [purge] N dossier(s) archivé(s) »
```

La même tâche envoie les **rappels du cycle annuel** : quand une étape de l'année (personnel, évaluation, relevé de
l'assureur, revue du contrat) devient bientôt due, puis quand elle est en retard — au plus un courriel par étape, état
et année (`[rappels] N rappel(s) du cycle annuel`). Elle a besoin de `COURTAGE_SMTP_URL`,
`COURTAGE_COURRIEL_EXPEDITEUR` et `COURTAGE_URL_PUBLIQUE`, que le plan Render reprend du service web ; sans envoi
configuré, elle le dit et n'envoie rien.

La même tâche archive les dossiers clôturés depuis 90 jours : leur personnel déposé est vidé,
l'identité des bénéficiaires effacée, et le dossier ne s'ouvre plus. Études, rapports scellés et journal
restent ; chaque document se vérifie toujours par son numéro. Voir
`docs/specs/2026-09-27-cycle-de-vie-des-dossiers-design.md`.

## 6. Ce qui n'a pas pu être vérifié ici

L'image a été construite et parcourue de bout en bout (migrations, contrôles, sonde,
connexion par code, interface, polices servies par la plateforme) **sans** la couche
`apt-get`. L'environnement de construction bloquait les dépôts Debian. Les
bibliothèques de WeasyPrint (Pango, HarfBuzz, DejaVu) n'y ont donc pas été
installées, ni le rendu PDF vérifié dans l'image. Premier geste sur l'hébergeur :
émettre une étude et ouvrir son rapport.


## 7. Surveiller, alerter, restaurer

### 7a. La sonde et la page d'état

`GET /api/v1/sante` répond 200 quand la base répond ET porte le schéma du code, 503 sinon. Render s'en sert pour
basculer le trafic ; un service de surveillance externe (UptimeRobot, Better Stack, Freshping… une offre gratuite
suffit) s'en sert pour prévenir **et publier une page d'état** :

1. Créer une sonde HTTP sur `https://courtage.purposecapital.africa/api/v1/sante`, toutes les 5 minutes, alerte
   par courriel (et SMS si l'offre le permet) après deux échecs.
2. Créer la page d'état publique du service et la relier depuis le pied de page si l'on veut la montrer aux clients.

### 7b. Les incidents

Une erreur inattendue répond 500 avec un numéro d'incident (`erreur_interne`, `details.incident`) ; le client le voit
et peut le citer. Le journal du serveur porte la même ligne `[incident] <numéro> — <route> — <type>`, avec la pile.
Avec `COURTAGE_ALERTE_URL`, un POST part à chaque incident (au plus un par minute, pour ne pas inonder) : un webhook
entrant Slack, Teams ou Discord convient tel quel. Le message d'erreur n'est **jamais** envoyé : il peut contenir des
données.

### 7c. Les sauvegardes, prouvées par une restauration

Render sauvegarde la base chaque jour (plans payants : restauration à un instant donné). Une sauvegarde qu'on n'a
jamais restaurée n'est pas une preuve. **Une fois par mois, et avant toute migration risquée** :

```bash
# une base jetable (locale ou une petite base Render), JAMAIS la production comme cible
SOURCE_URL="<url externe du propriétaire, production>" \
CIBLE_URL="postgresql://postgres:…@localhost/courtage_restau" \
  deploiement/verifier_sauvegarde.sh                   # ou : … verifier_sauvegarde.sh sauvegarde-render.dump
```

Le script copie (ou prend le fichier téléchargé depuis Render), vide la base cible, restaure, puis imprime les
contrôles du démarrage (`[sauvegarde] PASS …`), le nombre de lignes des tables qui comptent et la date du dernier acte
au journal. **Lire** : tout PASS, des comptes cohérents avec la production, un dernier acte du jour de la copie. Il
refuse une cible égale à la source. Noter la date et le résultat dans le registre d'exploitation.

Les sceaux se vérifient après restauration avec la même `COURTAGE_CLE_SCEAU` : une sauvegarde sans la clé ne prouve
plus rien. La clé se garde à part (coffre de mots de passe), jamais dans la sauvegarde.

### 7d. Ce que la sécurité doit encore

`docs/securite.md` dit ce qui est en place et ce qui reste, dont un test d'intrusion externe avant l'ouverture au
public.
