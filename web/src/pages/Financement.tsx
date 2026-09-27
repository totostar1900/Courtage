import { useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, Volet } from "../composants/communs";
import { millions, montant, pct } from "../format";
import { langue, t } from "../i18n";
import type { Financement as Resultat, Offre } from "../types";
import { useDossier } from "./Dossier";

const OFFRE_VIDE: Offre = { nom: "", taux_garanti: 0.025, participation_benefices: 0.85, frais_sur_cotisations: 0.04, frais_sur_encours: 0 };

export default function Financement() {
  const d = useDossier();
  const { etude: depuisUrl } = useParams();
  const [etude, setEtude] = useState(depuisUrl ?? d.etudes.find((e) => e.statut === "emise")?.id ?? d.etudes[0]?.id ?? "");
  const [offres, setOffres] = useState<Offre[]>([{ ...OFFRE_VIDE, nom: t("Assureur A", "Insurer A") }]);
  const [horizon, setHorizon] = useState(10);
  const [amortissement, setAmortissement] = useState(3);
  const [resultat, setResultat] = useState<Resultat | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);

  async function comparer() {
    setErreur(null);
    try {
      setResultat(await api.post<Resultat>(`/organisations/${d.org.id}/etudes/${etude}/financement`,
        { horizon, amortissement_annees: amortissement, offres: offres.filter((o) => o.nom.trim()) }));
    } catch (e) { setErreur(e); }
  }
  const maj = (i: number, champ: Partial<Offre>) => setOffres(offres.map((o, j) => (j === i ? { ...o, ...champ } : o)));

  if (!d.etudes.length) return <><h1>{t("Financer", "Funding")}</h1><p>{t("Lancez d'abord une étude.", "Start a study first.")}</p></>;

  return (
    <>
      <h1>{t("Financer votre engagement", "Fund your liability")}</h1>
      <p>{t("Chaque offre reçoit les mêmes cotisations et paie les mêmes départs ; on compare ce qu'elle en fait, sous "
        + "trois scénarios de rendement. La provision interne, garder l'argent chez vous, est toujours dans la comparaison.",
        "Each offer receives the same contributions and pays the same departures; we compare what it does with them under "
        + "three return scenarios. The internal provision, keeping the money in-house, is always part of the comparison.")}</p>
      <div className="carte formulaire">
        <div className="grille g3">
          <label>{t("Étude", "Study")}
            <select value={etude} onChange={(e) => setEtude(e.target.value)}>
              {d.etudes.map((e) => <option key={e.id} value={e.id}>{e.date_evaluation} · {millions(e.dette)} · {e.statut}</option>)}
            </select>
          </label>
          <label>{t("Horizon (années)", "Horizon (years)")}<input type="number" min={1} max={30} value={horizon} onChange={(e) => setHorizon(Math.min(30, Math.max(1, Number(e.target.value))))} /></label>
          <label>{t("Rattraper le passé en (années)", "Catch up on past service over (years)")}<input type="number" min={1} max={horizon} value={amortissement} onChange={(e) => setAmortissement(Number(e.target.value))} /></label>
        </div>
        <h3>{t("Offres reçues ou envisagées", "Offers received or considered")}</h3>
        {offres.map((o, i) => (
          <div key={i} className="grille g4" style={{ alignItems: "end" }}>
            <label>{t("Assureur", "Insurer")}<input value={o.nom} onChange={(e) => maj(i, { nom: e.target.value })} /></label>
            <label>{t("Taux garanti (%)", "Guaranteed rate (%)")}<input type="number" step={0.1} value={o.taux_garanti * 100} onChange={(e) => maj(i, { taux_garanti: Number(e.target.value) / 100 })} /></label>
            <label>{t("Frais sur cotisations (%)", "Charges on contributions (%)")}<input type="number" step={0.1} value={o.frais_sur_cotisations * 100} onChange={(e) => maj(i, { frais_sur_cotisations: Number(e.target.value) / 100 })} /></label>
            <label>{t("Frais sur encours (%/an)", "Charges on assets (%/year)")}<input type="number" step={0.1} value={o.frais_sur_encours * 100} onChange={(e) => maj(i, { frais_sur_encours: Number(e.target.value) / 100 })} /></label>
          </div>
        ))}
        <div className="actions">
          <button type="button" onClick={() => setOffres([...offres, {
            nom: t(`Assureur ${String.fromCharCode(65 + offres.length)}`, `Insurer ${String.fromCharCode(65 + offres.length)}`), taux_garanti: 0.02, participation_benefices: 0.9,
            frais_sur_cotisations: 0.02, frais_sur_encours: 0.005 }])}>{t("Ajouter une offre", "Add an offer")}</button>
          <button className="principal" onClick={comparer} disabled={!etude}>{t("Comparer", "Compare")}</button>
        </div>
        <Erreur erreur={erreur} />
      </div>
      {resultat && (
        <Volet titre={t("Comparaison des offres", "Comparison of offers")} onFermer={() => setResultat(null)} className="section">
          <Comparaison r={resultat} />
        </Volet>
      )}
    </>
  );
}

/** Les offres en cartes, la moins chère marquée (Check24), le détail replié. */
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
              {i === 0 && <span className="badge">{t("Le moins cher", "Cheapest")}</span>}
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
