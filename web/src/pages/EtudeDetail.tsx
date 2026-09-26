import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { Anomalies, Cle, Echeancier, Erreur, libelleMotif, useCharge } from "../composants/communs";
import { dateFr, millions, montant, pct } from "../format";
import type { Etude } from "../types";
import { useDossier } from "./Dossier";
import Experience from "../composants/Experience";
import Rapprochement, { sousCotisation } from "../composants/Rapprochement";

const SENSIBILITES: Record<string, string> = {
  taux_actualisation_moins_1pt: "Taux d'actualisation − 1 point",
  taux_actualisation_plus_1pt: "Taux d'actualisation + 1 point",
  croissance_salaires_plus_1pt: "Salaires + 1 point par an",
};

export default function EtudeDetail() {
  const d = useDossier();
  const { etude: id } = useParams();
  const { donnee: e, erreur, recharger } = useCharge(() => api.get<Etude>(`/organisations/${d.org.id}/etudes/${id}`), [id]);
  const [erreurAction, setErreurAction] = useState<unknown>(null);

  if (erreur) return <Erreur erreur={erreur} />;
  if (!e) return <p className="discret">Chargement…</p>;

  async function emettre() {
    setErreurAction(null);
    try { await api.post(`/organisations/${d.org.id}/etudes/${e!.id}/emission`); recharger(); d.recharger(); }
    catch (x) { setErreurAction(x); }
  }

  return (
    <>
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
          <Link to="financement"><button>Financer cet engagement</button></Link>
        </div>
        <Erreur erreur={erreurAction} />
        {e.statut === "emise" && e.honoraires_ht !== null && d.role !== "lecteur_client" && (
          <p className="discret">Honoraires de l'étude : {montant(e.honoraires_ht)} HT, selon vos conditions.</p>
        )}
      </div>

      <div className="carte section">
        <h3>Départs prévus</h3>
        <Echeancier annees={e.echeancier} fonds={e.fonds_disponible} />
      </div>
      <div className="grille g2 section">
        <div className="carte">
          <h3>Sensibilités</h3>
          <div className="defile"><table><tbody>
            {Object.entries(e.sensibilites).map(([k, v]) => (
              <tr key={k}><td>{SENSIBILITES[k] ?? k}</td><td className="n">{montant(v.dette)}</td>
                <td className="n">{pct((v.dette - e.totaux.dette) / e.totaux.dette)}</td></tr>
            ))}
          </tbody></table></div>
        </div>
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
