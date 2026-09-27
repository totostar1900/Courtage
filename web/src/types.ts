// Les formes renvoyées par l'API (courtage/api/routes.py). Seul ce que l'interface lit est typé.

export type Role = "admin_client" | "contributeur_client" | "lecteur_client" | "conseiller";

/** Un membre de l'équipe, tel que l'appelant peut le voir et le gérer. */
export interface Membre {
  id: string; nom: string; email: string | null; telephone: string | null; role: Role; droits: string;
  fonction: string | null; moi: boolean; modifiable: boolean; retirable: boolean; raison_retrait: string | null;
}
export interface Equipe {
  membres: Membre[]; droits_attribuables: { role: Role; libelle: string }[]; fonctions: string[];
}

export interface Moi {
  id: string;
  email: string | null;
  admin_plateforme: boolean;
  organisations: { id: string; nom: string; pays: string; role: Role; etat?: EtatCycle; etat_depuis?: string }[];
}

export interface Anomalie {
  niveau: "bloquant" | "avertissement";
  code: string;
  message: string;
  ligne?: number | null;
  colonne?: string | null;
}

export interface Fichier {
  id: string;
  nom_fichier: string;
  depose_le: string;
  date_donnees: string;
  periodicite: string;
  effectif: number;
  anomalies: Anomalie[];
}

export interface Totaux {
  effectif: number;
  vapf: number;
  dette: number;
  charge: number;
  cotisation_nette?: number;
  cotisation_totale?: number;
}

export interface Annee {
  annee: number;
  effectif: number;
  ifc: number;
  prestations_probables?: number;
  vapf: number;
  /** Absent des études émises avant le découpage par catégorie : leur graphique reste d'un seul tenant. */
  par_categorie?: Record<string, { effectif: number; ifc: number; prestations_probables: number; vapf: number }>;
}

export interface Constat {
  niveau: "bloque" | "avertit" | "informe";
  code: string;
  titre?: string;
  message: string;
  categorie?: string | null;
  chiffres?: Record<string, unknown>;
  details?: Record<string, unknown>;
  sources?: { titre: string; url?: string | null }[];
  statut_contenu?: "calcul" | "valide" | "a_valider";
}

export interface Categorie {
  categorie: string;
  convention_code: string;
  bareme: Bareme;
  anciennete_minimale?: number;
  plafond_mois?: number | null;
  arrondi?: "annees" | "mois";
  base_salaire?: "dernier" | "moyenne_12_mois";
  avec_primes?: boolean;
  evenements?: string[];
}

export interface Bareme {
  forme: "tranches_cumulatives" | "paliers";
  tranches?: { jusqu_a: number | null; mois_par_annee: number }[];
}

export interface Version {
  id: string;
  regime_id: string;
  nom: string;
  numero: number;
  en_vigueur_du: string;
  fondement: string;
  document_reference: string;
  statut: "analyse" | "adoptee";
  /** Pour une version adoptée : depuis quand elle s'applique, et jusqu'à quand. Une information, pas un statut. */
  application?: { a_venir: boolean; depuis: string; remplacee_le: string | null; remplacee_par: number | null;
                  en_cours: boolean } | null;
  adoptee_le?: string | null;
  etudes?: number;
  citations?: { etudes_emises: number; brouillons: { id: string; date_evaluation: string }[]; cahiers: number;
                partages: number; notes: number };
  suppression?: { possible: boolean; reservee_entreprise: boolean; brouillons: number; raison: string | null };
  notes?: { salaries: string | null; assureurs: string | null };
  non_conformite_acceptee: boolean;
  categories: Categorie[];
  constats: Constat[];
}

export interface Regime {
  id: string;
  nom: string;
  versions: Version[];
}

export interface EtudeResume {
  id: string;
  statut: "brouillon" | "emise";
  date_evaluation: string;
  convention_code: string;
  dette: number;
  emise_le: string | null;
}

export interface Etude {
  id: string;
  statut: "brouillon" | "emise";
  fichier_id: string;
  date_evaluation: string;
  convention: { code: string; libelle: string; en_vigueur_du: string; statut: string; verification: string };
  regime: Version | null;
  hypotheses: { valeurs: Record<string, unknown>; ecarts: unknown[]; justification: string | null;
                lues?: HypotheseLue[] };
  fonds_disponible: number;
  totaux: Totaux;
  totaux_convention: Totaux | null;
  par_categorie: Record<string, { effectif: number; dette: number; charge: number }> | null;
  echeancier: Annee[];
  sensibilites: Record<string, { dette: number; charge: number }>;
  anomalies: Anomalie[];
  emission: { possible: boolean; motifs: string[] };
  empreinte: string | null;
  honoraires_ht: number | null;
  emise_le: string | null;
  rapport: { numero: string } | null;
  experience?: Experience | null;
}

export interface Experience {
  etude_precedente: { date_evaluation: string } | null;
  attendu_contre_reel: { annee: number; attendu_retraites: number | null; attendu_prestations: number | null;
    reel_retraites: number; reel_du: number; reel_verse: number }[];
  rotation: { taux: number | null; departs: number; annees: number; effectif: number; taux_hypothese: number;
    credible: boolean; proposition: { taux_turnover: number; justification: string } | null; message: string };
  paiements_du_fonds: { depuis: string | null; montant: number };
}

