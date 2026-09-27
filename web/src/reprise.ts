/** « Reprendre où l'on s'était arrêté » : la dernière page ouverte dans un dossier, par personne, dans ce
 *  navigateur. On ne garde que l'identifiant du dossier, le chemin et le libellé des pages ; le nom du
 *  dossier est relu à l'affichage, et un dossier auquel on n'a plus accès ne se propose pas. */

import { langue, t } from "./i18n";

export interface Reprise { org: string; chemin: string; pages: string[]; quand: number }

const cle = (utilisateur: string) => `courtage:reprise:${utilisateur}`;

export function noterReprise(utilisateur: string, reprise: Reprise): void {
  try { localStorage.setItem(cle(utilisateur), JSON.stringify(reprise)); } catch { /* stockage refusé : rien à reprendre */ }
}

export function lireReprise(utilisateur: string): Reprise | null {
  try {
    const brut = localStorage.getItem(cle(utilisateur));
    const r = brut ? (JSON.parse(brut) as Reprise) : null;
    return r && typeof r.org === "string" && typeof r.chemin === "string" && r.chemin.startsWith(`/dossier/${r.org}`) ? r : null;
  } catch {
    return null;
  }
}

/** « à l'instant », « il y a 12 min », « il y a 3 h », « hier », « il y a 4 jours », puis la date. */
export function ilYa(quand: number, maintenant = Date.now()): string {
  const minutes = Math.floor((maintenant - quand) / 60_000);
  if (minutes < 1) return t("à l'instant", "just now");
  if (minutes < 60) return t(`il y a ${minutes} min`, `${minutes} min ago`);
  const heures = Math.floor(minutes / 60);
  if (heures < 24) return t(`il y a ${heures} h`, `${heures} h ago`);
  const jours = Math.floor(heures / 24);
  if (jours === 1) return t("hier", "yesterday");
  if (jours < 7) return t(`il y a ${jours} jours`, `${jours} days ago`);
  return langue() === "en" ? `on ${new Date(quand).toLocaleDateString("en-GB")}`
    : `le ${new Date(quand).toLocaleDateString("fr-FR")}`;
}
