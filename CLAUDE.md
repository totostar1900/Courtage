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