export interface Conditions {
  en_vigueur_du: string;
  mode: "honoraires" | "commission" | "mixte";
  honoraires_etude_ifc: number;
  honoraires_par_salarie: number;
  commission_bps: number;
  note: string | null;
}

export interface Offre {
  nom: string;
  taux_garanti: number;
  participation_benefices: number;
  frais_sur_cotisations: number;
  frais_sur_encours: number;
  interne?: boolean;
}

export interface ProjectionScenario {
  scenario: string;
  rendement: number;
  cout_total: number;
  cout_net_actualise: number;
  frais_totaux: number;
  fonds_final: number;
  annees_decouvert: number[];
  couverture_des_departs_restants: number | null;
  annees: { annee: number; cotisation: number; prestations: number; decouvert: number; fonds_fin: number }[];
}

export interface Financement {
  plan_amortissement: { deficit_initial: number; annees: number; annuite: number };
  scenario_de_reference: string;
  classement: string[];
  offres: { nom: string; interne: boolean; conditions: Offre; scenarios: ProjectionScenario[] }[];
}

export interface Fiche {
  id: string;
  numero: string;
  etude_id: string;
  date_limite_reponse: string;
  emise_le: string;
}

export interface Contrat {
  id: string;
  en_vigueur_du: string;
  service: "courtage" | "comparaison";
  assureur: string | null;
  numero_police: string | null;
  date_effet_police: string | null;
  mandat_reference: string | null;
  note: string | null;
}

export interface ContratsDossier {
  service: "courtage" | "comparaison";
  en_vigueur: Contrat | null;
  historique: Contrat[];
  constats: Constat[];
}

export type MotifDepart = "retraite" | "demission" | "licenciement" | "deces" | "autre";

export interface CalculPrestation {
  anciennete: number;
  mois: number;
  plancher_applique: boolean;
  source: { type: "regime" | "convention"; libelle: string; convention_code?: string; regime_version_id?: string; categorie?: string } | null;
  raison?: string;
}

export interface Prestation {
  id: string;
  matricule: string;
  categorie: string | null;
  motif: MotifDepart;
  date_naissance: string | null;
  date_embauche: string;
  date_depart: string;
  salaire_mensuel_reference: number;
  du: number;
  calcul: CalculPrestation;
  verse: number | null;
  part_fonds_demandee: number | null;
  part_fonds_payee: number | null;
  payee_le: string | null;
  soldee: boolean;
  origine: "saisie" | "import";
  import_id: string | null;
  note: string | null;
  remplace_id: string | null;
  motif_correction: string | null;
  service: "courtage" | "comparaison";
  constats: Constat[];
  dossier?: { id: string; statut: string; numero: string | null } | null;
}

export interface Prestations {
  prestations: Prestation[];
  totaux: { nombre: number; retraites: number; autres_departs: number; du: number; verse: number; part_fonds_payee: number };
}

export interface LigneImport {
  numero: number; matricule: string; motif: MotifDepart; date_embauche: string; date_depart: string;
  salaire_mensuel_reference: number; du: number; verse: number | null; part_fonds_payee: number | null;
  calcul: CalculPrestation; constats: Constat[];
}

export interface ApercuImport {
  lignes: LigneImport[];
  anomalies: Anomalie[];
  colonnes: Record<string, string>;
  colonnes_ignorees: string[];
  enregistrees: number;
}

export type EtapeDossier = "declare" | "a_completer" | "resoumis" | "verifie" | "transmis" | "paye" | "refuse" | "identite_effacee";

export interface Beneficiaire {
  qualite: "salarie" | "ayant_droit"; nom: string; prenoms: string | null; date_naissance: string | null;
  piece_type: "cni" | "passeport" | "carte_sejour" | "autre"; piece_numero: string; telephone: string | null;
  moyen_paiement: "virement" | "mobile_money" | "cheque"; coordonnees_paiement: string | null;
}

export interface DossierPEC {
  id: string; matricule: string; date_depart: string; prestation_id: string; montant_demande: number;
  statut: Exclude<EtapeDossier, "identite_effacee">; numero: string | null; assureur: string | null;
  numero_police: string | null; mandat_reference: string | null;
  evenements: { etape: EtapeDossier; le: string; montant: number | null; motif: string | null; numero: string | null }[];
  beneficiaire: Beneficiaire | null;
  pieces: { id: string; nature: string; nom_fichier: string; taille: number; empreinte: string; cree_le: string }[];
  identite_effacee: boolean; efface_le: string | null; constats: Constat[];
}

export interface Orientation {
  prestation_id: string; service: "courtage" | "comparaison"; qui_s_en_occupe: "plateforme" | "entreprise";
  assureur: string | null; numero_police: string | null; date_effet_police: string | null;
  du: number; verse: number | null; montant_a_demander: number; calcul: CalculPrestation;
  delai_jours: number; delai_exige: boolean; pieces: { nature: string; libelle: string; detail: string }[]; message: string;
}

