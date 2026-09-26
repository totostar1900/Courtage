import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Erreur } from "../composants/communs";
import { dateFr, millions } from "../format";
import { useDossier } from "./Dossier";

export default function Cahier() {
  const d = useDossier();
  const emises = d.etudes.filter((e) => e.statut === "emise");
  const [erreur, setErreur] = useState<unknown>(null);
  const dansUnMois = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);

  async function emettre(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const taux = (k: string) => (f.get(k) ? Number(f.get(k)) / 100 : null);
    setErreur(null);
    try {
      await api.post(`/organisations/${d.org.id}/fiches`, {
        etude_id: f.get("etude_id"), date_limite_reponse: f.get("date_limite_reponse"),
        conditions: {
          taux_garanti_minimum: taux("taux_garanti_minimum"), participation_benefices_minimum: taux("participation_benefices_minimum"),
          frais_sur_cotisations_maximum: taux("frais_sur_cotisations_maximum"), frais_sur_encours_maximum: taux("frais_sur_encours_maximum"),
          transfert_preavis_mois_maximum: f.get("transfert_preavis_mois_maximum") ? Number(f.get("transfert_preavis_mois_maximum")) : null,
          transfert_penalite_maximum: taux("transfert_penalite_maximum"),
          delai_paiement_jours_maximum: f.get("delai_paiement_jours_maximum") ? Number(f.get("delai_paiement_jours_maximum")) : null,
          note: f.get("note") || null,
        },
      });
      d.recharger();
    } catch (e) { setErreur(e); }
  }

  return (
    <>
      <h1>Mettre les assureurs en concurrence</h1>
      <p>Un cahier des charges identique pour tous : votre régime, votre engagement scellé, votre personnel en agrégats
        (rien d'individuel), les conditions que vous demandez, et une grille de réponse commune. Changer d'assureur
        commence ici : le préavis et la pénalité de transfert se négocient maintenant.</p>

      {d.role === "conseiller" && emises.length > 0 && (
        <form className="carte formulaire" onSubmit={emettre}>
          <div className="grille g2">
            <label>Étude de référence
              <select name="etude_id">{emises.map((e) => <option key={e.id} value={e.id}>{dateFr(e.date_evaluation)} · {millions(e.dette)}</option>)}</select>
            </label>
            <label>Réponse attendue avant le<input name="date_limite_reponse" type="date" defaultValue={dansUnMois} required /></label>
          </div>
          <div className="grille g4">
            <label>Taux garanti minimum (%)<input name="taux_garanti_minimum" type="number" step={0.1} defaultValue={2.5} /></label>
            <label>Participation minimum (%)<input name="participation_benefices_minimum" type="number" step={1} defaultValue={85} /></label>
            <label>Frais sur cotisations max (%)<input name="frais_sur_cotisations_maximum" type="number" step={0.1} defaultValue={3} /></label>
            <label>Frais sur encours max (%/an)<input name="frais_sur_encours_maximum" type="number" step={0.1} defaultValue={0.5} /></label>
            <label>Préavis de transfert max (mois)<input name="transfert_preavis_mois_maximum" type="number" defaultValue={3} /></label>
            <label>Pénalité de transfert max (%)<input name="transfert_penalite_maximum" type="number" step={0.1} defaultValue={0} /></label>
            <label>Délai de paiement max (jours)<input name="delai_paiement_jours_maximum" type="number" defaultValue={30} /></label>
          </div>
          <label>Note aux assureurs<textarea name="note" rows={2} /></label>
          <div className="actions"><button className="principal">Émettre et sceller le cahier des charges</button></div>
          <Erreur erreur={erreur} />
        </form>
      )}
      {emises.length === 0 && <p>Le cahier des charges part d'une étude émise.</p>}
      {d.role !== "conseiller" && emises.length > 0 && d.fiches.length === 0 && (
        <p className="discret">Votre conseiller prépare et émet le cahier des charges.</p>
      )}

      <div className="section">
        <h2>Cahiers des charges émis</h2>
        <table>
          <thead><tr><th>Numéro</th><th>Émis le</th><th>Réponses avant le</th><th /></tr></thead>
          <tbody>{d.fiches.map((f) => (
            <tr key={f.id}><td>{f.numero}</td><td>{dateFr(f.emise_le)}</td><td>{dateFr(f.date_limite_reponse)}</td>
              <td className="n"><button onClick={() => api.ouvrir(`/organisations/${d.org.id}/fiches/${f.id}/document`)}>PDF</button></td></tr>
          ))}</tbody>
        </table>
      </div>
    </>
  );
}
