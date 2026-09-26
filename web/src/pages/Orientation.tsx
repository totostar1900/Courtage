import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Erreur, useCharge, Volet } from "../composants/communs";
import { dateFr, montant } from "../format";
import type { Orientation, Prestation } from "../types";
import { ExpliquerCalcul } from "../composants/Calcul";
import { useDossier } from "./Dossier";

/** Comparaison : à qui s'adresser, avec quoi, pour combien — et, après, ce que l'assureur a payé. */
export function OrientationAssureur({ p, onFermer, onFait }: { p: Prestation; onFermer: () => void; onFait: () => void }) {
  const d = useDossier();
  const base = `/organisations/${d.org.id}/prestations/${p.id}`;
  const { donnee: o, erreur } = useCharge(() => api.get<Orientation>(`${base}/orientation`), [p.id]);
  const [cochees, setCochees] = useState<string[]>([]);
  const [erreurPaiement, setErreurPaiement] = useState<unknown>(null);
  const ecrit = d.role !== "lecteur_client";

  async function declarer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreurPaiement(null);
    try {
      await api.post(`${base}/paiement`, {
        part_fonds_demandee: f.get("demandee") ? Number(f.get("demandee")) : null,
        part_fonds_payee: Number(f.get("payee")), payee_le: f.get("le") });
      onFait();
    } catch (e) { setErreurPaiement(e); }
  }

  return (
    <Volet titre={`Demander à l'assureur · matricule ${p.matricule}`} onFermer={onFermer} className="section">
      <Erreur erreur={erreur} />
      {o && (
        <>
          <p>{o.message}</p>
          <div className="grille g3">
            <div><div className="discret">Assureur</div><strong>{o.assureur ?? "non enregistré"}</strong>
              {o.numero_police && <div className="discret">police {o.numero_police}</div>}</div>
            <div><div className="discret">Montant à demander</div><strong>{montant(o.montant_a_demander)}</strong>
              <div className="discret">{o.verse !== null && o.verse < o.du ? "le versé, sous le dû" : "le dû selon votre régime"}</div></div>
            <div><div className="discret">Délai de paiement attendu</div><strong>{o.delai_jours} jours</strong>
              <div className="discret">{o.delai_exige ? "exigé au cahier des charges" : "d'usage"}</div></div>
          </div>
          <div className="section"><ExpliquerCalcul calcul={o.calcul} du={o.du} salaire={p.salaire_mensuel_reference} /></div>

          <h3>Les pièces que l'assureur demande d'ordinaire</h3>
          <ul className="liste-pieces">
            {o.pieces.map((x) => (
              <li key={x.nature}>
                <label><input type="checkbox" checked={cochees.includes(x.nature)}
                  onChange={(e) => setCochees(e.target.checked ? [...cochees, x.nature] : cochees.filter((n) => n !== x.nature))} />
                  <span><strong>{x.libelle}</strong><span className="discret"> — {x.detail}</span></span></label>
                {x.nature === "fiche_de_calcul" && ecrit && (
                  <button className="lien" onClick={() => api.ouvrir(`${base}/fiche-de-calcul`)}>Télécharger la fiche scellée</button>
                )}
              </li>
            ))}
          </ul>
          <p className="discret">{cochees.length}/{o.pieces.length} prêtes. Cette liste vous aide, elle ne s'enregistre pas ;
            votre assureur peut demander d'autres pièces.</p>

          {p.part_fonds_payee !== null && (
            <p className="section"><span className="etat bien">Payé</span> {montant(p.part_fonds_payee)} par l'assureur
              {p.payee_le && ` le ${dateFr(p.payee_le)}`}.</p>
          )}
          {ecrit && (
            <form className="formulaire section" onSubmit={declarer}>
              <h3>{p.part_fonds_payee !== null ? "Corriger le paiement déclaré" : "Après la réponse : ce que l'assureur a payé"}</h3>
              <p className="discret">Sans nom : le montant et la date suffisent pour que vos rapports tiennent compte de ce départ.</p>
              <div className="grille g3">
                <label>Demandé au fonds (F)<input name="demandee" type="number" min={0} defaultValue={o.montant_a_demander} /></label>
                <label>Payé par l'assureur (F)<input name="payee" type="number" min={1} required
                       defaultValue={p.part_fonds_payee ?? undefined} /></label>
                <label>Payé le<input name="le" type="date" required defaultValue={p.payee_le ?? undefined} /></label>
              </div>
              <div className="actions"><button className="principal">
                {p.part_fonds_payee !== null ? "Corriger le paiement" : "Déclarer le paiement"}</button></div>
              <Erreur erreur={erreurPaiement} />
            </form>
          )}
        </>
      )}
    </Volet>
  );
}
