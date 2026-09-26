import { Link } from "react-router-dom";

import { dateFr, montant, pct } from "../format";
import type { Experience as E } from "../types";

/** Ce que les départs enregistrés disent de l'étude : l'attendu contre le réel, la rotation observée. */
export default function Experience({ x, peutProposer }: { x: E; peutProposer: boolean }) {
  const r = x.rotation;
  const suite = r.proposition
    ? `../?turnover=${r.proposition.taux_turnover}&justification=${encodeURIComponent(r.proposition.justification)}`
    : null;
  return (
    <div className="carte section" data-experience>
      <h2>L'expérience réelle</h2>
      <p className="discret">Les départs enregistrés, lus à la date d'évaluation
        {x.etude_precedente ? `, face à l'étude du ${dateFr(x.etude_precedente.date_evaluation)}` : ""}.</p>
      {x.attendu_contre_reel.length > 0 && (
        <div className="defile"><table>
          <thead><tr><th>Année</th><th className="n">Retraites prévues</th><th className="n">Prestations prévues</th>
            <th className="n">Retraites réelles</th><th className="n">Dû</th><th className="n">Versé</th></tr></thead>
          <tbody>{x.attendu_contre_reel.map((l) => (
            <tr key={l.annee}><td>{l.annee}</td>
              <td className="n">{l.attendu_retraites ?? "—"}</td>
              <td className="n">{l.attendu_prestations === null ? "—" : montant(l.attendu_prestations)}</td>
              <td className="n">{l.reel_retraites}</td><td className="n">{montant(l.reel_du)}</td><td className="n">{montant(l.reel_verse)}</td></tr>
          ))}</tbody>
        </table></div>
      )}
      <div className="section">
        <h3>Rotation du personnel</h3>
        <p>{r.message}</p>
        {r.taux !== null && (
          <p className="discret">{r.departs} démission(s) et licenciement(s) en {r.annees} an(s), pour {r.effectif} salariés :
            {" "}{pct(r.taux)} par an observés, {pct(r.taux_hypothese)} supposés dans cette étude.</p>
        )}
        {r.proposition && (
          <div className="constat informe">
            <div className="titre">Hypothèse proposée : {pct(r.proposition.taux_turnover)}</div>
            <p>Elle n'est pas appliquée à cette étude. La retenir est une décision, justifiée, dans une nouvelle étude.</p>
            {peutProposer && suite && <Link to={suite}>Préparer une étude avec cette rotation</Link>}
          </div>
        )}
      </div>
      {x.paiements_du_fonds.montant > 0 && (
        <p className="discret">Le fonds a payé {montant(x.paiements_du_fonds.montant)} de prestations
          {x.paiements_du_fonds.depuis ? ` depuis le ${dateFr(x.paiements_du_fonds.depuis)}` : ""} : le fonds déclaré pour
          cette étude doit en tenir compte.</p>
      )}
    </div>
  );
}
