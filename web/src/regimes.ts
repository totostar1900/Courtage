/** Le vocabulaire des versions d'un régime, en un seul endroit : ce que dit chaque état, ce qu'il implique, et comment
 *  on en sort. La page Régime, les études, la simulation et le guide le lisent ici. */
import type { EtatVersion, Version } from "./types";

export const ETATS_VERSION: Record<EtatVersion, {
  libelle: string; classe: "bien" | "attention" | "neutre"; definition: string; impact: string; suite: string;
}> = {
  projet: {
    libelle: "Projet", classe: "attention",
    definition: "Enregistrée, pas encore adoptée par l'entreprise.",
    impact: "Elle se simule et s'étudie en brouillon ; aucune étude ne s'émet sur elle.",
    suite: "L'entreprise l'adopte ; sinon on l'abandonne, ou on la supprime si aucune étude ne s'en est servie.",
  },
  a_venir: {
    libelle: "Adoptée, à venir", classe: "neutre",
    definition: "Adoptée, sa date d'effet n'est pas encore arrivée.",
    impact: "Elle s'appliquera aux études datées de son entrée en vigueur ou après.",
    suite: "Elle entre en vigueur d'elle-même à sa date.",
  },
  en_vigueur: {
    libelle: "En vigueur", classe: "bien",
    definition: "Adoptée, et la plus récente dont la date d'effet est passée.",
    impact: "C'est la base des études d'aujourd'hui.",
    suite: "Pour la changer : enregistrer une nouvelle version, que l'entreprise adopte. Elle la remplacera à sa date.",
  },
  remplacee: {
    libelle: "Remplacée", classe: "neutre",
    definition: "Adoptée, puis relayée par une version plus récente.",
    impact: "Elle reste la base des études datées de sa période d'application.",
    suite: "Elle ne bouge plus et ne se supprime pas : des études et des rapports la citent.",
  },
  abandonnee: {
    libelle: "Abandonnée", classe: "neutre",
    definition: "Un projet que l'entreprise n'a pas retenu.",
    impact: "Elle ne sert plus de base à une étude ; elle reste lisible, avec son motif.",
    suite: "Elle ne bouge plus.",
  },
};

/** L'état d'une version ; une réponse ancienne (sans `etat`) se lit sur son statut. */
export function etatVersion(v: Pick<Version, "statut" | "etat">): EtatVersion {
  return v.etat ?? (v.statut === "adoptee" ? "en_vigueur" : v.statut === "abandonnee" ? "abandonnee" : "projet");
}

/** L'ordre de lecture : ce qui s'applique, ce qui vient, ce qui attend une décision ; puis l'historique. */
const RANG: Record<EtatVersion, number> = { en_vigueur: 0, a_venir: 1, projet: 2, remplacee: 3, abandonnee: 4 };
export const ACTUELS: EtatVersion[] = ["en_vigueur", "a_venir", "projet"];

export function ordonner(versions: Version[]): Version[] {
  return [...versions].sort((a, b) => RANG[etatVersion(a)] - RANG[etatVersion(b)] || b.numero - a.numero);
}

/** Le libellé d'une version dans une liste (étude, simulation) : « Accord IFC, version 2 — projet ». */
export function libelleVersion(v: Pick<Version, "numero" | "statut" | "etat">, nomRegime: string): string {
  return `${nomRegime}, version ${v.numero} — ${ETATS_VERSION[etatVersion(v)].libelle.toLowerCase()}`;
}
