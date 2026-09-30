/** Le thème de l'écran : celui de l'appareil par défaut, ou clair, pénombre, sombre, au choix de la personne. Le choix est
 *  gardé dans ce navigateur ; il pose `data-theme` sur la racine, que la feuille de style lit (styles.css, en tête).
 *  Les documents scellés restent clairs : ce sont des documents, pas des écrans. */
export type Theme = "auto" | "clair" | "penombre" | "sombre";
const CLE = "courtage:theme";

export function lireTheme(): Theme {
  try {
    const v = localStorage.getItem(CLE);
    return v === "clair" || v === "penombre" || v === "sombre" ? v : "auto";
  } catch { return "auto"; }
}

/** Le fond de chaque thème (`--fond` dans styles.css) : la barre du navigateur sur téléphone prend sa couleur. */
const FOND = { clair: "#f5f7f9", penombre: "#46515e", sombre: "#070b10" } as const;

export function appliquerTheme(theme: Theme) {
  const racine = document.documentElement;
  if (theme === "auto") racine.removeAttribute("data-theme");
  else racine.setAttribute("data-theme", theme === "sombre" ? "dark" : theme === "penombre" ? "dim" : "light");
  // index.html porte une couleur par thème de l'appareil ; un thème imposé les aligne toutes deux sur lui.
  document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach((m) => {
    const propre = m.media.includes("dark") ? FOND.sombre : FOND.clair;
    m.content = theme === "auto" ? propre : FOND[theme];
  });
}

export function choisirTheme(theme: Theme) {
  try { if (theme === "auto") localStorage.removeItem(CLE); else localStorage.setItem(CLE, theme); } catch { /* ce navigateur ne garde rien */ }
  appliquerTheme(theme);
}
