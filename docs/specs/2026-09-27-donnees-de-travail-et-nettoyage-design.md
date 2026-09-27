# Preuves, décisions, données de travail : ce qui se modifie, ce qui se supprime, ce qui se nettoie

*Conception, 27/09/2026, décidée avec le porteur du projet après l'audit des pages.*

## Le constat

« On n'efface rien, on ajoute une correction » avait été appliqué partout, y compris à des données de travail qui
n'en demandent pas : fichiers du personnel empilés pour toujours, équipe sans modification ni retrait, contrats et
conditions saisis par erreur impossibles à retirer. La plateforme sert à souscrire une assurance IFC, pas à gérer le
personnel : garder moins de données personnelles est plus sûr, moins coûteux, et c'est ce qu'attend la loi.

## Trois natures de données

| Nature | Exemples | Règle |
|---|---|---|
| **Preuves** | sceaux, journal | immuables ; un numéro se vérifie toujours |
| **Décisions** | version adoptée, étude émise, cahier, contrat, conditions | ne se réécrivent pas ; se suppriment tant que rien ne les cite |
| **Données de travail** | fichiers du personnel, brouillons, membres de l'équipe | libres : modifier, dupliquer, supprimer, nettoyer |

## Un menu ⋮ partout

`composants/MenuActions` : ouvrir ou télécharger, modifier, dupliquer, l'acte propre, supprimer (en dernier, en
rouge). Une action impossible reste visible, grisée, avec sa raison. Posé sur : versions de régime, membres de
l'équipe, fichiers du personnel (télécharger, alléger, supprimer), études, conditions de rémunération, contrats.

## L'équipe

Des **droits** (administrateur de l'entreprise, contributeur, lecture seule, conseiller) et une **fonction** libre.
Le conseiller gère tout le monde, l'administrateur de l'entreprise ses collègues ; côté client, le conseiller
apparaît à part. Le dernier administrateur et le dernier conseiller restent ; le numéro, identité de connexion, ne se
modifie pas. Migration `0018_equipe`, `services/equipe.py`.

## Supprimer ce que rien ne cite

Migration `0019_suppressions` : fichiers, conditions et contrats se suppriment ; les clés étrangères retiennent ce qui
est cité, le service le dit avant (`raison_de_garder`, `usages`). Un fichier cité par une étude émise s'allège (lignes
vidées, empreinte gardée).

## Nettoyer le dossier

Migration `0020_nettoyage`, `services/nettoyage.py`, en trois temps :
1. **l'archive** (ZIP) : documents scellés, études émises en Excel, sommaire des numéros ;
2. **le choix** : personnel (alléger ou supprimer), brouillons, études émises non citées par un cahier ;
3. **la confirmation** écrite (« NETTOYER »).

Une étude émise ne se supprime que par ce nettoyage, qui le signale à la base (`app.nettoyage`) ; un DELETE ordinaire
reste refusé. Les sceaux et le journal restent : la vérification publique ne dépend que d'eux. Le cycle de vie du
dossier fait la même chose, d'office, à l'archivage.

## À valider

La durée pendant laquelle l'entreprise doit conserver le rapport qui justifie sa provision (10 ans en zone OHADA)
est son obligation : l'archive la lui remet ; la plateforme n'a pas à garder le document à sa place.
