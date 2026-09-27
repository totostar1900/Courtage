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
import { t } from "../i18n";
import type { Annee } from "../types";

type Etude = { statut: string; date_evaluation: string; fonds_disponible: number; echeancier: Annee[];
               totaux: { effectif: number; dette: number } };
const etudes = Object.values(donnees.reponses as Record<string, unknown>)
  .filter((v): v is Etude => typeof v === "object" && v !== null && "echeancier" in v);
const etude = etudes.find((e) => e.statut === "emise") ?? etudes[0];

const essais = () => [
  [t("Mesure", "Measure"), t("prestations probables, indemnité si tous partent, valeur actuelle, ou le nombre de départs.",
    "probable benefits, benefit if everyone leaves, present value, or the number of departures.")],
  [t("Lecture", "View"), t("« Cumulée » additionne les années : la ligne en pointillés est le fonds déjà constitué, et la phrase sous le graphique dit jusqu'à quand il couvre les départs.",
    "“Cumulative” adds the years together: the dotted line is the fund already accumulated, and the sentence below the chart says until when it covers departures.")],
  [t("Découpage", "Breakdown"), t("« Par catégorie » sépare les cadres des autres salariés ; la bulle détaille chaque catégorie.",
    "“By category” separates managers from other employees; the tooltip details each category.")],
  [t("Horizon", "Horizon"), t("les 10 ou 20 premières années, ou tout l'échéancier.", "the first 10 or 20 years, or the whole schedule.")],
  [t("Survol", "Hover"), t("chaque barre ouvre sa bulle (au clavier aussi) ; « Voir le tableau » donne les mêmes chiffres.",
    "each bar opens its tooltip (from the keyboard too); “Show the table” gives the same figures.")],
];

function Maquette() {
  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "28px 16px 48px" }}>
      <p className="discret" style={{ margin: 0 }}>{t("Maquette · Société Démo SA (fictive) · 40 salariés inventés",
        "Mock-up · Société Démo SA (fictitious) · 40 made-up employees")}</p>
      <h1 style={{ marginTop: 4 }}>{t("Départs prévus : l'échéancier modulable", "Expected departures: the adjustable schedule")}</h1>
      <p>{t(`L'étude au ${etude.date_evaluation.split("-").reverse().join("/")} : ${etude.totaux.effectif} salariés, `
        + `une dette actuarielle de ${montant(etude.totaux.dette)}, un fonds constitué de ${montant(etude.fonds_disponible)}. `
        + "Le graphique ci-dessous est celui de la plateforme, avec ses vrais chiffres.",
        `The study at ${etude.date_evaluation.split("-").reverse().join("/")}: ${etude.totaux.effectif} employees, `
        + `an actuarial liability of ${montant(etude.totaux.dette)}, an accumulated fund of ${montant(etude.fonds_disponible)}. `
        + "The chart below is the platform's own, with its real figures.")}</p>
      <div className="carte section">
        <h3>{t("Départs prévus", "Expected departures")}</h3>
        <Echeancier annees={etude.echeancier} fonds={etude.fonds_disponible} />
      </div>
      <div className="carte section">
        <h3>{t("À essayer", "Try it")}</h3>
        <dl className="essais">
          {essais().map(([n, d]) => <div key={n}><dt>{n}</dt><dd>{d}</dd></div>)}
        </dl>
      </div>
    </main>
  );
}

createRoot(document.getElementById("racine")!).render(<StrictMode><Maquette /></StrictMode>);
