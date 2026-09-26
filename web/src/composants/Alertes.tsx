import { Link } from "react-router-dom";

import type { Alerte } from "../types";

export const NIVEAUX = {
  grave: { libelle: "À traiter", classe: "grave" },
  attention: { libelle: "À surveiller", classe: "attention" },
  info: { libelle: "À savoir", classe: "neutre" },
} as const;
const POUR = { entreprise: "L'entreprise", conseiller: "Le conseiller" } as const;

/** Les points d'attention d'un dossier : ce qui attend, qui doit agir, et un lien vers la page. */
export function PointsAttention({ alertes }: { alertes: Alerte[] }) {
  return (
    <section className="section" aria-label="Points d'attention">
      <h2>Points d'attention</h2>
      {alertes.length === 0 ? <p className="discret">Rien à signaler : le dossier est à jour.</p> : (
        <ul className="alertes">
          {alertes.map((a) => (
            <li key={`${a.code}-${a.lien}`} className={`alerte ${NIVEAUX[a.niveau].classe}`}>
              <div>
                <span className={`etat ${NIVEAUX[a.niveau].classe}`}>{NIVEAUX[a.niveau].libelle}</span>
                <strong>{a.titre}</strong>
                <p>{a.detail}</p>
                <span className="discret">{POUR[a.pour]} agit.</span>
              </div>
              <Link to={a.lien} className="bouton">Ouvrir</Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Le décompte d'un dossier, sur sa carte de « Vos dossiers ». */
export function DecompteAlertes({ decompte }: { decompte?: Record<Alerte["niveau"], number> }) {
  if (!decompte) return null;
  const parts = (["grave", "attention"] as const).filter((n) => decompte[n] > 0);
  if (parts.length === 0) return <span className="etat bien">À jour</span>;
  return (
    <span className="decompte">
      {parts.map((n) => <span key={n} className={`etat ${NIVEAUX[n].classe}`}>{decompte[n]} {NIVEAUX[n].libelle.toLowerCase()}</span>)}
    </span>
  );
}
