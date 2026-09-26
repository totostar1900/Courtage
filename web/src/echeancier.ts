import type { Annee } from "./types";

/** L'échéancier mis en forme pour le graphique : une colonne par année, une série par catégorie (ou une
 *  seule), selon la mesure, la lecture (annuelle ou cumulée) et l'horizon choisis. Pur, sans rendu. */

export type Mesure = "prestations_probables" | "ifc" | "vapf" | "effectif";
export type Lecture = "annuelle" | "cumulee";
export type Decoupage = "ensemble" | "categorie";
/** Le nombre d'années affichées depuis la première (1 à 30), ou tout l'échéancier. */
export type Horizon = number | "tout";
export const HORIZON_MAX = 30;

export const MESURES: Record<Mesure, { libelle: string; court: string; montant: boolean }> = {
  prestations_probables: { libelle: "Prestations probables", court: "Probables", montant: true },
  ifc: { libelle: "Si tous partent", court: "Si tous partent", montant: true },
  vapf: { libelle: "Valeur actuelle", court: "Valeur actuelle", montant: true },
  effectif: { libelle: "Départs à la retraite", court: "Départs", montant: false },
};

// La palette catégorielle validée (ordre fixe, jamais recyclé) ; au-delà, « Autres catégories ».
export const COULEURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
const ENSEMBLE = "#2f419a";
const MAX_SERIES = COULEURS.length;
const AUTRES = "__autres__";

export interface Serie { cle: string; libelle: string; couleur: string }
export interface Colonne { annee: number; valeurs: Record<string, number>; total: number; effectif: number }
export interface Vue { series: Serie[]; colonnes: Colonne[]; max: number; decoupageDisponible: boolean }

type Part = { effectif: number; ifc: number; prestations_probables?: number; vapf: number };
const valeur = (p: Part, m: Mesure) => (m === "prestations_probables" ? p.prestations_probables ?? p.ifc : p[m]);

/** Les catégories, de la plus lourde à la plus légère sur TOUT l'échéancier : la couleur suit la catégorie,
 *  jamais son rang dans l'horizon affiché (un filtre ne repeint pas les séries qui restent). */
export function categories(annees: Annee[]): Serie[] {
  const poids = new Map<string, number>();
  for (const a of annees) {
    for (const [c, p] of Object.entries(a.par_categorie ?? {})) poids.set(c, (poids.get(c) ?? 0) + valeur(p, "prestations_probables"));
  }
  const ordre = [...poids.entries()].sort((x, y) => y[1] - x[1]).map(([c]) => c);
  const seule = ordre.length === 1;
  const libelle = (c: string) => (c === "*" ? (seule ? "Tout le personnel" : "Autres salariés") : c);
  if (ordre.length <= MAX_SERIES) return ordre.map((c, i) => ({ cle: c, libelle: libelle(c), couleur: COULEURS[i] }));
  return [...ordre.slice(0, MAX_SERIES - 1).map((c, i) => ({ cle: c, libelle: libelle(c), couleur: COULEURS[i] })),
          { cle: AUTRES, libelle: "Autres catégories", couleur: COULEURS[MAX_SERIES - 1] }];
}

export function construire(annees: Annee[], mesure: Mesure, lecture: Lecture, decoupage: Decoupage, horizon: Horizon): Vue {
  if (!annees.length) return { series: [], colonnes: [], max: 1, decoupageDisponible: false };
  const decoupageDisponible = annees.every((a) => a.par_categorie && Object.keys(a.par_categorie).length > 0);
  const parCategorie = decoupage === "categorie" && decoupageDisponible;
  const series: Serie[] = parCategorie ? categories(annees) : [{ cle: "total", libelle: MESURES[mesure].libelle, couleur: ENSEMBLE }];
  const gardees = new Set(series.map((s) => s.cle));

  // Une colonne par année, départs ou non : l'axe du temps ne se comprime pas.
  const premiere = annees[0].annee;
  const derniere = annees[annees.length - 1].annee;
  const par = new Map(annees.map((a) => [a.annee, a]));
  const cumul: Record<string, number> = {};
  let effectifCumule = 0;
  const colonnes: Colonne[] = [];
  for (let annee = premiere; annee <= derniere; annee++) {
    const a = par.get(annee);
    const valeurs: Record<string, number> = Object.fromEntries(series.map((s) => [s.cle, 0]));
    if (a && parCategorie) {
      for (const [c, p] of Object.entries(a.par_categorie!)) valeurs[gardees.has(c) ? c : AUTRES] += valeur(p, mesure);
    } else if (a) {
      valeurs.total = valeur(a, mesure);
    }
    effectifCumule += a?.effectif ?? 0;
    if (lecture === "cumulee") for (const s of series) valeurs[s.cle] = (cumul[s.cle] = (cumul[s.cle] ?? 0) + valeurs[s.cle]);
    const total = Object.values(valeurs).reduce((t, v) => t + v, 0);
    colonnes.push({ annee, valeurs, total, effectif: lecture === "cumulee" ? effectifCumule : a?.effectif ?? 0 });
  }
  const vues = horizon === "tout" ? colonnes : colonnes.slice(0, horizon);
  return { series, colonnes: vues, max: Math.max(...vues.map((c) => c.total), 1), decoupageDisponible };
}

/** Un maximum rond pour l'axe, et ses graduations : 0, la moitié, le haut. */
export function graduations(max: number): number[] {
  const puissance = 10 ** Math.floor(Math.log10(max));
  const haut = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].map((f) => f * puissance).find((v) => v >= max) ?? max;
  return [0, haut / 2, haut];
}

/** L'année où les versements cumulés dépassent le fonds constitué ; null s'il les couvre tous. */
export function epuisement(colonnes: Colonne[], fonds: number): number | null {
  return colonnes.find((c) => c.total > fonds)?.annee ?? null;
}

/** Les années à écrire sous l'axe : toutes jusqu'à 12 colonnes, sinon les multiples de 5 (plus la première et la
 *  dernière quand elles ne tombent pas trop près d'un repère). */
export function reperesAnnees(annees: number[]): Set<number> {
  if (annees.length <= 12) return new Set(annees);
  const premiere = annees[0], derniere = annees[annees.length - 1];
  const reperes = new Set(annees.filter((a) => a % 5 === 0));
  if ([...reperes].every((a) => a - premiere >= 3)) reperes.add(premiere);
  if ([...reperes].every((a) => derniere - a >= 3)) reperes.add(derniere);
  return reperes;
}
