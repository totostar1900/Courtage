import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { dateFr, montant, pct } from "../format";
import type { Conditions } from "../types";
import { useDossier } from "./Dossier";

const MODES = { honoraires: "Honoraires", commission: "Commission de l'assureur", mixte: "Honoraires et commission" };

/** La transparence de Clark : ce que gagne le courtier, écrit en clair pour le client. */
export default function Remuneration() {
  const d = useDossier();
  const { donnee, recharger } = useCharge(
    () => api.get<{ en_vigueur: Conditions | null; historique: Conditions[] }>(`/organisations/${d.org.id}/remuneration`), []);
  const [erreur, setErreur] = useState<unknown>(null);
  const c = donnee?.en_vigueur;

  async function fixer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await api.post(`/organisations/${d.org.id}/remuneration`, {
        en_vigueur_du: f.get("en_vigueur_du"), mode: f.get("mode"),
        honoraires_etude_ifc: Number(f.get("honoraires_etude_ifc") || 0),
        honoraires_par_salarie: Number(f.get("honoraires_par_salarie") || 0),
        commission_bps: Math.round(Number(f.get("commission") || 0) * 100),
      });
      recharger();
    } catch (e) { setErreur(e); }
  }

  return (
    <>
      <h1>Comment nous sommes rémunérés</h1>
      <p>Nous vous le disons avant que vous ne signiez : ce que vous payez, ce que l'assureur nous verse.</p>
      {c ? (
        <div className="carte">
          <h2>{MODES[c.mode]}</h2>
          <div className="lignes-offre">
            {c.honoraires_etude_ifc > 0 && <div><span>Par étude actuarielle</span><strong>{montant(c.honoraires_etude_ifc)} HT</strong></div>}
            {c.honoraires_par_salarie > 0 && <div><span>Par salarié évalué</span><strong>{montant(c.honoraires_par_salarie)} HT</strong></div>}
            {c.commission_bps > 0 && <div><span>Commission versée par l'assureur retenu</span><strong>{pct(c.commission_bps / 10000)} des primes</strong></div>}
            <div><span>Depuis le</span><span>{dateFr(c.en_vigueur_du)}</span></div>
          </div>
        </div>
      ) : <p className="discret">Conditions à fixer avec votre conseiller.</p>}

      {d.role === "conseiller" && (
        <form className="carte formulaire section" onSubmit={fixer}>
          <h2>Nouvelles conditions</h2>
          <div className="grille g3">
            <label>À partir du<input name="en_vigueur_du" type="date" required /></label>
            <label>Mode<select name="mode">{Object.entries(MODES).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
            <label>Commission (% des primes)<input name="commission" type="number" step={0.1} defaultValue={0} /></label>
            <label>Honoraires par étude (F HT)<input name="honoraires_etude_ifc" type="number" min={0} defaultValue={0} /></label>
            <label>Honoraires par salarié (F HT)<input name="honoraires_par_salarie" type="number" min={0} defaultValue={0} /></label>
          </div>
          <div className="actions"><button className="principal">Enregistrer</button></div>
          <Erreur erreur={erreur} />
        </form>
      )}
    </>
  );
}
