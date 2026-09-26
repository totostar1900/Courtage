# Prestations IFC : déclarer un départ, reprendre les départs passés

*Statut : proposition révisée le 26/09 après la décision sur les deux services.*

Demande du 26/09 : « pouvoir renseigner une nouvelle prestation pour prise en charge,
ou une ancienne pour intégration aux rapports ». Décision du même jour : la plateforme
offre **deux services**, et c'est le service choisi par le client qui décide qui traite
une prestation.

## 1. Deux services, dits par le contrat

| | **Courtage** | **Comparaison** |
|---|---|---|
| Rôle de la plateforme | courtier mandaté : intermédiaire entre le client et l'assureur | comparateur : elle a éclairé le choix, le client a contracté seul |
| Contrat d'assurance | placé par la plateforme | signé directement entre le client et l'assureur |
| Une prestation | **la plateforme la collecte**, monte le dossier, le transmet et le suit | **le client s'adresse à l'assureur** ; la plateforme lui dit à qui, et avec quelles pièces |
| Identité du bénéficiaire | collectée, parce que c'est elle qui transmet | **jamais collectée** |
| Rémunération | commission ou mixte | honoraires (étude, comparaison) |

Le service est un fait **daté**, porté par un **contrat suivi** :
- l'assureur ;
- le numéro de police ;
- la date d'effet ;
- le service (`courtage` | `comparaison`) ;
- pour le courtage, la référence du mandat.

Un client peut passer de la comparaison au courtage (ou l'inverse) à une date. Une
prestation relève alors du service **en vigueur à sa date de départ**. Un client sans
contrat suivi est en comparaison par défaut. La plateforme ne suppose jamais un mandat
qu'elle n'a pas.

*Lien avec la rémunération (tâche 5)* : le mode `commission` ou `mixte` ne vaut pas
mandat. Le service se lit sur le contrat, jamais sur la rémunération. Une incohérence
(commission sans contrat en courtage) est signalée au conseiller, pas corrigée.

## 2. Ce que tout le monde saisit : la prestation anonyme

Dans les deux services, une prestation est d'abord un **enregistrement sans identité** :
- le matricule, qui la relie au fichier du personnel ;
- la date de départ et le motif (voir §5) ;
- l'ancienneté et le salaire de référence ;
- le montant **dû** selon le régime en vigueur à la date du départ, recalculé par la
  plateforme ;
- le montant **versé** au salarié, déclaré ; il peut dépasser le dû, l'entreprise est
  souveraine ;
- la part **prise en charge par le fonds** : demandée, puis payée par l'assureur.

L'écart entre dû et versé est **signalé**, jamais bloqué. C'est cet enregistrement que
lisent les rapports (§4), quel que soit le service.

## 3. Ce que chaque service ajoute

**Courtage : la plateforme porte le dossier.**
1. La DRH déclare le départ. En plus de l'enregistrement anonyme, elle saisit
   l'identité du bénéficiaire (nom, pièce d'identité, moyen de paiement) et joint les
   pièces : certificat de travail, attestation de départ, calcul signé.
2. Le conseiller vérifie. La plateforme émet un **dossier de prise en charge scellé**
   (même mécanisme que le rapport, numéro `PC-…`) et le transmet à l'assureur.
3. Suivi : `déclarée → transmise → payée` (montant et date) ou `refusée` (motif). Le
   délai est mesuré contre le délai de paiement exigé au cahier des charges, et un
   retard est signalé à la DRH et au conseiller.
4. L'identité vit dans une table à part (`beneficiaires`), sous RLS. Elle ne figure dans
   aucun rapport, aucun cahier des charges, aucune exportation. Elle est **effacée
   12 mois après le paiement** (proposition). Reste l'enregistrement anonyme et
   l'empreinte du dossier scellé, qui continue de se vérifier.

**Comparaison : le client traite avec son assureur.**
1. Au départ d'un salarié, la plateforme affiche :
   - l'assureur et le numéro de police ;
   - la liste des pièces habituellement demandées (guide) ;
   - le montant dû qu'elle a calculé, à joindre ou à comparer.
2. Aucune identité n'est demandée, aucune pièce n'est déposée, rien n'est transmis.
3. Le client **peut** ensuite déclarer la prestation anonyme et ce que l'assureur a
   payé, pour que ses rapports en tiennent compte. S'il ne le fait pas, les rapports
   disent qu'ils n'ont pas l'expérience réelle.

## 4. Reprendre les prestations passées

- Même enregistrement anonyme, dans les deux services, **sans identité** : un départ
  réglé n'a pas de dossier à transmettre.
- Saisie une à une, ou **import d'un tableur** (comme le fichier du personnel : colonnes
  en français ou en anglais, contrôles bloquants et avertissements). Cinq ans par
  défaut, plus si le client les a.
- Un départ passé déjà payé est « soldé » à l'enregistrement. Il ne passe par aucun
  statut de suivi.

Ce que les rapports en font :
- l'étude confronte l'**attendu** (les prestations probables de l'échéancier) au
  **réel**, par année ;
- la **rotation observée** est proposée comme hypothèse, motivée et chiffrée. Elle
  n'est jamais appliquée d'office : un changement d'hypothèse reste justifié et figure
  au rapport ;
- le **fonds** est réduit des sommes payées par l'assureur, à leur date ;
- le **cahier des charges** montre l'historique par année, sans identité, avec au moins
  3 départs par ligne (sinon regroupé), et les délais de paiement constatés quand la
  plateforme a suivi les dossiers.

## 5. Motifs

- `retraite` : ouvre droit à l'IFC.
- `demission`, `licenciement`, `deces`, `autre` : pas d'IFC au titre du régime. Ces
  départs sont enregistrés, sans identité, parce qu'ils **mesurent la rotation**
  réelle, et ne sont jamais transmis à un assureur.
- Un salarié parti en retraite **avant** la date d'évaluation n'est plus dans
  l'engagement. Un matricule déclaré parti mais encore présent dans le fichier suivant
  est signalé.

## 6. Invariants

1. **Le service est lu, jamais supposé** : pas de contrat en courtage, pas de collecte
   d'identité.
2. **Aucune identité hors du courtage**, et même là, aucune hors de la table
   `beneficiaires`.
3. **Une prestation est une écriture** : une correction ajoute une ligne qui annule la
   précédente et la cite, jamais une modification.
4. **La plateforme ne touche jamais l'argent** : elle transmet une demande et enregistre
   un paiement déclaré ou constaté.
5. **Dû ≠ versé est permis** et toujours montré.

## 7. Décisions à confirmer

Mes propositions tiennent tant que vous ne dites pas autre chose :
- en courtage, la DRH déclare et le conseiller vérifie avant transmission ; le
  conseiller peut saisir l'historique au nom de l'entreprise ;
- identité effacée 12 mois après le paiement ;
- historique de 5 ans par défaut, saisi une à une ou importé ;
- départs hors retraite enregistrés sans identité.
