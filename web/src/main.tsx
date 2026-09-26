import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, MemoryRouter } from "react-router-dom";

import { DEMO } from "./api";
import App from "./App";
// Les polices sont servies par la plateforme : aucune requête vers un tiers (Google Fonts),
// qui dirait à un autre qui consulte quoi, et qui manque quand le réseau le bloque.
import "@fontsource/figtree/latin-400.css";
import "@fontsource/figtree/latin-500.css";
import "@fontsource/figtree/latin-600.css";
import "@fontsource/figtree/latin-700.css";
import "@fontsource/young-serif/latin-400.css";
import "./styles.css";

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
