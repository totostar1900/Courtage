# Prestations IFC : déclarer un départ, reprendre les départs passés

*Statut : proposition, à valider. Demande du 26/09 : « pouvoir renseigner une nouvelle
prestation pour prise en charge, ou une ancienne pour intégration aux rapports ».*

## 1. Deux besoins, un seul objet

Une **prestation** est un départ en retraite qui a donné, ou donnera, lieu au versement
d'une IFC. Elle naît de deux façons :

| | Nouvelle prestation | Prestation passée |
|---|---|---|
| Qui | l'entreprise (DRH) | l'entreprise ou le conseiller |
| Quand | un salarié part, ou va partir | reprise de l'historique (3 à 5 ans) |
| But | demander le paiement au fonds / à l'assureur | expérience réelle dans les rapports |
| Suite | dossier de prise en charge transmis à l'assureur | aucun envoi, un enregistrement |

## 2. Ce qu'elle contient

- **Toujours** : le matricule (qui la relie au fichier du personnel), la date de départ,
  le motif (retraite ; les autres motifs ne donnent pas d'IFC mais comptent pour la
  rotation), l'ancienneté, le salaire de référence, le montant **dû** selon le régime,
  le montant **versé** par l'entreprise (qui peut être supérieur : elle est souveraine),
  et la part demandée au fonds.
- **Pour une prise en charge seulement** : l'identité du bénéficiaire (nom, pièce, moyen
  de paiement). C'est le moment prévu par la spec §2.1 : « l'identité ne sert qu'au
  sinistre ». Elle est gardée dans une table à part et transmise à l'assureur. Elle
  n'entre ni dans un rapport, ni dans un cahier des charges, et un délai de conservation
  est fixé (question 3).
- Pièces : le certificat de travail, l'attestation de départ, le calcul signé.

## 3. Ce que la plateforme en fait

1. **Contrôle** : le montant dû, recalculé avec le régime en vigueur à la date du départ,
   est comparé au montant déclaré. L'écart est signalé, jamais bloqué ; un montant versé
   au-delà du dû est normal.
2. **Prise en charge** : un dossier scellé (même mécanisme que le rapport) est émis vers
   l'assureur. Le statut suit les étapes déclarée → transmise → payée par l'assureur, ou
   refusée avec son motif, et le délai est mesuré contre le délai de paiement exigé au
   cahier des charges.
3. **Rapports** :
   - l'étude suivante confronte l'attendu (échéancier des prestations probables) au réel ;
   - la rotation observée alimente les hypothèses, en proposition motivée, jamais en
     remplacement automatique ;
   - le fonds baisse du montant payé, qui s'inscrit au registre ;
   - dans le cahier des charges, l'historique est agrégé par année, sans identité (au
     moins 3 départs par ligne, sinon regroupement).
4. **Registre** : une prestation est une écriture. Une correction est une nouvelle ligne
   qui annule la précédente, jamais une modification.

## 4. Questions

1. **Paiement** : la plateforme ne fait que **transmettre** la demande à l'assureur et
   suivre sa réponse, sans jamais toucher à l'argent. D'accord ?
2. **Qui déclare** : la DRH seule, le conseiller vérifiant avant transmission ? Ou le
   conseiller peut-il aussi déclarer au nom de l'entreprise (reprise d'historique) ?
3. **Conservation de l'identité** : combien de temps après le paiement ? Proposition :
   supprimée 12 mois après le paiement, seul l'enregistrement anonyme restant.
4. **Historique** : jusqu'où remonter, et sous quelle forme (tableur importé comme le
   personnel, ou saisie une à une) ? Proposition : les deux, 5 ans par défaut.
5. **Motifs hors retraite** (démission, licenciement, décès) : les enregistrer, sans IFC,
   pour mesurer la rotation réelle ? Proposition : oui, sans identité.
