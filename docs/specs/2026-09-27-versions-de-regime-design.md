# Les versions d'un régime : brouillon ou adoptée, un menu ⋮, des notes qui communiquent

*Conception, 27/09/2026, décidée avec le porteur du projet.*

## Deux statuts, rien d'autre

| Statut | Ce que c'est | Ce qu'on en fait (menu ⋮) |
|---|---|---|
| **Brouillon** (en analyse) | une version à l'étude | Modifier (sur place) · Dupliquer · Analyser · Comparer dans Simuler · Adopter… · Supprimer |
| **Adoptée** | une version figée parce que communiquée | Note aux salariés (PDF) · Note aux assureurs (PDF) · Dupliquer en brouillon · Analyser · Comparer · Supprimer… |

Les dates sont une **information**, écrite sur la carte : « s'applique depuis le … », « s'appliquera à partir du … »,
« s'est appliquée du … au …, remplacée par la version N » (`regimes.application`). La page range les versions en
trois zones : En application, Brouillons, Historique (replié).

## Adopter, c'est communiquer

L'adoption (par l'administrateur de l'entreprise, qui confirme une éventuelle non-conformité) fige la version. Ses deux
notes, scellées à la première émission (préfixe `NR-`) et rangées dans `documents` :

- **aux salariés** : ce que le régime verse, catégorie par catégorie, en mois de salaire et en mots, avec le rappel du
  minimum conventionnel ; aucun chiffre de dette, aucun nom ;
- **aux assureurs** : le régime à assurer (barèmes, conditions, événements couverts, conventions plancher), la
  population par catégorie, les points relevés.

Pour changer une version adoptée, on la **duplique en brouillon**, qu'on adopte à son tour.

## Supprimer

- Un **brouillon** se supprime toujours ; ses études en brouillon partent avec (la plateforme le dit avant).
- Une version **adoptée** se supprime tant que rien ne la cite : une étude émise, un cahier des charges, une note émise
  ou un partage au catalogue la retiennent (clés étrangères). C'est revenir sur une décision : l'administrateur de
  l'entreprise seul, avec un motif.
- Un régime resté sans version disparaît avec sa dernière version. Chaque suppression est au journal.

## Ne pas accumuler

- Un brouillon se corrige sur place ; pour essayer un barème, Simuler n'enregistre rien.
- Un brouillon sans décision est signalé à 30 jours ; à 90, l'alerte invite à trancher.
- « Faire le ménage » liste ce qui peut partir, avec sa raison ; les brouillons de plus de 90 jours sont cochés d'office,
  une version adoptée jamais (motif requis).

## Garde-fous en base (migration `0017_versions_et_notes`)

- Une version adoptée ne se modifie pas, ni ses catégories ; elle ne disparaît qu'avec ses catégories (ON DELETE
  CASCADE), et seulement si aucune clé étrangère ne la retient.
- Les documents acceptent une version (`documents.version_id`) ; les sceaux, le préfixe `NR-`. La vérification publique
  d'un numéro ne dépend que de `sceaux`.
