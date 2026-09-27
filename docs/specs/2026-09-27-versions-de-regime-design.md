# Les versions d'un régime : un vocabulaire, une règle de suppression, une page qui ne s'encombre pas

*Conception, 27/09/2026, décidée avec le porteur du projet.*

## Le principe

**Une version reste tant que quelque chose la cite ; tout le reste peut partir.** Ce qui a servi est conservé,
replié ; ce qui n'a jamais servi disparaît sans regret. Un rang en base pèse quelques kilo-octets : l'enjeu n'est pas
l'espace disque, c'est la lisibilité de la page Régime.

## Le parcours

```
Projet ──adopter──▶ Adoptée, à venir ──sa date──▶ En vigueur ──nouvelle version──▶ Remplacée
  │ modifiable            │                                              (repliée, conservée)
  │ sur place             └──supprimer (DRH, motif, si non citée)
  ├──abandonner (motif) ──▶ Abandonnée ──supprimer (si non citée)
  └──supprimer (si non citée)
```

| État | Modifiable | Abandonnable | Supprimable |
|---|---|---|---|
| Projet | oui, sur place | oui (motif) | si non citée |
| Adoptée, à venir | non | non | si non citée ; la DRH seule, avec un motif (c'est annuler sa décision) |
| En vigueur | non | non | jamais |
| Remplacée | non | non | jamais |
| Abandonnée | non | — | si non citée |

**« Citée »** : une étude s'appuie sur la version (en brouillon ou émise), un cahier des charges la nomme, ou elle
est partagée au catalogue. Une étude en brouillon se supprime et libère la version ; une étude émise reste
toujours. Le statut enregistré reste court (`analyse`, `adoptee`, `abandonnee`) ; l'état affiché se déduit des dates
(`regimes.etat_version`).

## Un vocabulaire

- Un seul badge par version, toujours en haut à droite de sa carte (`web/src/regimes.ts`).
- Trois niveaux pour l'analyse, partout : **Bloquant** (empêche d'adopter ou d'évaluer), **Attention** (à regarder
  avant de décider ; « sous le plancher » s'adopte en le confirmant), **Bon à savoir**.
- Les notes juridiques et fiscales sont rédigées comme des repères (« selon notre lecture », « pourrait »), à
  examiner avec le conseil de l'entreprise ; aucune mention « à valider » ne s'affiche.
- « Que veulent dire ces repères ? » définit les états, le parcours et les niveaux.

## Une page en trois zones

- **En application** : la version en vigueur et celle à venir.
- **En discussion** : les projets, chacun avec sa décision (adopter, modifier, abandonner, supprimer).
- **Historique**, replié : les versions remplacées et abandonnées.

## Ne pas accumuler, puis nettoyer

1. **Prévenir** : un projet se corrige sur place (`PUT …/regimes/versions/{id}`) ; pour essayer un barème, la page
   renvoie à Simuler, qui n'enregistre rien.
2. **Rappeler** : un projet sans décision est signalé à 30 jours ; à 90 (`JOURS_SANS_DECISION`), l'alerte
   `projet_a_trancher` invite à l'adopter, l'abandonner ou le supprimer.
3. **Nettoyer** : « Faire le ménage » (`GET/POST …/regimes/menage`) liste ce qui peut partir, avec sa raison et les
   brouillons qui partiront avec. Coché d'office : les versions abandonnées et les projets de plus de 90 jours ; une
   adoption à venir ne l'est jamais, et demande un motif.

## Garde-fous

- Chaque suppression est au journal : qui, quand, le motif, et le statut qu'avait la version.
- La base refuse de supprimer une version qui s'est appliquée (`version_supprimable` dans les déclencheurs de
  `regimes_versions` et `regimes_categories`) ; les clés étrangères retiennent toute version citée.
- Un régime resté sans version disparaît avec sa dernière version.