export interface CritereConformite {
  critere: string; libelle: string; sens: "min" | "max" | "oui";
  demande: number | boolean; offert: number | boolean | null; conforme: boolean | null;
}

export interface ReponseAssureur {
  id: string; assureur: string; recue_le: string; taux_garanti: number; participation_benefices: number;
  frais_sur_cotisations: number; frais_sur_encours: number; delai_paiement_jours: number | null;
  transfert_preavis_mois: number | null; transfert_penalite: number | null; accepte_etude_plateforme: boolean | null;
  reporting_annuel: boolean | null; historique_participation: string | null; commentaire: string | null;
  conformite: CritereConformite[]; conforme: boolean; tardive: boolean; rang: number | null;
  cout_net_actualise: number | null; offre: { nom_fichier: string; empreinte: string } | null;
  remplace_id: string | null; motif_correction: string | null;
}

export interface ReponsesFiche {
  fiche_id: string; date_limite_reponse: string; conditions: Record<string, number | boolean | string | null>;
  reponses: ReponseAssureur[]; recommandee: string | null; comparaison: Financement | null;
  choix: { reponse_id: string; assureur: string; motif: string | null; choisi_le: string; recommandee: boolean } | null;
}

export interface ModeExtraction {
  moteur: string; modele: string | null; envoie_a_un_tiers: boolean; pays_couverts: Record<string, string>;
}

export interface VersionProposee {
  en_vigueur_du: string | null; fondement: string; document_reference: string; categories: Categorie[];
}

export interface ModeleType {
  code: string; modele: "minimum" | "plus_25" | "cadres" | "simple"; titre: string; description: string;
  convention: { code: string; libelle: string; statut: "valide" | "a_valider" };
  version: VersionProposee;
  illustration: { anciennete: number; minimum: number; par_categorie: Record<string, number> }[];
}

export interface ModelesDuPays { pays: string; pays_libelle: string; modeles: ModeleType[] }

export interface RegimeCatalogue {
  id: string; convention_code: string | null; ecart_convention_20_ans: number | null;
  illustration: { anciennete: number; par_categorie: Record<string, number> }[];
  categories: Omit<Categorie, "convention_code">[];
}

export interface GroupeCatalogue {
  pays: string | null; secteur: string | null; taille: string | null; libelle: string; entreprises: number;
  regimes: RegimeCatalogue[];
}

export interface Catalogue {
  seuil: number; entreprises: number; groupes: GroupeCatalogue[];
  secteurs: Record<string, string>; tailles: Record<string, string>;
}

export interface PartageDossier { partage_id: string; version_id: string; partage_le: string; actif: boolean; visible: boolean }

export interface ExtractionProposee extends ModeExtraction {
  id: string;
  version: VersionProposee | Record<string, never>;
  verifications: { champ: string; valeur: unknown; citation: string | null; retrouvee: boolean | null }[];
  constats: Constat[];
}

export interface Alerte {
  niveau: "grave" | "attention" | "info";
  code: string; titre: string; detail: string;
  lien: string;                         // la page du dossier, relative à lui
  pour: "entreprise" | "conseiller";    // qui doit agir
}

/** Une hypothèse de l'étude, telle qu'on la lit : défaut, retenue, rôle, effet mesuré, comment la fixer. */
export interface HypotheseLue {
  champ: string; libelle: string; defaut: string; retenu: string; ecarte: boolean; role: string; effet: string; fixer: string;
}

export interface Tranche { des: number; taux: number }

/** Le catalogue des hypothèses réglables (`GET /referentiel/hypotheses`). */
export interface CatalogueHypotheses {
  defauts: Record<string, number | string | null> & { taux_turnover: number; age_retraite: number; table: string };
  champs: { champ: string; libelle: string; nature: "taux" | "age" | "tranches" | "table"; min: number | null;
            max: number | null; role: string; effet: string; fixer: string; avec: string }[];
  tables: { code: string; libelle: string; disponible: boolean; raison?: string }[];
  age_premier_emploi: number;
}

/** Le cycle de vie d'un dossier (un dossier archivé ou supprimé ne figure plus dans « Vos dossiers »). */
export type EtatCycle = "ouvert" | "suspendu" | "cloture" | "archive" | "supprime";
export type ActionCycle = "suspendre" | "cloturer" | "reprendre" | "supprimer";

export interface Cycle {
  etat: EtatCycle; libelle: string; depuis: string; archivage_prevu: string | null;
  actions: ActionCycle[]; supprimable: boolean;
  motifs: Record<ActionCycle, { code: string; libelle: string }[]>;
  historique: { etat: EtatCycle; libelle: string; action: string; motif_code: string | null; motif_libelle: string | null;
                motif: string | null; par: string; le: string }[];
}


/** Une ligne du ménage : une version qui peut partir, pourquoi, et ce que la plateforme coche. */
export interface CandidatMenage {
  version_id: string; regime: string; numero: number; statut: "analyse" | "adoptee"; raison: string; coche: boolean;
  brouillons: { id: string; date_evaluation: string }[]; motif_requis: boolean;
}
