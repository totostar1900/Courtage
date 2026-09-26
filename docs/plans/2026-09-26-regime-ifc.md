# Plan — le régime IFC de l'entreprise

Spécification : `docs/specs/2026-09-26-regime-ifc-compagnon-design.md`.
Méthode : tests d'abord, suite verte avant chaque commit, un commit par tâche.
Ce plan passe AVANT les tâches 7 à 9 du plan de l'étude IFC (interface,
authentification, déploiement) : l'interface couvrira le parcours complet.

## R1 — Catégories et moteur par catégorie

- [ ] Fichier du personnel : colonne catégorie reconnue (FR/EN), gardée.
- [ ] Moteur : des règles par catégorie — barème, plancher (convention),
      ancienneté minimale, plafond en mois, arrondi de l'ancienneté (années
      entières | mois).
- [ ] Au plus favorable du barème et du plancher, ancienneté par ancienneté ;
      chaque ligne dit si le plancher a joué.
- [ ] Totaux par catégorie ; une catégorie sans règle est refusée.
- [ ] Sans règles, le moteur se comporte exactement comme avant (les
      références AZITO ne bougent pas).

Commit : `feat(actuariat): règles par catégorie, conditions et plancher`

## R2 — Le régime

- [ ] Migration : `regimes` (versions, document source, statut `analyse` →
      `adopte`, adoption par un seul acte de l'entreprise) et
      `regimes_categories` (convention plancher, barème, conditions, base de
      salaire, événements couverts) ; reprise des barèmes d'entreprise.
- [ ] Un régime sous le plancher est ENREGISTRÉ (plus refusé) et signalé.
- [ ] L'étude s'appuie sur une version du régime ; catégories du fichier
      contrôlées ; base « moyenne 12 mois » signalée ; événements non évalués
      signalés ; non-conformité en tête du rapport.

## R3 — L'analyse

- [ ] Module pur de constats `bloque | avertit | informe` (spec §5), chacun
      sourcé, le contenu juridique `a_valider`.
- [ ] Coût de la non-conformité, dette de passé à l'adoption, concentration
      sur les dirigeants, usage, provisionnement, déductibilité.

## R4 — La simulation

- [ ] Plancher seul, régime en vigueur, variantes : dette, charge,
      cotisation initiale, échéancier, répartition par catégorie, part des
      cinq premiers bénéficiaires.

## R5 — Le financement

- [ ] Cotisation initiale et annuelle ; plan d'amortissement sur N années.
- [ ] Projection du fonds paramétrable (horizon, taux garanti, frais sur
      cotisations et sur encours, participation aux bénéfices) sous plusieurs
      scénarios ; décaissements aux dates des départs ; années de découvert.
- [ ] Offres d'assureurs comme jeux de conditions ; coût total actualisé ;
      provision interne comme offre de référence.

## R6 — La fiche régime

- [ ] Le cahier des charges exportable (régime, population agrégée, étude,
      conditions demandées), scellé comme le rapport.
