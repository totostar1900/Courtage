/** Le vocabulaire des versions d'un régime, en un seul endroit. Une version est un **brouillon** ou une version
 *  **adoptée**, rien d'autre ; ses dates (s'applique depuis, à partir de, remplacée le) sont une information. */
import { dateFr } from "./format";
import type { Version } from "./types";

export const STATUTS: Record<Version["statut"], { libelle: string; classe: "bien" | "attention"; definition: string }> = {
  analyse: {
    libelle: "Brouillon", classe: "attention",
    definition: "En analyse : se modifie, se duplique, se compare, s'adopte ou se supprime. Aucune étude ne s'émet dessus.",
  },
  adoptee: {
    libelle: "Adoptée", classe: "bien",
    definition: "Figée parce que communiquée (notes aux salariés et aux assureurs). Pour la changer : la dupliquer en "
      + "brouillon. Elle se supprime tant que rien ne la cite.",
  },
};

/** Où ranger une version : ce qui s'applique ou s'appliquera, ce qui se prépare, ce qui a été remplacé (replié). */
export type Zone = "application" | "brouillons" | "historique";
export const ZONES: { cle: Zone; titre: string; repliee?: boolean }[] = [
  { cle: "application", titre: "En application" },
  { cle: "brouillons", titre: "Brouillons" },
  { cle: "historique", titre: "Historique", repliee: true },
];

export function zone(v: Version): Zone {
  if (v.statut === "analyse") return "brouillons";
  const a = v.application;
  return a && !a.en_cours && !a.a_venir ? "historique" : "application";
}

/** La ligne de dates d'une version. */
export function periode(v: Version): string {
  const a = v.application;
  if (v.statut === "analyse") return `prévue à partir du ${dateFr(v.en_vigueur_du)}`;
  if (!a) return `à partir du ${dateFr(v.en_vigueur_du)}`;
  if (a.a_venir) return `s'appliquera à partir du ${dateFr(a.depuis)}`;
  if (a.remplacee_le && !a.en_cours)
    return `s'est appliquée du ${dateFr(a.depuis)} au ${dateFr(a.remplacee_le)}, remplacée par la version ${a.remplacee_par}`;
  return `s'applique depuis le ${dateFr(a.depuis)}`
    + (a.remplacee_le ? `, jusqu'au ${dateFr(a.remplacee_le)} (version ${a.remplacee_par})` : "");
}

/** Ce qui s'applique d'abord, puis ce qui vient, les brouillons, l'historique ; le plus récent d'abord. */
export function ordonner(versions: Version[]): Version[] {
  const rang = (v: Version) => (zone(v) === "application" ? (v.application?.en_cours ? 0 : 1) : zone(v) === "brouillons" ? 2 : 3);
  return [...versions].sort((a, b) => rang(a) - rang(b) || b.numero - a.numero);
}

export function enCours(v: Version): boolean {
  return v.statut === "adoptee" && (v.application?.en_cours ?? true);
}

/** Le libellé d'une version dans une liste (étude, simulation) : « Accord IFC, version 2 — brouillon ». */
export function libelleVersion(v: Pick<Version, "numero" | "statut">, nomRegime: string): string {
  return `${nomRegime}, version ${v.numero} — ${STATUTS[v.statut].libelle.toLowerCase()}`;
}
