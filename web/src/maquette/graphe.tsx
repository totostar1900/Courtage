/** La maquette de l'échéancier des départs : le VRAI composant, sur l'étude émise de la Société Démo SA
 *  (fictive, capturée depuis l'API par scripts/capturer_demo.py). `npm run maquette`. */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "@fontsource/figtree/latin-400.css";
import "@fontsource/figtree/latin-500.css";
import "@fontsource/figtree/latin-600.css";
import "@fontsource/figtree/latin-700.css";
import "@fontsource/young-serif/latin-400.css";
import "../styles.css";
import { Echeancier } from "../composants/Echeancier";
import donnees from "../demo/donnees.json";
import { montant } from "../format";
import type { Annee } from "../types";

type Etude = { statut: string; date_evaluation: string; fonds_disponible: number; echeancier: Annee[];
               totaux: { effectif: number; dette: number } };
const etudes = Object.values(donnees.reponses as Record<string, unknown>)
  .filter((v): v is Etude => typeof v === "object" && v !== null && "echeancier" in v);
const etude = etudes.find((e) => e.statut === "emise") ?? etudes[0];

const ESSAIS = [
  ["Mesure", "prestations probables, indemnité si tous partent, valeur actuelle, ou le nombre de départs."],
  ["Lecture", "« Cumulée » additionne les années : la ligne en pointillés est le fonds déjà constitué, et la phrase sous le graphique dit jusqu'à quand il couvre les départs."],
  ["Découpage", "« Par catégorie » sépare les cadres des autres salariés ; la bulle détaille chaque catégorie."],
  ["Horizon", "les 10 ou 20 premières années, ou tout l'échéancier."],
  ["Survol", "chaque barre ouvre sa bulle (au clavier aussi) ; « Voir le tableau » donne les mêmes chiffres."],
];

function Maquette() {
  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "28px 16px 48px" }}>
      <p className="discret" style={{ margin: 0 }}>Maquette · Société Démo SA (fictive) · 40 salariés inventés</p>
      <h1 style={{ marginTop: 4 }}>Départs prévus : l'échéancier modulable</h1>
      <p>L'étude au {etude.date_evaluation.split("-").reverse().join("/")} : {etude.totaux.effectif} salariés,
        une dette actuarielle de {montant(etude.totaux.dette)}, un fonds constitué de {montant(etude.fonds_disponible)}.
        Le graphique ci-dessous est celui de la plateforme, avec ses vrais chiffres.</p>
      <div className="carte section">
        <h3>Départs prévus</h3>
        <Echeancier annees={etude.echeancier} fonds={etude.fonds_disponible} />
      </div>
      <div className="carte section">
        <h3>À essayer</h3>
        <dl className="essais">
          {ESSAIS.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}
        </dl>
      </div>
    </main>
  );
}

createRoot(document.getElementById("racine")!).render(<StrictMode><Maquette /></StrictMode>);
