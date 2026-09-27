// Montants en francs CFA entiers, dates et taux : à la française, ou à l'anglaise quand la page est en anglais.
import { langue } from "./i18n";

const entier = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const integer = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
const virgule = (s: string) => (langue() === "en" ? s : s.replace(".", ","));

export function montant(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  if (langue() === "en") return `${integer.format(Math.round(n))} F`;
  return `${entier.format(Math.round(n)).replace(/ | /g, " ")} F`;
}

export function millions(n: number): string {
  return `${virgule((n / 1_000_000).toFixed(1))} M F`;
}

export function pct(x: number | null | undefined, decimales = 1): string {
  if (x === null || x === undefined) return "—";
  return `${virgule((x * 100).toFixed(decimales))}${langue() === "en" ? "%" : " %"}`;
}

export function dateFr(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, j] = iso.slice(0, 10).split("-");
  return `${j}/${m}/${a}`;
}

/** Des mois d'indemnité, à la française : « 3,8 mois », « 14,5 mois ». */
export function mois(n: number): string {
  return langue() === "en" ? `${n.toLocaleString("en-GB", { maximumFractionDigits: 2 })} months`
    : `${n.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} mois`;
}
