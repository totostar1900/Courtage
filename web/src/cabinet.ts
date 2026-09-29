import { api } from "./api";
import { useCharge } from "./composants/communs";

/** Le cabinet qui exploite la plateforme, tel que la configuration le donne (`GET /public/cabinet`). */
export interface Cabinet {
  nom: string; agrement: string; adresse: string; rccm: string; courriel: string; telephone: string;
  hebergeur: string; conditions_version: string; manquants: string[];
}

let enCours: Promise<Cabinet | null> | null = null;

/** Lu une fois par chargement : le pied de page de chaque écran s'en sert. Une erreur rend `null`, jamais un écran
 *  cassé. */
export function lireCabinet(): Promise<Cabinet | null> {
  enCours ??= api.get<Cabinet>("/public/cabinet").catch(() => { enCours = null; return null; });
  return enCours;
}

export function useCabinet(): Cabinet | null {
  return useCharge(lireCabinet, []).donnee ?? null;
}

/** Pour les tests : oublier la lecture précédente. */
export function oublierCabinet() { enCours = null; }
