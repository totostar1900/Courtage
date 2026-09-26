// Montants en francs CFA entiers, dates et taux à la française.

const entier = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

export function montant(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return `${entier.format(Math.round(n)).replace(/ | /g, " ")} F`;
}

export function millions(n: number): string {
  return `${(n / 1_000_000).toFixed(1).replace(".", ",")} M F`;
}

export function pct(x: number | null | undefined, decimales = 1): string {
  if (x === null || x === undefined) return "—";
  return `${(x * 100).toFixed(decimales).replace(".", ",")} %`;
}

export function dateFr(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, j] = iso.slice(0, 10).split("-");
  return `${j}/${m}/${a}`;
}

/** Des mois d'indemnité, à la française : « 3,8 mois », « 14,5 mois ». */
export function mois(n: number): string {
  return `${n.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} mois`;
}
