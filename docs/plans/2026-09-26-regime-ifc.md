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

- [x] Module pur `courtage.analyse` : `analyser(Contexte) -> [Constat]`,
      triés `bloque | avertit | informe`. Deux sortes : les CALCULS, garantis
      (`statut_contenu = calcul`), et les NOTES, sourcées et `a_valider`.
- [x] Notes juridiques en données (`referentiel/donnees/notes_juridiques.json`) :
      provisionnement, usage, déductibilité CI et CM, égalité de traitement,
      abus de biens sociaux — chacune citée, aucune relue par un juriste.
- [x] Calculs : coût de la non-conformité (le texte lu à la lettre contre la
      dette réelle), dette de passé créée par l'adoption (face à la version en
      vigueur la veille, sinon à la seule convention), concentration de ce que
      le régime ajoute sur le décile des salaires les plus élevés (alerte
      au-delà de 15 points de plus que leur part de la dette conventionnelle).
- [x] `GET /organisations/{id}/regimes/versions/{vid}/analyse` : légalité et
      nature sans fichier ; les coûts avec `fichier_id`.

Commit : `feat(analyse): constats sourcés sur un régime IFC`

## R4 — La simulation

- [x] `POST /organisations/{id}/simulations` : un calcul, rien d'enregistré
      (ni étude, ni version, ni journal) ; ouvert à tout membre, expert-comptable
      compris.
- [x] Toujours « Convention seule » en premier, puis jusqu'à 6 variantes :
      une version de régime (adoptée ou non) OU des catégories saisies.
- [x] Pour chacune : dette, charge annuelle, cotisation initiale (dette moins
      fonds), écart à la convention, échéancier, totaux par catégorie, part
      des cinq premiers bénéficiaires, concentration sur les mieux payés,
      constats de légalité.
- [x] Une variante qui ne couvre pas le personnel rend son erreur ; les autres
      sont calculées. Hypothèses modifiables sans justification : une
      simulation n'engage personne.

Commit : `feat(simulation): convention, régime et variantes côte à côte`

## R5 — Le financement

- [x] Module pur `courtage.financement` : `projeter(engagement, offres,
      scénarios, paramètres)`. Une année : cotisation (charge indexée +
      annuité d'amortissement du déficit sur N années), frais sur cotisations,
      intérêts au taux garanti plus la participation aux bénéfices au-delà,
      frais sur encours, prestations probables payées PAR LE FONDS dans la
      limite de ce qu'il contient ; le reste est un découvert payé par
      l'entreprise.
- [x] Horizon, taux d'actualisation, croissance, amortissement paramétrables ;
      scénarios de rendement paramétrables (par défaut prudent 3,5 %, central
      5 %, favorable 6,5 %) ; offres bornées (frais ≤ 20 %, PB entre 0 et 1).
- [x] Par offre et par scénario : l'année par année, le coût total, les frais,
      les années de découvert, le fonds final, le coût net actualisé (critère
      de comparaison) et la couverture des départs restants à l'horizon.
      Classement sur le scénario de référence.
- [x] La provision interne est toujours comparée (ajoutée si absente).
- [x] L'échéancier des études donne les prestations probables par année ;
      `POST /organisations/{id}/etudes/{eid}/financement`, rien d'enregistré.

Reste pour le placement : enregistrer les offres reçues des assureurs.

Commit : `feat(financement): projection du fonds, scénarios et offres comparées`

## R6 — La fiche régime

- [x] Module pur `courtage.fiche` : agrégats publiables. Case de moins de 3
      personnes masquée (« <3 »), masse salariale d'une catégorie masquée
      retenue ; échéancier par périodes de cinq ans, une période de moins de
      3 départs fusionnée avec la suivante. Aucun matricule, aucune date,
      aucun salaire individuel.
- [x] Migration `0006_fiches_regime` : la fiche (étude émise, version du
      régime, conditions, contenu, empreinte), en ajout seul ; `documents`
      accueille une étude OU une fiche.
- [x] Contenu : organisation, régime (ou convention seule), engagement
      (numéro du rapport scellé, dette, charge, VAPF, fonds, hypothèses,
      sensibilités), population agrégée, départs, conditions demandées,
      date limite, grille de réponse alignée sur les offres du financement.
- [x] Émise par le conseiller, d'un seul acte scellé et rendu ; lue par le
      client ; vérifiable publiquement (nature `fiche_regime`).
- [x] Le scellement est commun aux deux documents (`sceller_document`).

Commit : `feat(fiche): le cahier des charges scellé pour les assureurs`
