/** Le thème de l'écran : celui de l'appareil par défaut, ou clair, ou sombre, au choix de la personne. Le choix est
 *  gardé dans ce navigateur ; il pose `data-theme` sur la racine, que la feuille de style lit (styles.css, en tête).
 *  Les documents scellés restent clairs : ce sont des documents, pas des écrans. */
export type Theme = "auto" | "clair" | "sombre";
const CLE = "courtage:theme";

export function lireTheme(): Theme {
  try {
    const v = localStorage.getItem(CLE);
    return v === "clair" || v === "sombre" ? v : "auto";
  } catch { return "auto"; }
}

export function appliquerTheme(theme: Theme) {
  const racine = document.documentElement;
  if (theme === "auto") racine.removeAttribute("data-theme");
  else racine.setAttribute("data-theme", theme === "sombre" ? "dark" : "light");
}

export function choisirTheme(theme: Theme) {
  try { if (theme === "auto") localStorage.removeItem(CLE); else localStorage.setItem(CLE, theme); } catch { /* ce navigateur ne garde rien */ }
  appliquerTheme(theme);
}
