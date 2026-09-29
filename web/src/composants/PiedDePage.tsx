import { Link } from "react-router-dom";

import { useCabinet } from "../cabinet";
import { t } from "../i18n";

/** Sur chaque écran : qui exploite la plateforme, et les pages légales. */
export default function PiedDePage() {
  const c = useCabinet();
  return (
    <footer className="pied">
      <div className="interieur">
        <div>{c ? <>{c.nom} · {t("courtier agréé", "licensed broker")} {c.agrement}</> : "courtage."}</div>
        <nav aria-label={t("Pages légales", "Legal pages")}>
          <Link to="/mentions-legales">{t("Mentions légales", "Legal notice")}</Link>
          <Link to="/conditions">{t("Conditions d'utilisation", "Terms of use")}</Link>
          <Link to="/confidentialite">{t("Confidentialité", "Privacy")}</Link>
          <Link to="/guide">{t("Guide", "Guide")}</Link>
        </nav>
      </div>
    </footer>
  );
}
