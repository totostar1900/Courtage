import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, MemoryRouter } from "react-router-dom";

import { DEMO } from "./api";
import App from "./App";
// Les polices sont servies par la plateforme : aucune requête vers un tiers (Google Fonts),
// qui dirait à un autre qui consulte quoi, et qui manque quand le réseau le bloque.
import "@fontsource/geist-sans/latin-400.css";
import "@fontsource/geist-sans/latin-500.css";
import "@fontsource/geist-sans/latin-600.css";
import "@fontsource/geist-sans/latin-700.css";
import "@fontsource/geist-mono/latin-400.css";
import "@fontsource/geist-mono/latin-500.css";
import "./styles.css";
import { appliquerTheme, lireTheme } from "./theme";

// Le thème choisi est posé avant le premier rendu : pas d'éclair clair sur un écran sombre.
appliquerTheme(lireTheme());

createRoot(document.getElementById("racine")!).render(
  <StrictMode>
    {DEMO ? (
      // Une page publiée n'a pas d'adresses : la navigation vit en mémoire.
      <MemoryRouter initialEntries={["/connexion"]}><App /></MemoryRouter>
    ) : (
      <BrowserRouter><App /></BrowserRouter>
    )}
  </StrictMode>,
);
