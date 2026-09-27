import { Link } from "react-router-dom";

import { dateFr, montant, pct } from "../format";
import { langue, t } from "../i18n";
import type { Experience as E } from "../types";

/** Ce que les départs enregistrés disent de l'étude : l'attendu contre le réel, la rotation observée. */
export default function Experience({ x, peutProposer }: { x: E; peutProposer: boolean }) {
  const r = x.rotation;
  const suite = r.proposition
    ? `../?turnover=${r.proposition.taux_turnover}&justification=${encodeURIComponent(r.proposition.justification)}`
    : null;
  return (
    <div className="carte section" data-experience>
      <h2>{t("L'expérience réelle", "Actual experience")}</h2>
      <p className="discret">{t("Les départs enregistrés, lus à la date d'évaluation", "Recorded departures, read at the valuation date")}
        {x.etude_precedente ? t(`, face à l'étude du ${dateFr(x.etude_precedente.date_evaluation)}`,
          `, compared with the study of ${dateFr(x.etude_precedente.date_evaluation)}`) : ""}.</p>
      {x.attendu_contre_reel.length > 0 && (
        <div className="defile"><table>
          <thead><tr><th>{t("Année", "Year")}</th><th className="n">{t("Retraites prévues", "Expected retirements")}</th>
            <th className="n">{t("Prestations prévues", "Expected benefits")}</th>
            <th className="n">{t("Retraites réelles", "Actual retirements")}</th><th className="n">{t("Dû", "Due")}</th>
            <th className="n">{t("Versé", "Paid")}</th></tr></thead>
          <tbody>{x.attendu_contre_reel.map((l) => (
            <tr key={l.annee}><td>{l.annee}</td>
              <td className="n">{l.attendu_retraites ?? "—"}</td>
              <td className="n">{l.attendu_prestations === null ? "—" : montant(l.attendu_prestations)}</td>
              <td className="n">{l.reel_retraites}</td><td className="n">{montant(l.reel_du)}</td><td className="n">{montant(l.reel_verse)}</td></tr>
          ))}</tbody>
        </table></div>
      )}
      <div className="section">
        <h3>{t("Rotation du personnel", "Staff turnover")}</h3>
        <p>{r.message}</p>
        {r.taux !== null && (
          langue() === "en"
          ? <p className="discret">{r.departs} resignation(s) and dismissal(s) over {r.annees} year(s), for {r.effectif} employees:
            {" "}{pct(r.taux)} a year observed, {pct(r.taux_hypothese)} assumed in this study.</p>
          : <p className="discret">{r.departs} démission(s) et licenciement(s) en {r.annees} an(s), pour {r.effectif} salariés :
            {" "}{pct(r.taux)} par an observés, {pct(r.taux_hypothese)} supposés dans cette étude.</p>
        )}
        {r.proposition && (
          <div className="constat informe">
            <div className="titre">{t("Hypothèse proposée :", "Proposed assumption:")} {pct(r.proposition.taux_turnover)}</div>
            <p>{t("Elle n'est pas appliquée à cette étude. La retenir est une décision, justifiée, dans une nouvelle étude.",
              "It is not applied to this study. Adopting it is a justified decision, made in a new study.")}</p>
            {peutProposer && suite && <Link to={suite}>{t("Préparer une étude avec cette rotation", "Prepare a study with this turnover")}</Link>}
          </div>
        )}
      </div>
      {x.paiements_du_fonds.montant > 0 && (
        langue() === "en"
          ? <p className="discret">The fund has paid {montant(x.paiements_du_fonds.montant)} in benefits
            {x.paiements_du_fonds.depuis ? ` since ${dateFr(x.paiements_du_fonds.depuis)}` : ""}: the fund declared for
            this study must take this into account.</p>
          : <p className="discret">Le fonds a payé {montant(x.paiements_du_fonds.montant)} de prestations
          {x.paiements_du_fonds.depuis ? ` depuis le ${dateFr(x.paiements_du_fonds.depuis)}` : ""} : le fonds déclaré pour
          cette étude doit en tenir compte.</p>
      )}
    </div>
  );
}
