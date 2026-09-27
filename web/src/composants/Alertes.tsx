import { Link } from "react-router-dom";

import type { Alerte } from "../types";
import { t } from "../i18n";

/** Les niveaux d'une alerte. Une fonction : la langue se lit au rendu. */
export const niveauxAlerte = () => ({
  grave: { libelle: t("À traiter", "To handle"), classe: "grave" },
  attention: { libelle: t("À surveiller", "To watch"), classe: "attention" },
  info: { libelle: t("À savoir", "Good to know"), classe: "neutre" },
}) as const;

/** Les points d'attention d'un dossier : ce qui attend, qui doit agir, et un lien vers la page. */
export function PointsAttention({ alertes }: { alertes: Alerte[] }) {
  const NIVEAUX = niveauxAlerte();
  return (
    <section className="section" aria-label={t("Points d'attention", "Points of attention")}>
      <h2>{t("Points d'attention", "Points of attention")}</h2>
      {alertes.length === 0 ? <p className="discret">{t("Rien à signaler : le dossier est à jour.", "Nothing to report: the file is up to date.")}</p> : (
        <ul className="alertes">
          {alertes.map((a) => (
            <li key={`${a.code}-${a.lien}`} className={`alerte ${NIVEAUX[a.niveau].classe}`}>
              <div>
                <span className={`etat ${NIVEAUX[a.niveau].classe}`}>{NIVEAUX[a.niveau].libelle}</span>
                <strong>{a.titre}</strong>
                <p>{a.detail}</p>
                <span className="discret">{a.pour === "entreprise" ? t("L'entreprise agit.", "The company acts.") : t("Le conseiller agit.", "The adviser acts.")}</span>
              </div>
              <Link to={a.lien} className="bouton">{t("Ouvrir", "Open")}</Link>
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
  if (parts.length === 0) return <span className="etat bien">{t("À jour", "Up to date")}</span>;
  const NIVEAUX = niveauxAlerte();
  return (
    <span className="decompte">
      {parts.map((n) => <span key={n} className={`etat ${NIVEAUX[n].classe}`}>{decompte[n]} {NIVEAUX[n].libelle.toLowerCase()}</span>)}
    </span>
  );
}
