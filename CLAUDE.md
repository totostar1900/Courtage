# courtage — guide du dépôt

Courtier d'assurance digital, Cameroun et zone CIMA. **La plateforme conseille
et trace ; elle ne porte aucun risque et ne garde pas l'argent des primes.**

Montants en **F CFA entiers**. Interface en français d'abord.

## Méthode

Spécification dans `docs/specs/`, puis plan numéroté dans `docs/plans/`, puis
exécution tâche par tâche : tests d'abord, suite verte avant chaque commit, un
commit par tâche avec le message du plan.

## Commandes

`cd api && pytest` — la suite complète. Les tests de base demandent
`TEST_DATABASE_URL` (rôle PROPRIÉTAIRE, base jetable : le schéma `public` y est
détruit à chaque session) ; sans elle ils sont ignorés.

```bash
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost/courtage_test pytest
```

## Base de données

- Le schéma vient des migrations `api/src/courtage/db/migrations/versions/`,
  écrites à la main en SQL ; les modèles de `courtage.db` le décrivent et un
  test vérifie qu'ils concordent. Une migration nouvelle s'ajoute ; on ne
  réécrit pas une migration appliquée, et il n'y a pas de retour arrière.
- **Les migrations s'exécutent avec le rôle propriétaire**, jamais avec
  `courtage_app` : qui crée une table la possède, et un propriétaire contourne
  la RLS. La migration crée `courtage_app` sans connexion ; le déploiement lui
  donne `LOGIN` et un mot de passe.
- Toute donnée d'un client se lit dans une transaction ouverte par
  `contexte(connexion, organisation_id)`.
- Une étude émise est immuable pour tous les rôles (déclencheur
  `etude_immuable`) ; le journal, les fichiers et les sceaux sont en ajout seul
  pour le rôle applicatif.

## Invariants (spec 2026-09-26, §2)

- Une étude émise est immuable ; une correction est une nouvelle étude.
- Toute hypothèse vient du référentiel, datée et versionnée ; un écart est
  enregistré avec sa justification.
- Une étude ne s'émet qu'avec une convention `valide` du pays de l'organisation.
- Le moteur (`courtage.actuariat`) est pur : pas de base, pas de date du jour.
- Aucun nom de salarié n'est lu ni stocké.

## Modules

```
api/src/courtage/
  actuariat/     moteur IFC, pur
  referentiel/   barèmes datés et sourcés, tables ; règle d'émission (motifs_de_refus)
    donnees/     un fichier JSON par version de barème ; jamais modifié, une nouvelle version s'ajoute
  fichier/       lecture du fichier du personnel et contrôles (bloquant | avertissement)
  db/            modèles, contexte RLS, migrations écrites à la main
  services/      logique métier ; reçoit une Session déjà dans le contexte de l'organisation
  api/           FastAPI : droits (acces(...)), transaction par requête, erreurs métier
  principal.py   point d'entrée uvicorn
```

## API

- Les droits se lisent sur la route : `acces("conseiller")` admet ce rôle,
  `acces()` tout membre. L'administrateur de plateforme n'est membre de rien
  par défaut : il ouvre les dossiers, il ne lit pas les données des clients.
- Erreurs : `ErreurMetier(code, message, statut, details)` → JSON
  `{code, message, details}`. Codes en snake_case, messages en français.
- Toute écriture appelle `journaliser(...)`.
- Les services ne vérifient pas les droits, l'API ne calcule rien.

## Régimes

- Un régime se prend TEL QUEL : sous le plancher, il est enregistré et
  signalé, jamais refusé ; le moteur retient le plus favorable du régime et
  de la convention, ancienneté par ancienneté.
- Seule l'entreprise (`admin_client`) adopte, d'un seul acte ; une version
  adoptée et ses catégories sont immuables (déclencheurs). Une modification
  est une nouvelle version, avec sa date d'effet.
- Les barèmes d'entreprise (0003) sont repris en régimes (0005) ; la table
  reste en lecture pour les études qui les citent.
- Dans un routeur, les chemins littéraux (`/regimes/versions/{id}`) sont
  déclarés AVANT les chemins à paramètre (`/regimes/{id}/versions`).

