/** La comparaison des régimes simulés : des chiffres côte à côte, ce que chaque barème verse selon l'ancienneté,
 *  et qui gagne ou perd d'une variante à l'autre. Pur, sans rendu. */
import { COULEURS } from "./echeancier";
import { t } from "./i18n";
import type { Totaux } from "./types";

export interface Variante {
  nom: string;
  totaux: Totaux;
  cotisation_initiale: number;
  ecart_convention: number;
  courbes: Record<string, number[]>;
  ifc_par_salarie: Record<string, number>;
  categorie_par_salarie: Record<string, string>;
}

/** La référence (la convention seule) en neutre foncé, toujours en tirets ; les variantes dans l'ordre de la palette,
 *  par leur rang dans la simulation : une variante garde sa couleur quel que soit le point de comparaison. */
export const NEUTRE = "#4a5068";
export const GAIN = "#2a78d6";
export const PERTE = "#eb6834";
export const EGAL = "#c9cdd9";

export function couleur(rang: number): string {
  return rang === 0 ? NEUTRE : COULEURS[(rang - 1) % COULEURS.length];
}

/** `libelle` est un accesseur : lu au rendu, il suit la langue choisie. */
export const MESURES = {
  dette: { get libelle() { return t("Dette actuarielle", "Actuarial liability"); }, lire: (v: Variante) => v.totaux.dette },
  charge: { get libelle() { return t("Charge annuelle", "Annual cost"); }, lire: (v: Variante) => v.totaux.charge },
  cotisation: { get libelle() { return t("Cotisation initiale", "Initial contribution"); }, lire: (v: Variante) => v.cotisation_initiale },
  dette_par_salarie: { get libelle() { return t("Dette par salarié", "Liability per employee"); },
                       lire: (v: Variante) => v.totaux.dette / (v.totaux.effectif || 1) },
  charge_par_salarie: { get libelle() { return t("Charge par salarié", "Cost per employee"); },
                        lire: (v: Variante) => v.totaux.charge / (v.totaux.effectif || 1) },
} as const;
export type Mesure = keyof typeof MESURES;

/** Les catégories du personnel, de la plus nombreuse à la moins nombreuse. */
export function categories(v: Variante): string[] {
  const n = new Map<string, number>();
  for (const c of Object.values(v.categorie_par_salarie)) n.set(c, (n.get(c) ?? 0) + 1);
  return [...n.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([c]) => c);
}

/** Ce que la variante verse à une catégorie : sa règle propre, sinon celle des « autres » (« * »). */
export function courbe(v: Variante, categorie: string): number[] {
  return v.courbes[categorie] ?? v.courbes["*"] ?? [];
}

export interface Bilan {
  gagnent: number; perdent: number; inchanges: number;
  gainMoyen: number; perteMoyenne: number;
  plusGrosGain: { matricule: string; montant: number } | null;
  plusGrossePerte: { matricule: string; montant: number } | null;
  ecartTotal: number;
}

/** Salarié par salarié, l'indemnité au départ sous `v` contre sous la référence. Un écart d'un franc ou moins est
 *  un arrondi, pas un gain. `categorie` restreint aux salariés de cette catégorie. */
export function bilan(reference: Variante, v: Variante, categorie?: string): Bilan {
  const b: Bilan = { gagnent: 0, perdent: 0, inchanges: 0, gainMoyen: 0, perteMoyenne: 0, plusGrosGain: null,
                     plusGrossePerte: null, ecartTotal: 0 };
  let gains = 0, pertes = 0;
  for (const [m, avant] of Object.entries(reference.ifc_par_salarie)) {
    if (categorie && reference.categorie_par_salarie[m] !== categorie) continue;
    const ecart = (v.ifc_par_salarie[m] ?? 0) - avant;
    b.ecartTotal += ecart;
    if (ecart > 1) {
      b.gagnent++; gains += ecart;
      if (!b.plusGrosGain || ecart > b.plusGrosGain.montant) b.plusGrosGain = { matricule: m, montant: ecart };
    } else if (ecart < -1) {
      b.perdent++; pertes += ecart;
      if (!b.plusGrossePerte || ecart < b.plusGrossePerte.montant) b.plusGrossePerte = { matricule: m, montant: ecart };
    } else b.inchanges++;
  }
  b.gainMoyen = b.gagnent ? gains / b.gagnent : 0;
  b.perteMoyenne = b.perdent ? pertes / b.perdent : 0;
  return b;
}

/** L'écart relatif à la référence, pour une mesure ; null quand la référence vaut zéro. */
export function ecartRelatif(valeur: number, reference: number): number | null {
  return reference ? (valeur - reference) / reference : null;
}

/** Des noms courts pour les graphiques : ce que les variantes ont en commun en tête (« Accord IFC Société Démo, ») se
 *  retire, pour que « version 1 » et « version 2 » ne se tronquent pas en deux libellés identiques. La référence et
 *  une variante seule gardent leur nom. Le nom complet reste dans la légende et les bulles. */
export function nomsCourts(noms: string[]): string[] {
  const variantes = noms.slice(1);
  if (variantes.length < 2) return noms;
  const mots = variantes.map((n) => n.split(" "));
  let commun = 0;
  while (mots.every((m) => m.length > commun + 1 && m[commun] === mots[0][commun])) commun++;
  // Couper à une virgule (« Accord IFC Démo, | version 1 »), sinon garder au moins deux mots.
  const virgule = mots[0].slice(0, commun).map((m) => m.endsWith(",")).lastIndexOf(true);
  commun = virgule >= 0 ? virgule + 1 : Math.min(commun, Math.min(...mots.map((m) => m.length)) - 2);
  if (commun <= 0) return noms;
  return [noms[0], ...mots.map((m) => m.slice(commun).join(" "))];
}

/** La catégorie où les régimes diffèrent le plus : la courbe s'ouvre là, pas sur des courbes confondues. */
export function categorieParlante(variantes: Variante[]): string {
  const cats = categories(variantes[0]);
  const ecart = (c: string) => {
    const courbes = variantes.map((v) => courbe(v, c));
    return courbes[0].reduce((t, _, n) => t + Math.max(...courbes.map((x) => x[n] ?? 0)) - Math.min(...courbes.map((x) => x[n] ?? 0)), 0);
  };
  return cats.reduce((meilleure, c) => (ecart(c) > ecart(meilleure) + 1e-9 ? c : meilleure), cats[0]);
}

/** Les variantes qui versent exactement la même chose que la référence à cette catégorie. */
export function confondues(variantes: Variante[], categorie: string): string[] {
  const ref = courbe(variantes[0], categorie);
  return variantes.slice(1).filter((v) => courbe(v, categorie).every((y, n) => Math.abs(y - (ref[n] ?? 0)) < 1e-9)).map((v) => v.nom);
}
