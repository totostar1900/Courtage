# Plateforme de courtage — socle et étude IFC en ligne

**Statut :** proposition, à valider · **Date :** 2026-09-26
**Contexte :** `docs/contexte/` (étude AZITO, note de stratégie).

## 1. Objet

Construire le socle d'un courtier d'assurance digital pour le Cameroun et la
zone CIMA, et y livrer un premier produit vendable avant l'agrément de
courtier : **l'étude actuarielle des indemnités de fin de carrière (IFC)**.

Une entreprise dépose le fichier de son personnel, la plateforme le contrôle,
calcule la dette actuarielle, la charge de l'exercice et la cotisation
d'ajustement, un conseiller relit, et l'entreprise reçoit un rapport scellé
qu'elle peut transmettre à son expert-comptable ou à son commissaire aux
comptes.

## 2. Principes — tenus par le code, pas seulement par l'interface

1. **La plateforme conseille et trace ; elle ne porte aucun risque.** Les
   primes vont de l'entreprise à l'assureur. Quand l'encaissement arrivera, il
   se fera directement sur le compte de l'assureur ; la plateforme garde la
   trace.
2. **Montants en F CFA entiers.** Tout montant stocké ou affiché est un entier
   (`int`, `BIGINT`). Les calculs intermédiaires du moteur sont en flottant ;
   l'arrondi à l'entier se fait une fois, à la sortie du moteur.
3. **Une étude émise est immuable.** Elle garde ses entrées (le fichier tel que
   lu), ses hypothèses, la version du référentiel et du moteur, ses résultats et
   leur empreinte. Une correction est une nouvelle étude qui cite la
   précédente. Rien n'est mis à jour en place.
4. **Toute hypothèse vient du référentiel, datée et versionnée.** Convention,
   table de mortalité, turnover, taux : une étude référence une version. Un
   écart par rapport au référentiel est permis, mais il est enregistré avec sa
   justification et apparaît dans le rapport.
5. **Une convention non validée ne sort pas.** Chaque barème du référentiel a
   un statut (`a_valider` | `valide`). Le moteur calcule avec l'un comme avec
   l'autre, mais une étude ne peut être **émise** qu'avec un barème `valide`.
   C'est la leçon d'AZITO : le texte d'un pays dans le rapport d'un autre.
6. **Contrôles bloquants avant tout calcul émis** (§6) : pays de la convention
   = pays de l'entreprise, date d'évaluation = une clôture, fichier récent,
   lignes complètes.
7. **Isolation par client.** Chaque table métier porte `organisation_id` ;
   PostgreSQL filtre par RLS sur l'organisation de la requête. Le rôle
   applicatif n'est pas propriétaire des tables.
8. **Minimisation des données.** Le fichier du personnel n'a besoin d'aucun
   nom : matricule, sexe, date de naissance, date d'embauche, salaire. Une
   colonne de nom est ignorée à la lecture et n'est jamais stockée. Ce
   recensement reste une donnée personnelle (dates et salaire suffisent souvent
   à reconnaître quelqu'un dans une petite entreprise) et se protège comme tel.
9. **L'évaluation ne demande aucune identité ; l'identité n'entre qu'avec un
   sinistre** (ajouté le 2026-09-26), dans un dossier séparé, aux accès plus
   étroits, aux champs chiffrés, à la conservation limitée. Spécification des
   sinistres à venir avec le placement.
10. **Une entreprise verse au moins sa convention.** Elle peut verser plus ;
   si elle le fait habituellement (accord, contrats, usage constant), sa dette
   réelle est plus lourde que la dette conventionnelle (obligation implicite,
   IAS 19) et l'étude l'évalue avec SON barème (§7 bis).

### Qui est qui dans un contrat IFC

Le **souscripteur**, l'**assuré** et le **bénéficiaire** du contrat sont
l'entreprise : l'engagement couvert est le sien, et l'assureur lui rembourse
les indemnités qu'elle verse, dans la limite du fonds. Le salarié n'a pas de
lien avec l'assureur : il est créancier de son employeur. La plateforme ne
traite donc qu'avec l'entreprise.

Au sinistre (départ en retraite), l'entreprise déclare et verse ; sa latitude
ne joue que vers le haut. Le contrat devra dire si le fonds rembourse le
montant conventionnel ou le montant versé (plafonné) : c'est une donnée de la
police, à modéliser avec le placement. La plateforme recalculera alors le
montant conventionnel au jour du départ et montrera l'écart avec le versement.

## 3. Pile technique

| Couche | Choix | Raison |
|---|---|---|
| API | Python 3.11+, FastAPI, Pydantic 2 | le moteur actuariel est en Python et lisible par un actuaire |
| Base | PostgreSQL 16, SQLAlchemy 2, Alembic | RLS, JSONB pour les résultats, migrations versionnées |
| Fichiers | openpyxl (xlsx), csv | lecture des fichiers de paie |
| Rapport | HTML → PDF (WeasyPrint) | un gabarit, pas de mise en page à la main |
| Interface | React + TypeScript + Vite | |
| Tests | pytest ; Vitest côté interface | |

**Ouvert :** le fournisseur d'authentification (géré, avec connexion par
téléphone, ou intégré). Décision à la tâche 8 du plan.