## Analyse

- `courtage.analyse` est pur, comme le moteur. Un constat est un CALCUL
  (garanti) ou une NOTE juridique (sourcée, `a_valider`). Les notes vivent en
  données dans `referentiel/donnees/notes_juridiques.json` ; on n'écrit pas de
  droit dans le code.
- Une note ne passe `valide` que relue par un juriste ; aucune ne l'est
  aujourd'hui (décision du 2026-09-26).

## Interface (`web/`)

- React + TypeScript + Vite ; `npm test` (Vitest, jsdom) et `npm run build`
  (`tsc` puis Vite) doivent passer avant un commit.
- Inspirée des courtiers en ligne (plan, tâche 7) : un parcours en étapes, le
  conseiller visible, les offres en cartes.
- Les droits se DISENT à l'écran (« votre conseiller émet », « l'adoption
  appartient à l'entreprise ») mais se DÉCIDENT dans l'API : l'interface ne
  cache un bouton que pour la clarté.
- Tous les textes en français ; montants par `format.ts`.

## Connexion

- Code à usage unique reçu par SMS ou WhatsApp (`courtage.auth`,
  `courtage.messagerie`), puis session : cookie `courtage_session` (HttpOnly)
  ou `Authorization: Bearer`. Ni code ni jeton ne sont stockés en clair.
- Toute écriture authentifiée par cookie porte `X-Courtage: 1` (l'interface
  le pose toujours) ; sans lui, 403 `csrf`.
- Un numéro inconnu reçoit la même réponse qu'un numéro connu : ne jamais
  faire varier la réponse selon qu'une personne existe.
- `COURTAGE_AUTH=entete_dev` (en-tête `X-Utilisateur`) : développement et
  tests seulement ; refusé en production, comme l'absence de clé ou de
  fournisseur d'envoi.

## Rapport et sceau

- Le rapport est rendu UNE fois, à l'émission, dans la même transaction
  (`services/rapport.py`, gabarit `services/gabarits/rapport_ifc.html`) ; il
  n'est jamais régénéré. Tout ce qu'il affiche vient de l'étude.
- Le sceau signe ce que le papier affirme (numéro, empreinte de l'étude,
  résumé public) ; le PDF a sa propre empreinte et sa propre signature.
- Sans `COURTAGE_CLE_SCEAU`, clé de développement et mention NON PROBANT ;
  en production l'application refuse de démarrer sans clé.

Un barème nouveau ou révisé : un nouveau fichier `convention_<pays>_<nom>_<année>.json`
avec `en_vigueur_du`, et `en_vigueur_au` posé sur la version précédente. Le
chargement refuse deux versions qui se chevauchent. Un barème dont le texte
n'a pas été relu reste `a_valider` : il calcule, il ne sort pas.

Décisions de produit : `docs/decisions.md`.

## Références de test

Le cas AZITO au 31/12/2019 (`api/tests/fixtures/azito_2019.json`) doit
redonner 60 976 604 F de dette avec la convention CI et 41 404 223 F avec le
barème APB Madagascar (le rapport 2023 erroné). Ne pas modifier ces attendus
pour faire passer un test.

## Déploiement

