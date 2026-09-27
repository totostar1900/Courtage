import { useState, type FormEvent } from "react";

import { Link } from "react-router-dom";

import { api } from "../api";
import { Erreur } from "../composants/communs";
import { dateFr, millions } from "../format";
import { t } from "../i18n";
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
      <h1>{t("Mettre les assureurs en concurrence", "Put insurers in competition")}</h1>
      <p>{t("Un cahier des charges identique pour tous : votre régime, votre engagement scellé, votre personnel en agrégats "
        + "(rien d'individuel), les conditions que vous demandez, et une grille de réponse commune. Changer d'assureur "
        + "commence ici : le préavis et la pénalité de transfert se négocient maintenant.",
        "The same tender specifications for all: your plan, your sealed liability, your staff in aggregate (nothing "
        + "individual), the terms you require, and a common response grid. Changing insurer starts here: the transfer "
        + "notice and penalty are negotiated now.")}</p>

      {d.role === "conseiller" && emises.length > 0 && (
        <form className="carte formulaire" onSubmit={emettre}>
          <div className="grille g2">
            <label>{t("Étude de référence", "Reference study")}
              <select name="etude_id">{emises.map((e) => <option key={e.id} value={e.id}>{dateFr(e.date_evaluation)} · {millions(e.dette)}</option>)}</select>
            </label>
            <label>{t("Réponse attendue avant le", "Response due by")}<input name="date_limite_reponse" type="date" defaultValue={dansUnMois} required /></label>
          </div>
          <div className="grille g4">
            <label>{t("Taux garanti minimum (%)", "Minimum guaranteed rate (%)")}<input name="taux_garanti_minimum" type="number" step={0.1} defaultValue={2.5} /></label>
            <label>{t("Participation minimum (%)", "Minimum profit sharing (%)")}<input name="participation_benefices_minimum" type="number" step={1} defaultValue={85} /></label>
            <label>{t("Frais sur cotisations max (%)", "Max. charges on contributions (%)")}<input name="frais_sur_cotisations_maximum" type="number" step={0.1} defaultValue={3} /></label>
            <label>{t("Frais sur encours max (%/an)", "Max. charges on assets (%/year)")}<input name="frais_sur_encours_maximum" type="number" step={0.1} defaultValue={0.5} /></label>
            <label>{t("Préavis de transfert max (mois)", "Max. transfer notice (months)")}<input name="transfert_preavis_mois_maximum" type="number" defaultValue={3} /></label>
            <label>{t("Pénalité de transfert max (%)", "Max. transfer penalty (%)")}<input name="transfert_penalite_maximum" type="number" step={0.1} defaultValue={0} /></label>
            <label>{t("Délai de paiement max (jours)", "Max. payment period (days)")}<input name="delai_paiement_jours_maximum" type="number" defaultValue={30} /></label>
          </div>
          <label>{t("Note aux assureurs", "Note to insurers")}<textarea name="note" rows={2} /></label>
          <div className="actions"><button className="principal">{t("Émettre et sceller le cahier des charges", "Issue and seal the tender specifications")}</button></div>
          <Erreur erreur={erreur} />
        </form>
      )}
      {emises.length === 0 && <p>{t("Le cahier des charges part d'une étude émise.", "The tender specifications are based on an issued study.")}</p>}
      {d.role !== "conseiller" && emises.length > 0 && d.fiches.length === 0 && (
        <p className="discret">{t("Votre conseiller prépare et émet le cahier des charges.", "Your adviser prepares and issues the tender specifications.")}</p>
      )}

      <div className="section">
        <h2>{t("Cahiers des charges émis", "Issued tender specifications")}</h2>
        <table>
          <thead><tr><th>{t("Numéro", "Number")}</th><th>{t("Émis le", "Issued on")}</th><th>{t("Réponses avant le", "Responses due by")}</th><th /></tr></thead>
          <tbody>{d.fiches.map((f) => (
            <tr key={f.id}><td>{f.numero}</td><td>{dateFr(f.emise_le)}</td><td>{dateFr(f.date_limite_reponse)}</td>
              <td className="n"><div className="actions" style={{ justifyContent: "flex-end", marginTop: 0 }}>
                <Link to={f.id}><button className="principal">{t("Réponses des assureurs", "Insurers' responses")}</button></Link>
                <button onClick={() => api.ouvrir(`/organisations/${d.org.id}/fiches/${f.id}/document`)}>PDF</button></div></td></tr>
          ))}</tbody>
        </table>
      </div>
    </>
  );
}
