# Le régime IFC de l'entreprise, et la plateforme comme compagnon

**Statut :** proposition, à valider · **Date :** 2026-09-26
**Prolonge :** `2026-09-26-plateforme-et-etude-ifc-design.md` (§7 bis, barème d'entreprise).

## 1. Le constat

1. **La « convention » que l'entreprise applique est SON régime IFC** : un
   accord d'entreprise, un règlement, des clauses de contrats, un usage, ou
   simplement la convention collective de sa branche. La convention collective
   n'en est que le **plancher légal**.
2. **Ces régimes existent déjà**, rédigés par d'autres, souvent incomplets. La
   plateforme les **prend tels quels** : elle les lit, les analyse, conseille,
   puis chiffre et tarifie. Elle aide aussi à en construire un quand il n'y en
   a pas.
3. **L'entreprise est souveraine.** Elle adopte son régime d'un seul acte ; la
   plateforme enregistre, ne soumet à aucune approbation interne.
4. **La valeur ajoutée propre à l'assureur**, aujourd'hui, se ramène à quatre
   choses : le **rendement financier** du fonds (taux garanti, participation
   aux bénéfices), la **gestion des sinistres** (le paiement des prestations),
   le **calcul actuariel** et le **reporting**.
5. **La plateforme est le compagnon du processus IFC**, de bout en bout : de
   la lecture du régime au paiement du dernier départ.

## 2. La thèse : dégrouper l'offre de l'assureur

Des quatre apports de l'assureur, deux ne tiennent qu'à lui : **le rendement
et la garantie** (il porte le fonds et son taux) et **le paiement des
sinistres**. Les deux autres, **l'actuariat et le reporting**, la plateforme
les fait de façon neutre, identique d'un assureur à l'autre, et c'est ce qui
rend les offres comparables.

Conséquences :
- L'appel d'offres demande aux assureurs de chiffrer ce qu'eux seuls
  apportent : frais sur cotisations, frais sur encours, taux garanti,
  participation aux bénéfices (taux et historique), délai de paiement d'une
  prestation, conditions de transfert. Et s'ils acceptent l'étude de la
  plateforme comme base, leurs frais de gestion doivent en tenir compte.
- Le client garde ses études, son historique et son reporting en changeant
  d'assureur : c'est ce qui rend le changement possible.
- L'assureur y gagne des dossiers propres et un client informé ; il perd
  l'opacité, qui était sa marge.

## 3. Le processus IFC, étape par étape

| Étape | Ce que fait l'entreprise | Ce que fait la plateforme | Ce que fait l'assureur |
|---|---|---|---|
| **1. Lire l'existant** | dépose ses textes (accord, règlement, contrats) et, s'il existe, son contrat d'assurance | transcrit le régime en règles, relève les ambiguïtés | — |
| **2. Analyser** | — | légalité face au plancher, nature, pièges, coût (§5) | — |
| **3. Concevoir ou corriger** | choisit, modifie | simule chaque variante sur le vrai fichier (§6) | — |
| **4. Adopter** | adopte, d'un seul acte | fige la version, la date, le document | — |
| **5. Évaluer** | transmet son fichier chaque année | étude, rapport scellé (livré) | — |
| **6. Financer et tarifer** | choisit provision interne ou externalisation | calcule la cotisation initiale et annuelle, un plan de financement (§7) | — |
| **7. Placer** | choisit son assureur | cahier des charges, comparaison des offres en coût total (§7) | cote, souscrit, porte le fonds |
| **8. Faire vivre** | déclare les entrées et sorties, les départs | recensement annuel, rapprochement du fonds, reporting comptable (§8) | sert le rendement |
| **9. Sinistre** | déclare le départ, verse l'indemnité | recalcule le dû au régime et au plancher, monte le dossier (§9) | rembourse |
| **10. Changer** | décide | chiffre le coût de sortie, organise le transfert | transfère le fonds |

## 4. Le régime : ce qu'il faut savoir exprimer

Un régime est une suite de **versions** (chacune avec sa date d'effet et son
document source), et chaque version a une ou plusieurs **catégories**.

Par catégorie :
- **qui** : la catégorie de personnel, telle que l'entreprise la nomme
  (cadres, agents de maîtrise, employés, ouvriers…), et la **convention
  plancher** qui s'y applique ;
- **le barème** : tranches, paliers, ou mois par année (formats existants) ;
- **les conditions** : ancienneté minimale ouvrant droit, plafond en mois,
  arrondi de l'ancienneté (années entières, mois), prorata de l'année entamée ;
- **la base de salaire** : dernier salaire, moyenne des 12 derniers mois, avec
  ou sans primes ; et, pour le commerce camerounais 2024, la promotion de
  catégorie deux ans avant le départ ;
- **les événements couverts** : retraite ; départ anticipé ; licenciement
  économique ; décès en activité. La première version du moteur n'évalue que
  la retraite et **dit** quand d'autres événements sont couverts mais non
  évalués.

Le fichier du personnel reçoit une colonne **catégorie**. Une catégorie du
fichier que le régime ne connaît pas est bloquante.

## 5. L'analyse : légalité, nature, pièges, coût

Chaque constat a un niveau — **bloque | avertit | informe** — et une source.
Le contenu juridique est `a_valider` tant qu'aucun juriste ne l'a relu
(décision du 2026-09-26 : pas de partenaire juridique pour l'instant) ; la
plateforme le dit : c'est une information, pas un avis juridique.

**Prendre tels quels** change une règle livrée hier. Un régime moins
favorable que le plancher n'est plus refusé à l'enregistrement : il est
enregistré tel quel, signalé comme **non conforme**, et **évalué au plus
favorable des deux, ancienneté par ancienneté**, parce que le salarié a
toujours droit au plancher. La dette calculée est donc la dette réelle ; le
rapport dit la non-conformité et son coût. (Modification de `baremes.proposer`
et de `comparer_baremes`, qui deviennent un constat et un `max`.)

Catalogue initial, à compléter et à faire relire :

| Constat | Niveau |
|---|---|
| sous le plancher à certaines anciennetés (lesquelles, pour qui) | bloque l'adoption tant que l'entreprise ne l'a pas vu ; évalué au plancher |
| condition plus stricte que la convention (ancienneté minimale, plafond) | bloque idem |
| base de salaire non définie, arrondi non défini | avertit : l'étude retient l'hypothèse prudente et le dit |
| catégories sans critère objectif, ou régime qui profite surtout aux dirigeants | avertit : risques de discrimination, fiscal, d'abus de biens sociaux |
| décision de la direction appliquée plusieurs fois | informe : elle devient un usage, donc une obligation |
| dette de passé créée à l'adoption (coût immédiat) | informe, chiffré |
| engagement à prestations définies : à provisionner (SYSCOHADA révisé, IAS 19) | informe |
| déductibilité fiscale des cotisations : selon le pays et les conditions du contrat | informe, `a_valider` |
| événements couverts non évalués | avertit |

## 6. Simuler avant d'adopter

Sur le fichier réel de l'entreprise, la plateforme compare côte à côte : le
plancher seul, le régime en vigueur, chaque variante envisagée. Pour chacune :
dette, charge annuelle, cotisation initiale, échéancier des départs, et qui en
profite (répartition par catégorie, part des cinq premiers bénéficiaires). Le
moteur sait déjà faire l'essentiel ; il faut les catégories et les
comparaisons.

## 7. Financer et tarifer

Ce que la plateforme appelle **tarifer** : calculer ce que le régime coûte à
l'entreprise, et ce que chaque offre d'assureur lui coûtera. Elle ne fixe pas
la prime de l'assureur.

- **Cotisation initiale** (le passé : dette moins fonds existant) et
  **cotisation annuelle** (la charge de l'exercice), avec un **plan
  d'amortissement** de l'initiale sur N années si l'entreprise le choisit.
- **Projection du fonds** sous les conditions de chaque offre : versements,
  frais sur cotisations, frais sur encours, taux garanti, participation aux
  bénéfices, et **décaissements aux dates des départs** de l'échéancier.
  C'est là que se voit le vrai risque : le contrat Ariane ne rembourse que
  « dans la limite des fonds disponibles ». Un fonds suffisant en moyenne peut
  manquer l'année de trois départs.
- **Le critère de comparaison** : le coût total actualisé sur l'horizon (10
  ans par défaut) et les années où le fonds ne couvrirait pas les départs.
- **Provision interne contre externalisation** : la même projection sans
  assureur, pour que la décision d'externaliser soit chiffrée elle aussi.

## 8. Faire vivre le régime

- **Recensement annuel** : rappel avant la clôture, dépôt, rapprochement avec
  l'année précédente (entrées, sorties, départs, hausses de salaire
  anormales).
- **Reporting comptable** : la note annexe d'une année sur l'autre (dette
  d'ouverture, coût des services, intérêt, prestations payées, écarts
  actuariels, dette de clôture). Il faut deux études consécutives ; c'est le
  « reporting » de l'assureur, fait de façon neutre.
- **Rapprochement du fonds** avec le relevé de l'assureur.

## 9. Le sinistre (spécification à part, avec le placement)

Rappel de la règle : l'identité du salarié n'entre qu'ici. À la déclaration
d'un départ, la plateforme recalcule ce qui est dû au plancher et au régime,
montre ce que l'entreprise décide de verser, et ce que le contrat fait
rembourser par le fonds (montant du régime, ou montant versé plafonné).

## 10. Ce qui change dans le modèle

- `baremes_entreprise` devient **`regimes`** (versions, document, statut
  `analyse` → `adopte`, adoption par un seul acte de l'entreprise) et
  **`regimes_categories`** (convention plancher, barème, conditions, base de
  salaire, événements).
- `fichiers_personnel` : colonne catégorie ; contrôle des catégories.
- Le référentiel : chaque convention porte aussi ses **règles** (conditions,
  plafonds, base) et ses **notes** sourcées, `a_valider`.
- Le moteur : conditions, plafond, `max(régime, plancher)` par ancienneté,
  évaluation par catégorie.
- Les constats d'analyse : un module pur qui rend une table de constats
  `bloque | avertit | informe`, sans base ni date du jour, comme le moteur.

## 11. Découpage proposé (avant l'interface)

| Tâche | Contenu |
|---|---|
| R1 | Catégories dans le fichier ; moteur par catégorie ; conditions et plafond ; `max(régime, plancher)` |
| R2 | Le régime : versions, catégories, document, adoption ; migration depuis le barème d'entreprise |
| R3 | L'analyse : catalogue de constats, contenu juridique `a_valider` et sourcé |
| R4 | La simulation : plancher, régime, variantes, répartition |
| R5 | Le financement : cotisations, plan d'amortissement, projection du fonds, conditions d'offres |
| R6 | La fiche régime : le cahier des charges exportable pour les assureurs |

L'interface (tâche 7 du premier plan) vient ensuite et couvre le parcours
complet : lire → analyser → simuler → adopter → évaluer → financer.

## 12. Questions ouvertes

1. L'étude peut-elle être **émise** avec un régime non conforme ? Proposition :
   oui, évaluée au plancher là où il est plus favorable, la non-conformité en
   tête du rapport — l'entreprise est souveraine, le rapport dit la vérité.
2. **Base de salaire** quand le fichier ne donne que le salaire courant et que
   le régime dit « moyenne des 12 mois » : retenir le salaire courant et le
   dire, ou demander la colonne ?
3. **Horizon et taux** de la projection du fonds : 10 ans et le taux garanti
   de chaque offre, ou des scénarios de participation aux bénéfices ?
4. **Lecture des textes existants** : saisie guidée par le conseiller d'abord,
   extraction assistée par un modèle de langue ensuite (toujours relue) ?
