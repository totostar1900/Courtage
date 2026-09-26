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
  conseiller visible, les offres en cartes, la rémunération en clair.
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
`python -m courtage.amorcer` (le premier administrateur), `Dockerfile` (une image : l'API sert `web/dist`), `deploiement/demarrer.sh`,
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
contrat, **jamais sur la rémunération** : une commission hors courtage est un constat
(`commission_sans_mandat`), pas une correction.

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

