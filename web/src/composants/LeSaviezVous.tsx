import { useState } from "react";
import { Link } from "react-router-dom";

import { ASTUCES, astuceDuJour } from "../guide/astuces";
import { t } from "../i18n";

const CLE = "courtage:astuce-fermee";
const aujourdhui = () => new Date().toISOString().slice(0, 10);

/** « Le saviez-vous ? » : une astuce par jour, une autre sur demande, refermée jusqu'à demain. */
export default function LeSaviezVous() {
  const [n, setN] = useState(astuceDuJour);
  const [fermee, setFermee] = useState(() => { try { return localStorage.getItem(CLE) === aujourdhui(); } catch { return false; } });
  if (fermee) return null;
  const a = ASTUCES[n];
  const fermer = () => { try { localStorage.setItem(CLE, aujourdhui()); } catch { /* rien */ } setFermee(true); };
  return (
    <aside className="carte astuce section" aria-label={t("Le saviez-vous ?", "Did you know?")}>
      <div className="volet-tete">
        <strong>💡 {t("Le saviez-vous ?", "Did you know?")}</strong>
        <button type="button" className="fermer-volet" onClick={fermer} aria-label={t("Fermer l'astuce", "Close the tip")} title={t("Fermer jusqu'à demain", "Close until tomorrow")}>×</button>
      </div>
      <p style={{ margin: "6px 0" }}>{a.texte}</p>
      <div className="actions" style={{ marginTop: 4 }}>
        {a.chapitre && <Link to={`/guide/${a.chapitre}`}>{t("En savoir plus", "Learn more")}</Link>}
        {a.lecon && <Link to={`/guide/lecons/${a.lecon}`}>{t("La leçon (2 min)", "The lesson (2 min)")}</Link>}
        <button type="button" className="lien" onClick={() => setN((n + 1) % ASTUCES.length)}>{t("Une autre astuce", "Another tip")}</button>
      </div>
    </aside>
  );
}
