import { useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, Volet } from "../composants/communs";
import { millions, montant, pct } from "../format";
import type { Financement as Resultat, Offre } from "../types";
import { useDossier } from "./Dossier";

const OFFRE_VIDE: Offre = { nom: "", taux_garanti: 0.025, participation_benefices: 0.85, frais_sur_cotisations: 0.04, frais_sur_encours: 0 };

export default function Financement() {
  const d = useDossier();
  const { etude: depuisUrl } = useParams();
  const [etude, setEtude] = useState(depuisUrl ?? d.etudes.find((e) => e.statut === "emise")?.id ?? d.etudes[0]?.id ?? "");
  const [offres, setOffres] = useState<Offre[]>([{ ...OFFRE_VIDE, nom: "Assureur A" }]);
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

  if (!d.etudes.length) return <><h1>Financer</h1><p>Lancez d'abord une étude.</p></>;

  return (
    <>
      <h1>Financer votre engagement</h1>
      <p>Chaque offre reçoit les mêmes cotisations et paie les mêmes départs ; on compare ce qu'elle en fait, sous
        trois scénarios de rendement. La provision interne, garder l'argent chez vous, est toujours dans la comparaison.</p>
      <div className="carte formulaire">
        <div className="grille g3">
          <label>Étude
            <select value={etude} onChange={(e) => setEtude(e.target.value)}>
              {d.etudes.map((e) => <option key={e.id} value={e.id}>{e.date_evaluation} · {millions(e.dette)} · {e.statut}</option>)}
            </select>
          </label>
          <label>Horizon (années)<input type="number" min={1} max={40} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} /></label>
          <label>Rattraper le passé en (années)<input type="number" min={1} max={horizon} value={amortissement} onChange={(e) => setAmortissement(Number(e.target.value))} /></label>
        </div>
        <h3>Offres reçues ou envisagées</h3>
        {offres.map((o, i) => (
          <div key={i} className="grille g4" style={{ alignItems: "end" }}>
            <label>Assureur<input value={o.nom} onChange={(e) => maj(i, { nom: e.target.value })} /></label>
            <label>Taux garanti (%)<input type="number" step={0.1} value={o.taux_garanti * 100} onChange={(e) => maj(i, { taux_garanti: Number(e.target.value) / 100 })} /></label>
            <label>Frais sur cotisations (%)<input type="number" step={0.1} value={o.frais_sur_cotisations * 100} onChange={(e) => maj(i, { frais_sur_cotisations: Number(e.target.value) / 100 })} /></label>
            <label>Frais sur encours (%/an)<input type="number" step={0.1} value={o.frais_sur_encours * 100} onChange={(e) => maj(i, { frais_sur_encours: Number(e.target.value) / 100 })} /></label>
          </div>
        ))}
        <div className="actions">
          <button type="button" onClick={() => setOffres([...offres, {
            nom: `Assureur ${String.fromCharCode(65 + offres.length)}`, taux_garanti: 0.02, participation_benefices: 0.9,
            frais_sur_cotisations: 0.02, frais_sur_encours: 0.005 }])}>Ajouter une offre</button>
          <button className="principal" onClick={comparer} disabled={!etude}>Comparer</button>
        </div>
        <Erreur erreur={erreur} />
      </div>
      {resultat && (
        <Volet titre="Comparaison des offres" onFermer={() => setResultat(null)} className="section">
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
      <p>Passé à rattraper : <strong>{montant(r.plan_amortissement.deficit_initial)}</strong>
        {r.plan_amortissement.annees > 1 && ` en ${r.plan_amortissement.annees} annuités de ${montant(r.plan_amortissement.annuite)}`}.
        Classement sur le scénario « {ref} ».</p>
      <div className="grille g3">
        {ordonnees.map((o, i) => {
          const s = o.scenarios.find((x) => x.scenario === ref) ?? o.scenarios[0];
          return (
            <div key={o.nom} className={`carte offre ${i === 0 ? "meilleure" : ""}`} data-offre={o.nom}>
              {i === 0 && <span className="badge">Le moins cher</span>}
              <h3 style={{ marginTop: 6 }}>{o.nom}</h3>
              <div className="discret">Coût net actualisé sur {s.annees.length} ans</div>
              <div className="gros">{millions(s.cout_net_actualise)}</div>
              <div className="lignes-offre">
                <div><span>Frais payés</span><span className="chiffre">{montant(s.frais_totaux)}</span></div>
                <div><span>Fonds à l'horizon</span><span className="chiffre">{montant(s.fonds_final)}</span></div>
                <div><span>Couverture des départs restants</span><span className="chiffre">{s.couverture_des_departs_restants === null ? "—" : pct(s.couverture_des_departs_restants, 0)}</span></div>
                <div><span>Années sans fonds suffisant</span>
                  {s.annees_decouvert.length ? <span className="etat grave">{s.annees_decouvert.join(", ")}</span> : <span className="etat bien">aucune</span>}</div>
                {!o.interne && <div><span>Taux garanti · frais</span><span className="chiffre">{pct(o.conditions.taux_garanti)} · {pct(o.conditions.frais_sur_cotisations)}</span></div>}
              </div>
              <div className="actions"><button onClick={() => setDetail(detail === o.nom ? null : o.nom)}>{detail === o.nom ? "Replier" : "Selon les scénarios"}</button></div>
              {detail === o.nom && (
                <table><tbody>{o.scenarios.map((x) => (
                  <tr key={x.scenario}><td>{x.scenario} ({pct(x.rendement)})</td><td className="n">{millions(x.cout_net_actualise)}</td></tr>
                ))}</tbody></table>
              )}
            </div>
          );
        })}
      </div>
      <p className="discret section">Le coût net actualisé retranche le fonds restant à l'horizon, qui vous appartient et
        financera les départs suivants : il peut être négatif. Il sert à comparer les offres entre elles.</p>
    </div>
  );
}
