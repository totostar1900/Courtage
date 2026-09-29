# Le cycle annuel — l'engagement se remesure chaque année

Date : 2026-09-29. Couvre l'étape 14 (vie du contrat) de la carte du parcours.

## 1. Pourquoi

Une provision IFC se mesure à une date, et se remesure chaque année, à la même date, pour les comptes. Sans rappel,
la mise à jour du personnel, l'évaluation et le relevé de l'assureur glissent ; la première année ne le montre pas,
toutes les suivantes si.

## 2. Le calendrier, calculé

Le cycle part de la **dernière étude émise** : sa date d'évaluation D fixe la prochaine, **N = D + 1 an** (la même
date, l'année suivante). Rien n'est stocké : chaque étape se lit dans les données.

| Étape | Faite quand | Échéance |
|---|---|---|
| Mettre à jour le personnel | un fichier du personnel daté de N ou après | N + 30 jours |
| Émettre l'évaluation de l'année | une étude émise au N ou après | N + 60 jours |
| Recevoir le relevé annuel de l'assureur | (police en vigueur seulement) un relevé daté de N ou après | N + 45 jours |
| Revoir le contrat avant son anniversaire | (police en vigueur seulement) rien à cocher : un rappel | 60 jours avant l'anniversaire de la police |

Une étape est **faite**, **à venir** (plus de 30 jours avant l'échéance, ou N pas encore atteint), **bientôt** (dans
les 30 jours), ou **en retard**. Quand l'évaluation de N est émise, le cycle passe à N + 1 de lui-même. Sans étude
émise, il n'y a pas encore de cycle : le parcours d'entrée s'en charge.

## 3. Où on le voit

- Le **tableau de bord** : « L'année du dossier », les étapes avec leur échéance et leur état.
- Les **points d'attention** : une étape bientôt due (information), en retard (attention ; grave au-delà de 30 jours
  de retard), avec le rôle qui doit agir. Le retard du personnel et de l'évaluation est déjà dit par les alertes
  existantes (« une nouvelle étude s'impose », « données anciennes ») : le calendrier ne les double pas, il les
  annonce seulement avant l'échéance.

## 4. Les rappels par courriel

La tâche quotidienne (`python -m courtage.purge`) envoie un rappel quand une étape devient **bientôt due**, puis quand
elle est **en retard** : au plus un courriel par étape, par état et par année (`rappels_envoyes`, migration 0029),
aux administrateurs de l'entreprise et aux conseillers selon l'étape, sauf à qui a coupé ses avis. Sans le contenu
du dossier : l'étape, l'échéance, le lien. Ces rappels sont des avis d'échéance, un par étape ; **l'envoi hebdomadaire
des alertes reste suspendu**.
