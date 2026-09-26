// Les formes renvoyées par l'API (courtage/api/routes.py). Seul ce que l'interface lit est typé.

export type Role = "admin_client" | "lecteur_client" | "conseiller";

export interface Moi {
  id: string;
  email: string | null;
  admin_plateforme: boolean;
  organisations: { id: string; nom: string; pays: string; role: Role }[];
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
  hypotheses: { valeurs: Record<string, number | string>; ecarts: unknown[]; justification: string | null };
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
