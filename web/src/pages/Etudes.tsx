import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { Erreur } from "../composants/communs";
import { CONVENTION_PAR_PAYS } from "../composants/EditeurCategories";
import { dateFr, montant } from "../format";
import type { Etude } from "../types";
import { useDossier } from "./Dossier";

export default function Etudes() {
  const d = useDossier();
  const naviguer = useNavigate();
  const [erreur, setErreur] = useState<unknown>(null);
  // Une hypothèse proposée par l'expérience réelle arrive ici, à confirmer : jamais appliquée sans décision.
  const [params] = useSearchParams();
  const proposee = params.get("turnover");
  const versions = d.regimes.flatMap((r) => r.versions.map((v) => ({ ...v, nomRegime: r.nom })));

  async function lancer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const version = f.get("regime_version_id") as string;
    setErreur(null);
    try {
      const e = await api.post<Etude>(`/organisations/${d.org.id}/etudes`, {
        fichier_id: f.get("fichier_id"), date_evaluation: f.get("date_evaluation"),
        fonds_disponible: Number(f.get("fonds_disponible") || 0),
        ...(f.get("taux_turnover") ? { hypotheses: { taux_turnover: Number(f.get("taux_turnover")) / 100 },
                                       justification: f.get("justification") } : {}),
        ...(version ? { regime_version_id: version } : { convention_code: f.get("convention_code") }),
      });
      d.recharger();
      naviguer(e.id);
    } catch (e) { setErreur(e); }
  }

  return (
    <>
      <h1>Évaluer votre engagement</h1>
      <p>La dette actuarielle, la charge de l'année, la cotisation à verser. Votre conseiller relit et émet le rapport,
        scellé et vérifiable.</p>
      {d.role !== "lecteur_client" && d.fichiers.length > 0 && (
        <form className="carte formulaire" onSubmit={lancer}>
          <div className="grille g4">
            <label>Personnel
              <select name="fichier_id">{d.fichiers.map((f) => <option key={f.id} value={f.id}>{f.nom_fichier}</option>)}</select>
            </label>
            <label>Date d'évaluation (une clôture)
              <input name="date_evaluation" type="date" required defaultValue={d.fichiers[0]?.date_donnees} />
            </label>
            <label>Base
              <select name="regime_version_id" defaultValue={versions.find((v) => v.statut === "adoptee")?.id ?? ""}>
                <option value="">la convention seule</option>
                {versions.map((v) => <option key={v.id} value={v.id}>{v.nomRegime}, version {v.numero}</option>)}
              </select>
            </label>
            <label>Convention (sans régime)<input name="convention_code" defaultValue={CONVENTION_PAR_PAYS[d.org.pays]} /></label>
          </div>
          <label style={{ maxWidth: 260 }}>Fonds déjà constitué (F)<input name="fonds_disponible" type="number" min={0} defaultValue={0} /></label>
          {proposee && (
            <div className="constat informe section">
              <div className="titre">Rotation proposée par l'expérience réelle</div>
              <div className="grille g3">
                <label>Rotation retenue (% par an)<input name="taux_turnover" type="number" step={0.1} min={0} max={50}
                       defaultValue={Math.round(Number(proposee) * 1000) / 10} /></label>
                <label style={{ gridColumn: "span 2" }}>Justification (figurera au rapport)
                  <input name="justification" required defaultValue={params.get("justification") ?? ""} /></label>
              </div>
            </div>
          )}
          <div className="actions"><button className="principal">Calculer</button></div>
          <Erreur erreur={erreur} />
        </form>
      )}
      {d.fichiers.length === 0 && <p>Déposez d'abord le fichier de votre personnel.</p>}

      <div className="section">
        <h2>Vos études</h2>
        <div className="defile">
          <table>
            <thead><tr><th>Évaluation au</th><th>Base</th><th className="n">Dette</th><th>État</th></tr></thead>
            <tbody>
              {d.etudes.map((e) => (
                <tr key={e.id} className="cliquable" onClick={() => naviguer(e.id)}>
                  <td>{dateFr(e.date_evaluation)}</td>
                  <td>{e.convention_code}</td>
                  <td className="n">{montant(e.dette)}</td>
                  <td>{e.statut === "emise" ? <span className="etat bien">Émise le {dateFr(e.emise_le)}</span>
                    : <span className="etat attention">Brouillon</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