## 4. Rôles

| Rôle | Portée |
|---|---|
| `admin_client` | son organisation : dépose, lance, lit, partage |
| `lecteur_client` | son organisation, en lecture (expert-comptable, CAC) |
| `conseiller` | les organisations qui lui sont confiées : relit, émet |
| `admin_plateforme` | le référentiel ; aucun accès aux données des clients par défaut |

Une étude est **émise** par un conseiller, jamais par le client seul : c'est le
conseil appuyé, et c'est ce qui engage la responsabilité de la plateforme.

## 5. Modèle de données (tranche IFC)

```
organisations        id, nom, pays (CM, CI, SN, GA, CG, TD, CF, GQ), secteur
utilisateurs         id, téléphone, e-mail
adhesions            utilisateur_id, organisation_id, role
referentiel_versions id, publiée_le, note          -- un instantané complet
conventions          id, version_id, pays, code, libellé, statut, bareme (JSONB), source
tables_mortalite     id, version_id, code (CIMA_H, CIMA_F…), lx (JSONB)
fichiers_personnel   id, organisation_id, déposé_le, nom_fichier, empreinte, lignes (JSONB), anomalies (JSONB)
etudes               id, organisation_id, fichier_id, référentiel_version_id,
                     convention_id, hypothèses (JSONB), date_evaluation, fonds_disponible,
                     version_moteur, statut (brouillon | emise), résultats (JSONB),
                     empreinte, emise_par, emise_le, remplace_etude_id
documents_scelles    numéro (RL-XXXX-XXXX), etude_id, empreinte, sceau, fichier
journal              qui, quoi, cible, quand, détails            -- en ajout seul
```

Les lignes du fichier sont gardées telles que lues (JSONB) : l'étude doit
pouvoir être refaite à l'identique dans dix ans.

## 6. Contrôles du fichier et de l'étude