`render.yaml` (plan Render : base, site, tâche d'effacement ; domaine `courtage.purposecapital.africa`),
`python -m courtage.amorcer` (le premier administrateur ; au démarrage par `COURTAGE_ADMIN_TELEPHONE` quand il n'y a pas de Shell), `Dockerfile` (une image : l'API sert `web/dist`), `deploiement/demarrer.sh`,
`deploiement/recette.yml`, `DEPLOY.md`. Au démarrage, `python -m courtage.deploiement`
migre avec le PROPRIÉTAIRE, ouvre `courtage_app`, puis lit sept contrôles dans la base.
Un FAIL arrête le démarrage. `GET /api/v1/sante` compare la révision en base à celle
du code. **Une nouvelle table qui porte `organisation_id` doit avoir la RLS**, sinon
le démarrage échoue (`HORS_RLS` ne contient qu'`adhesions`, lue avant qu'une
organisation soit connue). Les polices sont servies par la plateforme (`@fontsource`),
aucune ressource tierce. Les limites de fréquence (`api/limites.py`) vivent en mémoire,
par processus.

## Guide

`web/src/guide/` est un seul texte lu par quatre instruments :
- `chapitres.ts` : le guide, par groupes (Commencer, Le parcours, Comprendre, Référence) ;
- `glossaire.ts` : une phrase par mot, lue par l'infobulle `<Terme cle=…>` (et `Cle terme=…`) comme par le glossaire ;
- `lecons.ts` : les leçons rapides (écrans, puis une question dont la raison s'affiche toujours) ;
- `astuces.ts` : « Le saviez-vous ? », une par jour sur le tableau de bord.

`visite.ts` pose des bulles sur `[data-visite=…]`. La visite se lance seule au premier
dossier ouvert (`courtage:visite-faite`), puis depuis « Visite guidée » ; une étape dont
l'élément manque est sautée. `/guide/*` est public, comme `/verifier`, car rien d'un client
n'y figure. `/guide/conventions-preremplies` lit `GET /api/v1/referentiel/conventions`
(public). `guide.test.tsx` refuse un renvoi vers un chapitre ou une leçon qui n'existe
pas, et une étape de visite dont le code ne pose pas la cible. Un panneau qui s'ouvre
sur une page est un `Volet` (croix en haut, voir `communs.tsx`).

## Contrats : courtage ou comparaison

`services/contrats.py`, table `contrats` (migration 0009). Le service rendu est un fait
daté, jamais modifié. Un nouveau contrat prend effet à sa date. **Sans contrat, le
client est en comparaison** : la plateforme ne suppose jamais un mandat. Une
prestation relève du service en vigueur à la date du départ
(`service_a_la_date`), et seule une prestation en courtage pourra collecter une
identité (spec `2026-09-26-prestations-ifc-design.md`). Le service se lit sur le
contrat. **La plateforme ne porte aucune rémunération du courtier** (migration
`0021_sans_remuneration`) : ce qu'il facture relève de son mandat, signé à part.

## Prestations

`services/prestations.py`, table `prestations` (migration 0010), lecture des tableurs
dans `fichier/departs.py`. Une prestation est un départ **sans identité**, un
matricule ; aucun champ de l'API ne nomme une personne (`extra="forbid"`). Le
**dû** est recalculé avec la règle en vigueur le jour du départ
(`regle_au_depart` : version adoptée du régime, sinon convention nommée, sinon celle
de la dernière étude). Le **versé** est déclaré, et l'écart entre les deux est un
constat, jamais un refus. Une ligne ne se modifie pas : une correction ou une
annulation ajoute une ligne (`remplace_id`, unique). Les lignes « actives » sont celles
qu'aucune autre ne remplace. L'import s'enregistre tout ou rien.

## Dossiers de prise en charge (courtage)

`services/dossiers.py`, migration 0011. **L'identité d'un bénéficiaire n'existe qu'en
courtage** (le service à la date du départ), dans `beneficiaires`. Le PDF transmis et
les pièces, qui la contiennent aussi, sont dans `pieces_dossier`. Ces deux tables sont
les seules où `courtage_app` peut DELETE. Tout est effacé douze mois après le paiement
(`effacer_echus`, appelé à chaque lecture, au démarrage, et par
`python -m courtage.purge` chaque jour). Le `resume` d'un sceau est **public** :
jamais d'identité dedans, pas même le matricule. Les étapes sont des lignes
(`dossiers_evenements`) et `_SUITES` dit lesquelles se suivent. Un paiement
constaté s'inscrit sur la prestation par une ligne de correction. Aucune liste ne
porte l'identité, et un `lecteur_client` ne la lit jamais.

## Orientation (comparaison)

`services/orientation.py`. Hors courtage, la plateforme **oriente et ne recueille
rien** : l'assureur et la police du contrat au jour du départ, le montant à demander,
le délai attendu, les pièces d'usage (une aide, pas une liste officielle), et une
**fiche de calcul scellée** `FC-…`, sans identité, rangée dans `documents`
(`prestation_id`, migration 0012). Ce que l'assureur a payé se déclare ensuite
(`prestations.declarer_paiement`, une ligne de correction). Si un dossier de
courtage porte le départ, c'est ce dossier qui écrit son paiement.

## Expérience réelle

`courtage/experience.py` (pur) et `services/experience.py`. L'étude lit les départs
enregistrés **à sa date** et les scelle avec elle (`resultats.experience`) :
- l'attendu (échéancier de l'étude émise précédente) contre le réel ;
- la rotation observée, **proposée** à partir de 5 départs et d'un écart d'un
  demi-point, **jamais appliquée**. La retenir passe par une nouvelle étude, avec une
  justification.

Le cahier des charges en publie l'historique par années regroupées (≥ 3 retraites
par ligne), sans matricule.

