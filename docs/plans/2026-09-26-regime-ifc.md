# Plan — le régime IFC de l'entreprise

Spécification : `docs/specs/2026-09-26-regime-ifc-compagnon-design.md`.
Méthode : tests d'abord, suite verte avant chaque commit, un commit par tâche.
Ce plan passe AVANT les tâches 7 à 9 du plan de l'étude IFC (interface,
authentification, déploiement) : l'interface couvrira le parcours complet.

## R1 — Catégories et moteur par catégorie

- [x] Fichier du personnel : colonne catégorie reconnue (FR/EN), gardée.
- [x] Moteur : des règles par catégorie — barème, plancher (convention),
      ancienneté minimale, plafond en mois, arrondi de l'ancienneté (années
      entières | mois).
- [x] Au plus favorable du barème et du plancher, ancienneté par ancienneté ;
      chaque ligne dit si le plancher a joué.
- [x] Totaux par catégorie ; une catégorie sans règle est refusée.
- [x] Sans règles, le moteur se comporte exactement comme avant (les
      références AZITO ne bougent pas).

Moteur `ifc-1.1.0` : `Regles` (barème, plancher, ancienneté minimale,
plafond, arrondi), `mois_dus`, `evaluer(..., regles=)` avec `"*"` pour les
autres catégories, `Resultat.par_categorie`, `Ligne.mois` et
`Ligne.plancher_applique`.

Commit : `feat(actuariat): règles par catégorie, conditions et plancher`

## R2 — Le régime

- [x] Migration `0005_regimes` : `regimes`, `regimes_versions` (numéro, date
      d'effet, fondement, document, statut `analyse` → `adoptee`, adoption par
      un seul acte, constats figés à l'adoption) et `regimes_categories`
      (convention plancher, barème, ancienneté minimale, plafond, arrondi,
      base de salaire, primes, événements) ; immuables une fois adoptées.
      La version en vigueur à une date est la dernière adoptée qui la précède.
- [x] Reprise des barèmes d'entreprise (validé → adopté, proposé → analyse,
      catégorie « * ») ; la table reste lisible pour les études qui les citent,
      l'application n'y écrit plus. Vérifiée sur une base jetable.
- [x] Un régime sous le plancher est ENREGISTRÉ et signalé
      (`sous_le_plancher`, anciennetés en cause) ; l'adoption demande
      `accepte_non_conformite` ; seule l'entreprise (`admin_client`) adopte.
- [x] L'étude s'appuie sur une version (`regime_version_id`) : règles par
      catégorie avec la convention en vigueur à la date d'évaluation pour
      plancher ; catégorie du fichier sans règle → 422 `categories_inconnues` ;
      totaux par catégorie et totaux de la seule convention ; avertissements
      `non_conformite`, `base_salaire_approchee`, `evenements_non_evalues` ;
      motifs `regime_non_adopte`, `regime_hors_vigueur`.
- [x] Rapport : non-conformité en tête, régime et coût au-delà de la
      convention, détail par catégorie.

Commit : `feat(regime): le régime IFC de l'entreprise, par version et par catégorie`

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