**Bloquants** (l'étude ne peut pas être émise) :
- ligne sans matricule, date de naissance ou date d'embauche ;
- embauche postérieure à la date d'évaluation ; âge à l'embauche < 14 ans ;
- salaire nul ou négatif ;
- convention d'un autre pays que l'organisation, ou convention `a_valider` ;
- date d'évaluation qui n'est pas une fin de mois ;
- fichier de plus de 12 mois à la date d'évaluation.

**Avertissements** (affichés, repris dans le rapport) :
- salarié ayant dépassé l'âge de retraite (son IFC est due, pas future) ;
- un salarié pèse plus de 20 % de l'engagement ;
- dates au 1er janvier en série (souvent des dates estimées) ;
- écart de plus de 25 % avec l'étude précédente de la même organisation.

## 7. Le moteur

Méthode prospective, salarié par salarié, reprise d'Ariane IFC (`docs/contexte/`) :

```
âge, ancienneté       en années, DATEDIF(Y) + jours depuis l'anniversaire / 365
ancienneté totale M   ancienneté à la date de retraite
salaire final         salaire × ((1+inflation)(1+croissance))^(années restantes)
IFC                   barème(ancienneté totale arrondie) × salaire final mensuel
VAPF                  IFC × p_survie × p_présence × (1+i)^-(années restantes)
dette                 VAPF × ancienneté acquise / M
charge                VAPF / M                           (si âge < retraite)
cotisation            max(dette + charge − fonds, 0) × (1 + frais)
```

Le barème est une **donnée**, de deux formes :
- `tranches_cumulatives` : un pourcentage de mois par année, par tranche
  (Côte d'Ivoire : 30 % jusqu'à 5 ans, 35 % de 6 à 10, 40 % au-delà) ;
- `paliers` : un nombre de mois à partir d'une ancienneté, linéaire sous le
  premier palier (APB Madagascar).

Le moteur est une fonction pure : pas de base, pas de date du jour. Il rend le
détail par salarié et les totaux, arrondis à l'entier.

### 7 bis. Barème d'entreprise (ajouté le 2026-09-26)

Un barème propre à une organisation, qui AMÉLIORE une convention précise :
libellé, fondement (`accord_entreprise` | `contrat_travail` | `usage` |
`decision_direction`), référence du document, dates de vigueur, barème (même
format que le référentiel). Proposé par le client ou le conseiller, validé par
le conseiller ; validé, il ne bouge plus.

Il ne peut jamais donner moins que la convention : vérifié à la proposition
(refus, avec les anciennetés en cause) et à chaque étude contre la version de
la convention en vigueur à la date d'évaluation, parce que le minimum légal
monte (commerce camerounais au 16/01/2024) : un accord dépassé par une
révision bloque l'émission. Une étude avec barème d'entreprise donne aussi
ses totaux conventionnels : ce que l'accord coûte au-delà de la convention.

**Tests de référence** : le cas AZITO au 31/12/2019 doit redonner la dette du
classeur Ariane (60 976 604 F, convention CI) et celle du rapport 2023
(41 404 223 F, barème APB) à 0,01 % près.

## 8. Parcours

1. L'entreprise dépose son fichier (xlsx ou csv) → rapport de contrôle.
2. Elle corrige et redépose, ou continue avec les avertissements.
3. Le conseiller choisit la date d'évaluation, le fonds disponible, la version
   du référentiel ; les hypothèses sont pré-remplies.
4. Calcul → brouillon : résultats, échéancier, sensibilités, comparaison avec
   l'étude précédente.
5. Le conseiller émet → rapport PDF scellé, vérifiable en ligne par son numéro.
6. L'entreprise partage l'étude avec son expert-comptable (`lecteur_client`).

## 9. Hors périmètre de cette tranche

Appels d'offres, assureurs, contrats, santé, auto, voyage, paiement,
WhatsApp. Chacun aura sa spécification.

## 10. Questions ouvertes

1. ~~**Barème camerounais.**~~ **Réglé le 2026-09-26.** Le barème ivoirien
   n'est PAS proche du camerounais : sur les salariés AZITO, le commerce
   camerounais 2024 donne une dette 67 % plus élevée. Le référentiel porte le
   commerce (2012, puis 2024 : 45/50/65/75/80 % par année selon la tranche) et
   les banques (2021 : 25/35/45/55/65 % ; 2024 à valider), avec leurs sources.
   Les textes primaires n'ont pas pu être lus (accès bloqué depuis
   l'environnement de développement) ; les taux reposent sur des sources
   secondaires concordantes, ce que dit le champ `verification` de chaque
   barème. Reste à relire les textes : la lecture « chaque année au taux de sa
   tranche », et la promotion de catégorie deux ans avant la retraite (commerce
   2024), non modélisée.
2. **Table de mortalité.** CIMA F pour tous (prudent, comme Ariane) ou CIMA H /
   CIMA F selon le sexe ? Proposition : selon le sexe quand il est fourni.
3. **Attribution des droits.** Proratisation linéaire (Ariane) ou selon la
   formule du barème (IAS 19 strict) ? Proposition : linéaire par défaut,
   IAS 19 en option pour les clients qui publient en IFRS.
4. **Signature.** Qui signe le rapport : un actuaire qualifié salarié, ou un
   actuaire partenaire ?
5. **Fixture AZITO.** Le cas de test contient les dates et salaires réels de 23
   salariés, sans nom. Dépôt privé ; à remplacer par un jeu synthétique avant
   toute ouverture du code.