## Réponses des assureurs (placement)

`services/reponses.py`, migration 0013. Chaque réponse est confrontée aux
conditions du cahier : conforme, en écart, ou **non renseignée**, qui ne compte pas
comme conforme. Elle est ensuite classée par le coût net actualisé du scénario
central, le même calcul que la comparaison d'offres. La **recommandée** est la moins
chère des conformes. **Le choix appartient à l'entreprise** : un par cahier, et motivé
s'il ne se porte pas sur la recommandée. Une réponse arrive en multipart : la grille
est un champ JSON `donnees`, l'offre PDF est à côté.

## Modèles types

`courtage/modeles.py` (pur), `GET /referentiel/modeles?pays=` (public, CEMAC ; un pays sans convention rend
une liste vide), `composants/ModelesTypes.tsx`. Quatre barèmes CALCULÉS depuis chaque convention en vigueur
— minimum, +25 %, cadres à 1,5, barème unique —, arrondis vers le haut : **conformes par construction**, un
test le vérifie de 1 à 45 ans. Servis comme une `VersionProposee` : le formulaire les reprend, rien n'est
enregistré sans relecture. Aucune donnée d'entreprise. Première étape de « consulter des régimes » ; le
catalogue anonyme et la comparaison chiffrée viendront après (docs/specs/2026-09-26-modeles-types-design.md).

## Méthode actuarielle

`docs/methodologie-actuarielle.md` est la note de méthode de référence (formules, hypothèses par défaut,
financement, expérience, limites), et le chapitre « La méthode actuarielle en détail » du guide en est la
version lisible. **Tenir les deux fidèles au code** : un changement du moteur (`actuariat/ifc.py`), des
hypothèses par défaut ou de la projection se reporte dans les deux, dans le même commit.

## L'échéancier des départs

`services/etudes.echeancier` rend chaque année ET son découpage `par_categorie` (les études émises avant
ne l'ont pas : leur graphique reste d'un seul tenant, le réglage le dit). `web/src/echeancier.ts` (pur) met
en forme ; `composants/Echeancier.tsx` dessine : mesure (probables, si tous partent, valeur actuelle,
départs), lecture annuelle ou cumulée, ensemble ou par catégorie, horizon ; en cumulé, le fonds constitué
en repère et l'année où les versements le dépassent. Palette catégorielle validée (ordre fixe, huit au plus,
puis « Autres catégories ») ; légende, tableau et bulle par barre.

## Catalogue anonyme

`courtage/catalogue.py` (pur : `groupes_visibles`, `anonymiser_categories`), `services/catalogue.py`,
migration 0015. `catalogue_regimes` est PUBLIC (hors RLS, sans `organisation_id`, append-only comme
`sceaux`) : pays, secteur (liste fermée), taille, convention, année, catégories — jamais document, note,
dates. Le lien est chez l'entreprise (`partages_regime`, RLS). Une empreinte `sha256("catalogue:"+org)`
compte les entreprises distinctes, jamais servie. **Un régime ne se voit que dans un groupe d'au moins
5 entreprises**, et le découpage CEMAC → pays → secteur → taille ne descend que si TOUS les sous-groupes
atteignent 5 (sinon la soustraction désignerait la petite case). La convention n'est montrée que si le
secteur l'est. Partager : la DRH (`admin_client`), version adoptée, accord explicite, CEMAC, un seul actif ;
retrait par `catalogue_retraits`. Consulter : toute personne connectée (`GET /catalogue/regimes`).
Conception : docs/specs/2026-09-26-catalogue-anonyme-design.md.

