/** Le vocabulaire des versions d'un régime, en un seul endroit. Une version est un **brouillon** ou une version
 *  **adoptée**, rien d'autre ; ses dates (s'applique depuis, à partir de, remplacée le) sont une information. */
import { dateFr } from "./format";
import { t } from "./i18n";
import type { Version } from "./types";

/** Les libellés sont des accesseurs : lus au rendu, ils suivent la langue choisie. */
export const STATUTS: Record<Version["statut"], { libelle: string; classe: "bien" | "attention"; definition: string }> = {
  analyse: {
    get libelle() { return t("Brouillon", "Draft"); }, classe: "attention",
    get definition() {
      return t("En analyse : se modifie, se duplique, se compare, s'adopte ou se supprime. Aucune étude ne s'émet dessus.",
        "Under review: it can be edited, duplicated, compared, adopted or deleted. No study can be issued on it.");
    },
  },
  adoptee: {
    get libelle() { return t("Adoptée", "Adopted"); }, classe: "bien",
    get definition() {
      return t("Figée parce que communiquée (notes aux salariés et aux assureurs). Pour la changer : la dupliquer en "
        + "brouillon. Elle se supprime tant que rien ne la cite.",
        "Frozen because it has been communicated (notices to employees and insurers). To change it, duplicate it as a "
        + "draft. It can be deleted as long as nothing refers to it.");
    },
  },
};

/** Où ranger une version : ce qui s'applique ou s'appliquera, ce qui se prépare, ce qui a été remplacé (replié). */
export type Zone = "application" | "brouillons" | "historique";
export const ZONES: { cle: Zone; titre: string; repliee?: boolean }[] = [
  { cle: "application", get titre() { return t("En application", "In force"); } },
  { cle: "brouillons", get titre() { return t("Brouillons", "Drafts"); } },
  { cle: "historique", get titre() { return t("Historique", "History"); }, repliee: true },
];

export function zone(v: Version): Zone {
  if (v.statut === "analyse") return "brouillons";
  const a = v.application;
  return a && !a.en_cours && !a.a_venir ? "historique" : "application";
}

/** La ligne de dates d'une version. */
export function periode(v: Version): string {
  const a = v.application;
  if (v.statut === "analyse") return t(`prévue à partir du ${dateFr(v.en_vigueur_du)}`, `planned from ${dateFr(v.en_vigueur_du)}`);
  if (!a) return t(`à partir du ${dateFr(v.en_vigueur_du)}`, `from ${dateFr(v.en_vigueur_du)}`);
  if (a.a_venir) return t(`s'appliquera à partir du ${dateFr(a.depuis)}`, `will apply from ${dateFr(a.depuis)}`);
  if (a.remplacee_le && !a.en_cours)
    return t(`s'est appliquée du ${dateFr(a.depuis)} au ${dateFr(a.remplacee_le)}, remplacée par la version ${a.remplacee_par}`,
      `applied from ${dateFr(a.depuis)} to ${dateFr(a.remplacee_le)}, replaced by version ${a.remplacee_par}`);
  return t(`s'applique depuis le ${dateFr(a.depuis)}`, `applies since ${dateFr(a.depuis)}`)
    + (a.remplacee_le ? t(`, jusqu'au ${dateFr(a.remplacee_le)} (version ${a.remplacee_par})`,
      `, until ${dateFr(a.remplacee_le)} (version ${a.remplacee_par})`) : "");
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
