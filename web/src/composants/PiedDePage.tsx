import { Link } from "react-router-dom";

import { useCabinet } from "../cabinet";
import { t } from "../i18n";

/** Sur chaque écran : la marque, le cabinet qui exploite la plateforme (son nom légal), et les pages légales. */
export default function PiedDePage() {
  const c = useCabinet();
  return (
    <footer className="pied">
      <div className="interieur">
        <div>Nitch{c && <> · {t("exploitée par", "operated by")} {c.nom}, {t("courtier agréé", "licensed broker")} {c.agrement}</>}</div>
        <nav aria-label={t("Pages légales", "Legal pages")}>
          <Link to="/ifc">{t("Les IFC", "End-of-service benefits")}</Link>
          <Link to="/mentions-legales">{t("Mentions légales", "Legal notice")}</Link>
          <Link to="/conditions">{t("Conditions d'utilisation", "Terms of use")}</Link>
          <Link to="/confidentialite">{t("Confidentialité", "Privacy")}</Link>
          <Link to="/guide">{t("Guide", "Guide")}</Link>
          <Link to="/verifier">{t("Vérifier un document", "Verify a document")}</Link>
        </nav>
      </div>
    </footer>
  );
}
