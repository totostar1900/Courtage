/** L'état d'une inscription et ce qu'il permet, lus du serveur (qui les contrôle aussi). */
import { t } from "./i18n";

export type Capacite = "rapport_scelle" | "export_etude" | "notes_regime" | "fiche_de_calcul" | "equipe" | "catalogue"
  | "extraction_claude" | "mandat" | "cahier" | "departs";

export interface Activation {
  etat: "en_attente" | "confirmee" | "refusee";
  capacites: Record<Capacite, boolean>;
  libelles: Record<Capacite, string>;
  rccm: string | null; taille: string | null; adresse: string | null; ville: string | null;
  demandee_le: string | null; decidee_le: string | null; motif: string | null;
  echeance?: string; expire_le?: string;
}

/** Un dossier sans lecture d'activation (ancien, ou démonstration) est confirmé. */
export const CONFIRMEE: Activation = {
  etat: "confirmee", libelles: {} as Record<Capacite, string>,
  capacites: { rapport_scelle: true, export_etude: true, notes_regime: true, fiche_de_calcul: true, equipe: true,
               catalogue: true, extraction_claude: true, mandat: true, cahier: true, departs: true },
  rccm: null, taille: null, adresse: null, ville: null, demandee_le: null, decidee_le: null, motif: null,
};

/** `null` : permis. Sinon, la raison à afficher sur l'action grisée. */
export function raisonActivation(a: Activation | undefined, c: Capacite): string | null {
  if (!a || a.capacites[c]) return null;
  if (a.etat !== "confirmee") return t("Après confirmation de votre inscription par votre conseiller.",
    "Once your adviser has confirmed your sign-up.");
  if (c === "departs") return t("Une fois le contrat d'assurance signé et en vigueur.", "Once the insurance contract is signed and in force.");
  return t("Sous mandat de courtage signé.", "Under a signed brokerage mandate.");
}

export interface Inscription {
  id: string; nom: string; pays: string; secteur: string | null; rccm: string; taille: string; adresse: string | null;
  ville: string | null; demandee_le: string; echeance: string; en_retard: boolean; rccm_depose: boolean;
  expire_le: string; messages_non_lus: number; accompagnement_demande?: boolean;
  justificatifs?: { id: string; nom_fichier: string; depose_le: string }[];
  demandeur: { nom: string | null; fonction: string | null; telephone: string | null; courriel: string | null } | null;
}

