import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { Anomalies, Cle, Echeancier, Erreur, libelleMotif, useCharge } from "../composants/communs";
import { dateFr, millions, montant, pct } from "../format";
import type { Etude } from "../types";
import { useConfirmation } from "../composants/Confirmer";
import { demandeSuppression, raisonDeNePasSupprimer } from "../suppressionEtude";
import { useDossier } from "./Dossier";
import Experience from "../composants/Experience";
import Rapprochement, { sousCotisation } from "../composants/Rapprochement";

const SENSIBILITES: Record<string, string> = {
  taux_actualisation_moins_1pt: "Taux d'actualisation − 1 point",
  taux_actualisation_plus_1pt: "Taux d'actualisation + 1 point",
  croissance_salaires_moins_1pt: "Salaires − 1 point par an",
  croissance_salaires_plus_1pt: "Salaires + 1 point par an",
  rotation_moins_1pt: "Rotation − 1 point",
  rotation_plus_1pt: "Rotation + 1 point",
};

const rang = (k: string) => { const i = Object.keys(SENSIBILITES).indexOf(k); return i < 0 ? 99 : i; };

export default function EtudeDetail() {
  const d = useDossier();
  const { etude: id } = useParams();
  const { donnee: e, erreur, recharger } = useCharge(() => api.get<Etude>(`/organisations/${d.org.id}/etudes/${id}`), [id]);
  const [erreurAction, setErreurAction] = useState<unknown>(null);
  const aller = useNavigate();
  const [demander, fenetre] = useConfirmation();

  if (erreur) return <Erreur erreur={erreur} />;
  if (!e) return <p className="discret">Chargement…</p>;

  async function emettre() {
    setErreurAction(null);
    try { await api.post(`/organisations/${d.org.id}/etudes/${e!.id}/emission`); recharger(); d.recharger(); }
    catch (x) { setErreurAction(x); }
  }

  const retenue = raisonDeNePasSupprimer({ statut: e.statut, raison_de_garder: e.suppression?.raison_de_garder }, d.role);
  return (
    <>
      {fenetre}
      <div className="actions" style={{ justifyContent: "space-between", marginTop: 0 }}>
        <h1 style={{ margin: 0 }}>Évaluation au {dateFr(e.date_evaluation)}</h1>
        {e.statut === "emise" ? <span className="etat bien">Émise · {e.rapport?.numero}</span>
          : <span className="etat attention">Brouillon</span>}
      </div>
      <p className="discret">
        {e.regime ? `${e.regime.nom}, version ${e.regime.numero}` : e.convention.libelle} · {e.totaux.effectif} salariés
      </p>

      <div className="grille g4 section">
        <Cle etiquette="Dette actuarielle" terme="dette" valeur={millions(e.totaux.dette)} sous={montant(e.totaux.dette)} />
        <Cle etiquette="Charge annuelle" terme="charge" valeur={millions(e.totaux.charge)} sous={montant(e.totaux.charge)} />
        <Cle etiquette="Fonds constitué" terme="fonds" valeur={millions(e.fonds_disponible)} sous={montant(e.fonds_disponible)} />
        <Cle etiquette="Cotisation à verser" terme="cotisation" valeur={millions(e.totaux.cotisation_totale ?? 0)} sous={sousCotisation(e)} />
      </div>
      <div className="carte section"><Rapprochement etude={e} /></div>
      {e.experience && <Experience x={e.experience} peutProposer={d.role !== "lecteur_client"} />}
      {e.totaux_convention && (
        <p className="section">Votre régime représente <strong>{montant(e.totaux.dette - e.totaux_convention.dette)}</strong> de
          dette au-delà de la seule convention ({montant(e.totaux_convention.dette)}).</p>
      )}

      <div className="carte section">
        {e.statut === "brouillon" && (
          e.emission.possible
            ? <p><span className="etat bien">Prête</span> L'étude peut être émise.</p>
            : <p><span className="etat grave">Pas encore</span> Avant l'émission : {e.emission.motifs.map(libelleMotif).join(" · ")}.</p>
        )}
        <div className="actions">
          {e.statut === "brouillon" && d.role === "conseiller" && (
            <button className="principal" onClick={emettre} disabled={!e.emission.possible}>Émettre et sceller le rapport</button>
          )}
          {e.statut === "brouillon" && d.role !== "conseiller" && (
            <span className="discret">Votre conseiller relit puis émet le rapport.</span>
          )}
          {e.rapport && (
            <button onClick={() => api.ouvrir(`/organisations/${d.org.id}/etudes/${e.id}/rapport`)}>Ouvrir le rapport PDF</button>
          )}
          <button onClick={() => { setErreurAction(null);
            api.telecharger(`/organisations/${d.org.id}/etudes/${e.id}/export`, `etude-ifc-${e.date_evaluation}.xlsx`)
              .catch(setErreurAction); }}>Exporter en Excel</button>
          {d.role !== "lecteur_client" && (
            <button className="danger" disabled={!!retenue} title={retenue ?? undefined}
                    onClick={() => demander(demandeSuppression(d.org.id, e, () => { d.recharger(); aller(".."); }))}>
              {e.statut === "emise" ? "Supprimer l'étude" : "Supprimer ce brouillon"}</button>
          )}
          <Link to="financement"><button>Financer cet engagement</button></Link>
        </div>
        <Erreur erreur={erreurAction} />
      </div>

      <div className="carte section">
        <h3>Départs prévus</h3>
        <Echeancier annees={e.echeancier} fonds={e.fonds_disponible} />
      </div>
      <div className="grille g2 section">
        <div className="carte">
          <h3>Sensibilités</h3>
          <div className="defile"><table><tbody>
            {Object.entries(e.sensibilites).sort(([a], [b]) => rang(a) - rang(b)).map(([k, v]) => (
              <tr key={k}><td>{SENSIBILITES[k] ?? k}</td><td className="n">{montant(v.dette)}</td>
                <td className="n">{pct((v.dette - e.totaux.dette) / e.totaux.dette)}</td></tr>
            ))}
          </tbody></table></div>
        </div>
        {e.hypotheses.lues && (
          <div className="carte">
            <h3>Hypothèses retenues</h3>
            <div className="defile"><table>
              <thead><tr><th>Hypothèse</th><th className="n">Retenue</th><th className="n">Par défaut</th></tr></thead>
              <tbody>{e.hypotheses.lues.map((h) => (
                <tr key={h.champ} title={`${h.role} ${h.effet}`}>
                  <td>{h.libelle}{h.ecarte && <span className="etat attention" style={{ marginLeft: 6 }}>ajustée</span>}</td>
                  <td className="n">{h.retenu}</td><td className="n discret">{h.defaut}</td></tr>))}</tbody>
            </table></div>
            {e.hypotheses.justification && <p className="discret">Justification : {e.hypotheses.justification}</p>}
            <details className="repli">
              <summary>Ce que fait chaque hypothèse</summary>
              {e.hypotheses.lues.map((h) => (
                <p key={h.champ}><b>{h.libelle}.</b> {h.role} {h.effet}</p>))}
            </details>
          </div>
        )}
      </div>

      {e.par_categorie && (
        <div className="carte section">
          <h3>Par catégorie</h3>
          <div className="defile"><table><thead><tr><th>Catégorie</th><th className="n">Effectif</th><th className="n">Dette</th><th className="n">Charge</th></tr></thead>
            <tbody>{Object.entries(e.par_categorie).map(([k, c]) => (
              <tr key={k}><td>{k === "*" ? "Autres" : k}</td><td className="n">{c.effectif}</td>
                <td className="n">{montant(c.dette)}</td><td className="n">{montant(c.charge)}</td></tr>))}</tbody></table></div>
        </div>
      )}

      <div className="section">
        <h2>Points d'attention</h2>
        <Anomalies anomalies={e.anomalies} />
      </div>
    </>
  );
}