## Extraction assistée

`courtage/extraction/` (module pur + deux moteurs) et `services/extractions.py`,
migration 0014. La plateforme **propose, elle n'enregistre pas** : la proposition
préremplit le formulaire d'une version, et une personne la relit. Chaque valeur
**cite son passage**, que `citation_retrouvee` cherche dans le texte lu localement.
Une valeur introuvable est signalée, jamais reprise en silence.

- **CEMAC seulement**, pour le dossier comme pour le texte.
- **Moteurs** : `regles` par défaut, sans appel externe ; `claude` si
  `COURTAGE_EXTRACTION=claude`, avec `claude-opus-5`, une sortie structurée et
  `fallbacks: "default"`. Un moteur qui envoie le texte à un tiers exige l'accord
  explicite de la personne.
- **Ce qui est gardé** : l'empreinte et la proposition, **jamais le document**.
- **Schémas** : garder `extraction/claude.py:SCHEMA` aligné sur le modèle
  `Extraction`. Un test vérifie que le schéma est strict partout.


## Plateforme ouverte (lot P1, spec 2026-09-29)

- **La vitrine** : `/` montre la vitrine sans session (`Racine` dans `App.tsx`), l'accueil des dossiers avec.
  `/mentions-legales`, `/conditions`, `/confidentialite` sont publiques (`pages/Legal.tsx`, le français fait foi) ;
  le pied de page les relie sur chaque écran. L'identité du cabinet vient de la configuration
  (`courtage/cabinet.py`, `GET /public/cabinet`, variables `COURTAGE_COURTIER_*`), la même que sur le mandat ; une
  valeur absente s'affiche entre crochets, jamais inventée.
- **Les conditions** : changer le texte de `Legal.tsx`, c'est changer `CONDITIONS_VERSION`. L'inscription exige la
  version en vigueur (`conditions_requises`) et le compte la garde (migration 0024).
