# courtage — guide du dépôt

Courtier d'assurance digital, Cameroun et zone CIMA. **La plateforme conseille
et trace ; elle ne porte aucun risque et ne garde pas l'argent des primes.**

Montants en **F CFA entiers**. Interface en français d'abord.

## Méthode

Spécification dans `docs/specs/`, puis plan numéroté dans `docs/plans/`, puis
exécution tâche par tâche : tests d'abord, suite verte avant chaque commit, un
commit par tâche avec le message du plan.

## Commandes

`cd api && pytest` — la suite complète.

## Invariants (spec 2026-09-26, §2)

- Une étude émise est immuable ; une correction est une nouvelle étude.
- Toute hypothèse vient du référentiel, datée et versionnée ; un écart est
  enregistré avec sa justification.
- Une étude ne s'émet qu'avec une convention `valide` du pays de l'organisation.
- Le moteur (`courtage.actuariat`) est pur : pas de base, pas de date du jour.
- Aucun nom de salarié n'est lu ni stocké.

## Références de test

Le cas AZITO au 31/12/2019 (`api/tests/fixtures/azito_2019.json`) doit
redonner 60 976 604 F de dette avec la convention CI et 41 404 223 F avec le
barème APB Madagascar (le rapport 2023 erroné). Ne pas modifier ces attendus
pour faire passer un test.
