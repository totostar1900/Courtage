import { useState } from "react";

import { millions, montant, pct } from "../format";
import { langue, t } from "../i18n";
import type { Financement as Resultat } from "../types";

/** Le détail des projections : chaque offre sous les trois scénarios, sur les mêmes cotisations et les mêmes départs. */
export function Comparaison({ r }: { r: Resultat }) {
  const [detail, setDetail] = useState<string | null>(null);
  const ref = r.scenario_de_reference;
  const ordonnees = [...r.offres].sort((a, b) => r.classement.indexOf(a.nom) - r.classement.indexOf(b.nom));
  return (
    <div className="section">
      {langue() === "en" ? (
        <p>Past service to catch up: <strong>{montant(r.plan_amortissement.deficit_initial)}</strong>
          {r.plan_amortissement.annees > 1 && ` in ${r.plan_amortissement.annees} annual instalments of ${montant(r.plan_amortissement.annuite)}`}.
          Ranked on the “{ref}” scenario.</p>
      ) : (
      <p>Passé à rattraper : <strong>{montant(r.plan_amortissement.deficit_initial)}</strong>
        {r.plan_amortissement.annees > 1 && ` en ${r.plan_amortissement.annees} annuités de ${montant(r.plan_amortissement.annuite)}`}.
        Classement sur le scénario « {ref} ».</p>
      )}
      <div className="grille g3">
        {ordonnees.map((o, i) => {
          const s = o.scenarios.find((x) => x.scenario === ref) ?? o.scenarios[0];
          return (
            <div key={o.nom} className={`carte offre ${i === 0 ? "meilleure" : ""}`} data-offre={o.nom}>
              {i === 0 && <span className="badge">{t("Le coût net le plus bas", "Lowest net cost")}</span>}
              <h3 style={{ marginTop: 6 }}>{o.nom}</h3>
              <div className="discret">{t(`Coût net actualisé sur ${s.annees.length} ans`, `Discounted net cost over ${s.annees.length} years`)}</div>
              <div className="gros">{millions(s.cout_net_actualise)}</div>
              <div className="lignes-offre">
                <div><span>{t("Frais payés", "Charges paid")}</span><span className="chiffre">{montant(s.frais_totaux)}</span></div>
                <div><span>{t("Fonds à l'horizon", "Fund at the horizon")}</span><span className="chiffre">{montant(s.fonds_final)}</span></div>
                <div><span>{t("Couverture des départs restants", "Coverage of remaining departures")}</span><span className="chiffre">{s.couverture_des_departs_restants === null ? "—" : pct(s.couverture_des_departs_restants, 0)}</span></div>
                <div><span>{t("Années sans fonds suffisant", "Years without sufficient fund")}</span>
                  {s.annees_decouvert.length ? <span className="etat grave">{s.annees_decouvert.join(", ")}</span> : <span className="etat bien">{t("aucune", "none")}</span>}</div>
                {!o.interne && <div><span>{t("Taux garanti · frais", "Guaranteed rate · charges")}</span><span className="chiffre">{pct(o.conditions.taux_garanti)} · {pct(o.conditions.frais_sur_cotisations)}</span></div>}
              </div>
              <div className="actions"><button onClick={() => setDetail(detail === o.nom ? null : o.nom)}>{detail === o.nom ? t("Replier", "Collapse") : t("Selon les scénarios", "By scenario")}</button></div>
              {detail === o.nom && (
                <table><tbody>{o.scenarios.map((x) => (
                  <tr key={x.scenario}><td>{x.scenario} ({pct(x.rendement)})</td><td className="n">{millions(x.cout_net_actualise)}</td></tr>
                ))}</tbody></table>
              )}
            </div>
          );
        })}
      </div>
      <p className="discret section">{t("Le coût net actualisé retranche le fonds restant à l'horizon, qui vous appartient et "
        + "financera les départs suivants : il peut être négatif. Il sert à comparer les offres entre elles.",
        "The discounted net cost deducts the fund remaining at the horizon, which belongs to you and will fund later "
        + "departures: it can be negative. It is used to compare the offers with one another.")}</p>
    </div>
  );
}
