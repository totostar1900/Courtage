// Le serveur de la démonstration : il rejoue des réponses de la VRAIE API, enregistrées sur une
// entreprise fictive (api/scripts/capturer_demo.py), et calcule le financement dans le navigateur.
// Rien ne s'écrit : toute action qui modifierait le dossier répond qu'il s'agit d'une démonstration.

import { ErreurApi } from "../api";
import donnees from "./donnees.json";
import documents from "./documents.json";
import { SCENARIOS, arrondir, projeter, type OffreF } from "./financement";

const R = donnees.reponses as Record<string, unknown>;
export const DOCUMENTS = documents as Record<string, string[]>;

export async function repondre(methode: string, chemin: string, corps: unknown, utilisateur: string | null): Promise<unknown> {
  const m = methode.toUpperCase();
  if (m === "GET" && chemin === "/auth/mode") return { mode: "demonstration" };
  if (m === "GET" && chemin === "/moi") {
    if (!utilisateur) throw new ErreurApi(401, "non_authentifie", "Choisissez une personne.");
    return trouver(`GET /moi@${utilisateur}`);
  }
  if (m === "POST" && chemin === "/auth/deconnexion") return { message: "Déconnecté." };
  if (m === "GET") return trouver(`GET ${chemin}`);
  if (m === "POST" && chemin.endsWith("/simulations")) return trouver(`POST ${chemin}`);
  const f = chemin.match(/^\/organisations\/[^/]+\/etudes\/([^/]+)\/financement$/);
  if (m === "POST" && f) return financer(chemin.replace(/\/financement$/, ""), corps as Record<string, unknown>);
  throw new ErreurApi(403, "demo_lecture_seule",
    "Démonstration en lecture seule : dans la version réelle, cette action est enregistrée et tracée.");
}

function trouver(cle: string): unknown {
  if (cle in R) return structuredClone(R[cle]);
  throw new ErreurApi(404, "introuvable", "Cette page n'a pas de données dans la démonstration.");
}

function financer(cheminEtude: string, corps: Record<string, unknown>) {
  const e = trouver(`GET ${cheminEtude}`) as {
    date_evaluation: string; fonds_disponible: number; totaux: { dette: number; charge: number };
    hypotheses: { valeurs: Record<string, number> }; echeancier: { annee: number; prestations_probables: number }[];
  };
  const horizon = Number(corps.horizon ?? 10), amortissement = Number(corps.amortissement_annees ?? 1);
  if (!(horizon >= 1 && horizon <= 40 && amortissement >= 1 && amortissement <= horizon))
    throw new ErreurApi(422, "parametres_invalides", "Horizon entre 1 et 40 ans, rattrapage entre 1 an et l'horizon.");
  const offres = [...((corps.offres as OffreF[]) ?? [])];
  if (!offres.some((o) => o.interne)) offres.push({ nom: "Provision interne", taux_garanti: 0, interne: true });
  const p = { horizon, amortissement_annees: amortissement, taux_actualisation: e.hypotheses.valeurs.taux_actualisation,
              croissance_salaires: e.hypotheses.valeurs.croissance_salaires };
  const engagement = { annee_evaluation: Number(e.date_evaluation.slice(0, 4)), dette: e.totaux.dette, charge: e.totaux.charge,
    fonds_initial: e.fonds_disponible,
    prestations: Object.fromEntries(e.echeancier.map((a) => [a.annee, a.prestations_probables])) };
  return { parametres: p, ...(arrondir(projeter(engagement, offres, SCENARIOS, p)) as object) };
}
