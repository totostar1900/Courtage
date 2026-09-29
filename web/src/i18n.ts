/** Deux langues, le français d'abord. `t("français", "English")` s'écrit là où s'écrivait le texte : le français reste
 *  lisible dans le code, l'anglais vit à côté. La langue est choisie par le visiteur et gardée dans son navigateur.
 *
 *  Le serveur suit la même langue (en-tête X-Langue, voir api.ts). Restent en français : les documents scellés (PDF)
 *  et les exports, et les textes de référence (conventions collectives, sources). */
import { useSyncExternalStore } from "react";

export type Langue = "fr" | "en";
const CLE = "courtage:langue";

function lire(): Langue {
  try { return localStorage.getItem(CLE) === "en" ? "en" : "fr"; } catch { return "fr"; }
}

let courante: Langue = lire();
const ecouteurs = new Set<() => void>();

export function langue(): Langue { return courante; }

export function t(fr: string, en: string): string {
  return courante === "en" ? en : fr;
}

export function changerLangue(l: Langue): void {
  courante = l;
  try { localStorage.setItem(CLE, l); } catch { /* navigation privée : la langue vaut pour la visite */ }
  document.documentElement.lang = l;
  ecouteurs.forEach((f) => f());
}

/** Relit la langue gardée : les tests vident le stockage entre deux écrans. */
export function relireLangue(): void {
  if (lire() !== courante) changerLangue(lire());
}

export function useLangue(): Langue {
  return useSyncExternalStore((f) => { ecouteurs.add(f); return () => ecouteurs.delete(f); }, () => courante);
}