- **Le signataire du mandat** dit sa qualité (`representant_legal` | `delegataire`) ; le délégataire cite une
  délégation déposée (justificatif `delegation`, par l'administrateur seul). Migration 0025, contrainte en base.
- **Les avis par courriel** (`services/avis.py`) : `prevoir(...)` dans le service, à côté de `journaliser` ; ils
  partent APRÈS la validation (`after_commit`), jamais à l'auteur, jamais avec le contenu du dossier, en français.
  `session_db` pose l'expéditeur et l'adresse publique dans `session.info` ; sans eux (tâche, script), rien ne part.
  Coupés par `utilisateurs.avis_courriel` (migration 0026). L'envoi hebdomadaire des alertes reste suspendu.
- **Sécurité** (`api/securite.py`) : CSP stricte, pas de script en ligne ni de ressource tierce — un ajout qui en
  demande une casse la page, ne pas relâcher la CSP sans le décider. Erreur 500 numérotée (`erreur_interne`),
  alerte `COURTAGE_ALERTE_URL`. Ce qui reste : `docs/securite.md`.
- **Sauvegardes** : `deploiement/verifier_sauvegarde.sh` restaure dans une base jetable et lit les contrôles
  (`python -m courtage.sauvegarde`). DEPLOY.md §7.

## Placement (spec 2026-09-29, clôture du placement)

**La plateforme ne paie rien.** Les primes partent par virement, de la banque de l'entreprise au compte de
l'assureur ; ici, on range l'appel, on confronte ses coordonnées, on reçoit la déclaration et la quittance. Ni lien
de paiement, ni compte du cabinet : une prime qui passerait par le courtier n'existe pas ici.

- `services/placement.py`, `api/placement.py`, migration 0027, page `pages/Placement.tsx`. Sous mandat (capacité
  `cahier`) pour écrire.
- **La police** avance par des faits (reçue = document déposé, signée = date déclarée, première prime encaissée =
  quittance) ; le statut se CALCULE (`statut`), rien ne se coche.
- **Le registre des comptes** (`comptes_assureurs`, plateforme, en ajout seul) : l'administrateur de la plateforme
  seul, chaque ligne avec son contre-appel ; un changement remplace sans effacer. Chaque appel y est confronté
  (`controle` : conforme | modifie | non_enregistre). Un écart se lève par le contre-appel du conseiller, jamais par
  un clic ; l'encaissement ne se confirme pas avant (la base le refuse aussi).
- **Les coordonnées bancaires ne sortent jamais** : ni courriel, ni message ; l'avis dit « un appel vous attend ».
  Ne pas ajouter de montant ni d'IBAN dans `avis.EVENEMENTS`.
- Un virement déclaré sur un appel non confirmé est enregistré (c'est un fait) et journalisé `avant_contre_appel`.

## Consultation des assureurs (spec 2026-09-29, lien assureur)

- `services/consultations.py`, `api/consultations.py`, migration 0028, `composants/Consultations.tsx`, page
  publique `pages/Offre.tsx` (`/offre/:jeton`, comme `/verifier`).
- Le lien est un jeton aléatoire envoyé par courriel, gardé seulement sous forme d'empreinte dans `liens_assureurs`
  (HORS RLS, lu avant qu'une organisation soit connue) ; jamais journalisé. Relancer émet un lien neuf et révoque
  l'ancien ; annuler révoque ; un cahier attribué ou une date limite passée ferme la consultation.
- L'offre déposée par le lien entre dans `reponses_fiche` comme les autres (`consultation_id`, `saisie_par` vide) :
  confrontée, classée, corrigée ou retirée par le conseiller avec motif. Une seule par lien ; l'offre PDF est exigée.
- `avis.prevoir_adresse` : un courriel à une adresse hors compte (l'assureur), aux mêmes règles que les avis.

## Cycle annuel (spec 2026-09-29, cycle annuel)

- `services/annuel.py`, `GET /calendrier`, `composants/AnneeDossier.tsx` (tableau de bord), migration 0029.
- Calculé, jamais stocké : la dernière étude émise D fixe N = D + 1 an ; chaque étape se lit dans les données
  (fichier daté de N, étude émise au N, relevé de l'assureur, revue avant l'anniversaire de la police).
- Les points d'attention n'annoncent que « bientôt » pour le personnel et l'évaluation : leur retard est déjà dit par
  `etude_a_renouveler` et `donnees_anciennes` (`DEJA_ALERTES`). Ne pas doubler.
- Les rappels partent de `python -m courtage.purge` (`rappeler_partout`), au plus un par étape, état et année
  (`rappels_envoyes`), en envoi immédiat (`session.info["envoi_immediat"]`) : un fil mourrait avec la tâche.

## Site public (spec 2026-09-29, site public)

- `web/index.html` porte la description, Open Graph (image `web/public/apercu.png`, 1200×630), l'icône et un
  `<noscript>` ; `__URL_PUBLIQUE__` y est remplacé par le serveur (`api/web.py`, `page_index`). Chaque page publique
  pose son titre (`composants/Titre.tsx`). `/robots.txt` et `/sitemap.xml` : `api/public.py` (`routeur_racine`) ;
  une nouvelle page publique s'ajoute à `PAGES_PUBLIQUES`, une page privée à `NON_INDEXEES`.
- **Être rappelé** : `services/demandes_rappel.py`, `demandes_rappel` (plateforme, hors RLS, effacée à douze mois
  par la tâche quotidienne), `POST /public/rappel` (limité, champ piège `site_web`), `GET/PUT /rappels` (courtier).
  L'avis au courtier ne porte ni numéro ni message.

## Contenus, mesure, portefeuille, WhatsApp (spec 2026-09-29, lot suivant)

- **Pages de contenu** : `/ifc` et `/ifc/cameroun` (`pages/Contenu.tsx`), publiques et au plan du site. Les barèmes
  sont LUS dans le référentiel (`/referentiel/conventions`), avec leurs sources ; le droit reprend la rédaction
  prudente des notes. N'y écrire ni taux ni règle qui ne vienne pas du référentiel.
- **La mesure d'audience** (`services/mesure.py`, migration 0031) : des compteurs par jour, événement (liste fermée)
  et catégorie de référent — ni cookie, ni adresse, ni identifiant. `mesure.ts` ne part pas en démonstration ni quand
  le navigateur demande à ne pas être suivi (GPC, DNT), une fois par session et par événement. L'inscription et la
  signature du mandat se comptent côté serveur. L'entonnoir : `GET /mesures`, sur l'accueil du courtier.
- **Le portefeuille** (`services/portefeuille.py`, `GET /portefeuille`, `pages/Portefeuille.tsx`) : l'étape de chaque
  dossier est CALCULÉE à la lecture (la plus avancée des faits), rien n'est stocké. Lu dossier par dossier dans son
  contexte RLS, qui est vidé à la fin. Courtier : tout ; conseiller : ses dossiers ; les autres : 403.
- **Les avis sur WhatsApp** (migration 0032, `utilisateurs.avis_whatsapp`, désactivé par défaut) : `prevoir` range
  aussi un message pour qui l'a demandé et a un numéro, si `session.info["whatsapp"]` existe
  (`messagerie.WhatsAppAvis`, variables `TWILIO_WHATSAPP_*`). Un modèle approuvé, deux variables : le sujet et le
  lien — jamais le texte de l'avis. Le profil ne propose l'option que si le modèle existe (`whatsapp_disponible`).
- **Préparer le test d'intrusion** : `docs/securite/test-intrusion.md` est le cahier à remettre au prestataire.
  `tests/test_isolation.py` parcourt TOUTES les routes de l'application : une route nouvelle de dossier doit refuser
  un étranger (par une dépendance, avant le corps — pas un test dans la fonction) ; une route publique nouvelle doit
  entrer dans `PUBLIQUES` avec sa raison, et dans une limite de fréquence si elle écrit ou devine.

## Parcours client revu (spec 2026-09-29, parcours client et design)

- **Déposer un fichier** : toujours `DepotFichier` (zone, fichier retenu en clair, « Changer », « Retirer »), jamais
  un `<input type="file">` nu. Le champ est nommé par `aria-labelledby` sur son libellé.
- **Un téléphone** : toujours `ChampTelephone` (indicatif + numéro national → E.164). `composer` / `decomposer`.
- **L'essai** garde sa saisie trente minutes dans le navigateur (`garde_le`, `DUREE_ESSAI_MS`) ; « Retirer » l'oublie.
- **Plus de page Simuler** : le comparatif de régimes est un pli de la page Étude (`ComparerRegimes`, `#comparer`).
- **Aucun fil écrit dans l'application** : la page Contact (`/contact`, alias `/messages`) ouvre WhatsApp,
  le courriel ou l'appel (`contact.ts`) ; l'ancien fil ne s'affiche plus, ni son compte de non-lus. Un bouton
  WhatsApp flotte en bas à droite (`BoutonWhatsApp`) : vers le conseiller dans un dossier (à défaut, le cabinet),
  vers le cabinet sur les pages publiques ; jamais pour le courtier. Ni retrait d'inscription ni « Nettoyer »
  à l'écran (les routes API restent, celles des messages aussi).
- **Capacité `departs`** (`activation.SOUS_CONTRAT`) : déclarer, importer, corriger un départ ou ouvrir une prise
  en charge exige un contrat en vigueur — une police « en vigueur » du placement, ou un contrat de courtage avec son
  assureur (`contrat_en_vigueur`). Les tests d'API qui déclarent des départs appellent `sous_contrat` (outils).
- **L'accompagnement dès l'inscription** : `POST /inscription` accepte `accompagnement: {besoins, message}` (même
  transaction), `GET /public/besoins` donne les cases.
- **Plus de page Accompagnement** (2026-09-30) : le mandat se demande, se propose, se lit et se signe dans la page
  Contrat (`pages/Mandat.tsx`, monté par `Contrat.tsx`, ancre `#mandat`) ; `/accompagnement` y mène, et les avis
  (`avis.py`) pointent sur `/contrat`. « Contrat » ouvre le parcours (`parcours.ts`) et n'est plus en double dans
  les outils du menu.
- **L'étude dit sa base de calcul** : le minimum de la convention collective (avec son code) ou une version du
  régime de l'entreprise (chaque catégorie y porte déjà sa convention ; le champ convention disparaît).
- **Les offres** : la page `financement` est « Offres » (`OffresDossier`) — les réponses du dernier cahier, rien
  d'autre ; plus aucune comparaison sur des chiffres saisis. Classement par **rendement net** (`financement.rendement_net`,
  `classement_rendement`) ; la recommandée est la meilleure des conformes hors `pour_comparaison` (migration 0033).
  L'entreprise ajoute un devis « pour comparaison » (`POST …/reponses/comparaison`) seulement après une offre du
  conseiller ; il ne se retient pas (`offre_pour_comparaison`).
- **Le socle visuel** est le dernier bloc de `styles.css` ; les plis s'écrivent `<details className="pli">` avec
  `<summary>` puis `<div className="pli-corps">`. L'audit et ce qui reste : `docs/design/audit-2026-09-29.md`.

## Identité Glacier (2026-09-29, docs/design/identite-glacier.md)

- Geist (texte) et Geist Mono (chiffres, étiquettes), servies par la plateforme (`@fontsource/geist-sans`,
  `@fontsource/geist-mono`) : la CSP n'admet aucune police tierce.
- Clair et sombre : les jetons en tête de `styles.css` (clair, sombre, impression) ; `theme.ts` pose `data-theme`.
  **Jamais une couleur en dur dans une règle** : un jeton, sinon le thème sombre casse.
- La forme (angles de 2 px, traits d'un pixel, chiffres en chasse fixe) et la vitrine : le dernier bloc de
  `styles.css`. L'ancien socle (ombres, rayons de 16 px, Young Serif, Figtree) n'existe plus.

## Marque Nitch (2026-09-29, docs/design/marque-nitch.md)

- Le logotype est `composants/Marque.tsx` (contours de Geist, carré à `--accent`) ; favicon, icône de téléphone et
  aperçu de lien dans `web/public/`. Titres « … — Nitch ».
- Le pied nomme le cabinet comme exploitant, sous son nom légal ; les documents scellés gardent ce nom légal.
- « courtage » reste le nom du métier dans le texte, et les noms techniques (`courtage_session`, `X-Courtage`,
  `COURTAGE_*`, le paquet) ne changent pas.
- La vitrine : « Être rappelé » est un bouton du bandeau ; trois engagements en bande ; « Ce que vous obtenez » mène
  par la concurrence des assureurs et le suivi dans la durée ; « L'expérience à votre service » dit l'équipe (les faits
  donnés par le cabinet : 50+ ans cumulés, actuaires, Cameroun · Afrique · Europe — jamais l'Amérique ; n'en ajouter aucun).
  Aucune page de présentation (vitrine, inscription, essai, contrat, contenus, guide) ne parle de la
  rémunération du courtier : seuls les conditions d'utilisation et le mandat la disent (garde : vitrine.test.tsx).
- Le visuel du bandeau d'accueil défile (`ApercuDefilant`) : l'engagement, les offres classées, les départs à venir,
  un dossier suivi — des chiffres d'exemple, marqués « Exemple ». Pause au survol et au focus, immobile quand
  l'appareil demande moins de mouvement.
- Trois thèmes : clair, **pénombre** (`data-theme="dim"`, une ardoise à mi-chemin, chaque couleur ≥ 4,5:1), sombre.
- **Téléphone** (`ChampTelephone`) : tous les pays de `libphonenumber-js` (245), nommés par `Intl.DisplayNames` ; la
  CEMAC en tête. L'indicatif se tape (« +33 », « 33 », « France », « fr ») ou se choisit dans la liste filtrée ; un
  indicatif partagé (+1, +44, +7) garde le pays choisi. `composer` passe par la bibliothèque : le 0 national tombe
  où le plan de numérotation le veut (France), reste où il fait partie du numéro (Côte d'Ivoire).
- **L'étude** choisit la convention dans les conventions du pays (`GET /referentiel/conventions`) ; une seule : elle
  se lit, sans champ.
- **Le rail du dossier ne bouge pas** : collé à sa place au défilement (`--rail-haut`, mesuré au chargement), chaque
  page s'ouvre en haut (`App.tsx`), et `scrollbar-gutter: stable` garde la place de la barre de défilement.
- Se déconnecter mène à l'accueil (`/`).

