import { Link } from "react-router-dom";

import { api } from "../api";
import { PointsAttention } from "../composants/Alertes";
import { Cle, Constats, useCharge } from "../composants/communs";
import { dateFr, millions, montant } from "../format";
import { etapes } from "../parcours";
import Rapprochement, { sousCotisation } from "../composants/Rapprochement";
import type { Alerte, Etude } from "../types";
import LeSaviezVous from "../composants/LeSaviezVous";
import AnneeDossier from "../composants/AnneeDossier";
import { useDossier } from "./Dossier";
import { t } from "../i18n";

export default function TableauDeBord() {
  const d = useDossier();
  const suivante = etapes(d.etat).find((e) => e.suivant);
  const derniere = d.etudes.find((e) => e.statut === "emise") ?? d.etudes[0];
  const { donnee: etude } = useCharge(
    () => (derniere ? api.get<Etude>(`/organisations/${d.org.id}/etudes/${derniere.id}`) : Promise.resolve(null)),
    [derniere?.id],
  );

  const { donnee: alertes } = useCharge(() => api.get<Alerte[]>(`/organisations/${d.org.id}/alertes`), [d.org.id]);

  return (
    <>
      <h1>{t("Où en est votre dossier", "Where your file stands")}</h1>
      {alertes && alertes.length > 0 && <PointsAttention alertes={alertes} />}
      {suivante ? (
        <div className="carte" style={{ borderColor: "var(--ocre)" }} data-visite="prochaine">
          <div className="discret">{t("Prochaine étape", "Next step")}</div>
          <h2 style={{ margin: "4px 0" }}>{suivante.libelle}</h2>
          <p>{suivante.aide}</p>
          <Link to={suivante.cle}><button className="principal">{t("Continuer", "Continue")}</button></Link>
        </div>
      ) : (
        <div className="carte" data-visite="prochaine"><h2>{t("Toutes les étapes sont faites.", "All steps are done.")}</h2>
          <p>{t("Le cahier des charges est parti : les réponses des assureurs viendront s'y comparer.",
                "The specifications have gone out: the insurers' responses will be compared against them.")}</p></div>
      )}

      <AnneeDossier orgId={d.org.id} />

      {etude && (
        <div className="section">
          <h2>{etude.statut === "emise" ? t("Votre engagement", "Your liability") : t("Dernier brouillon", "Latest draft")}
            {" "}{t("au", "as at")} {dateFr(etude.date_evaluation)}</h2>
          <div className="grille g4" data-visite="chiffres">
            <Cle etiquette={t("Dette actuarielle", "Actuarial liability")} terme="dette" valeur={millions(etude.totaux.dette)} sous={montant(etude.totaux.dette)} />
            <Cle etiquette={t("Charge annuelle", "Annual cost")} terme="charge" valeur={millions(etude.totaux.charge)} sous={`${montant(etude.totaux.charge)} · ${t("une année de plus", "one more year")}`} />
            <Cle etiquette={t("Fonds constitué", "Fund built up")} terme="fonds" valeur={millions(etude.fonds_disponible)} sous={montant(etude.fonds_disponible)} />
            <Cle etiquette={t("Cotisation à verser", "Contribution to pay")} terme="cotisation" valeur={millions(etude.totaux.cotisation_totale ?? 0)}
                 sous={sousCotisation(etude)} />
          </div>
          <details className="carte section repli">
            <summary>{t("Comment on arrive à la cotisation", "How the contribution is reached")}</summary>
            <Rapprochement etude={etude} titre={false} />
          </details>
          <div className="section">
            <Constats constats={etude.anomalies.filter((a) => a.niveau === "avertissement").slice(0, 3).map((a) => ({
              niveau: "avertit", code: a.code, message: a.message }))} vide="" />
          </div>
          <Link to={`etudes/${etude.id}`}>{t("Voir l'étude complète", "See the full study")}</Link>
        </div>
      )}
      <LeSaviezVous />
    </>
  );
}
