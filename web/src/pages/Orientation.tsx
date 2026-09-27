import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Erreur, useCharge, Volet } from "../composants/communs";
import { dateFr, montant } from "../format";
import { t } from "../i18n";
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
    <Volet titre={t(`Demander à l'assureur · matricule ${p.matricule}`, `Request from the insurer · staff number ${p.matricule}`)} onFermer={onFermer} className="section">
      <Erreur erreur={erreur} />
      {o && (
        <>
          <p>{o.message}</p>
          <div className="grille g3">
            <div><div className="discret">{t("Assureur", "Insurer")}</div><strong>{o.assureur ?? t("non enregistré", "not recorded")}</strong>
              {o.numero_police && <div className="discret">{t(`police ${o.numero_police}`, `policy ${o.numero_police}`)}</div>}</div>
            <div><div className="discret">{t("Montant à demander", "Amount to request")}</div><strong>{montant(o.montant_a_demander)}</strong>
              <div className="discret">{o.verse !== null && o.verse < o.du ? t("le versé, sous le dû", "the amount paid, below the amount due") : t("le dû selon votre régime", "the amount due under your scheme")}</div></div>
            <div><div className="discret">{t("Délai de paiement attendu", "Expected payment time")}</div><strong>{t(`${o.delai_jours} jours`, `${o.delai_jours} days`)}</strong>
              <div className="discret">{o.delai_exige ? t("exigé au cahier des charges", "required in the specifications") : t("d'usage", "customary")}</div></div>
          </div>
          <div className="section"><ExpliquerCalcul calcul={o.calcul} du={o.du} salaire={p.salaire_mensuel_reference} /></div>

          <h3>{t("Les pièces que l'assureur demande d'ordinaire", "The documents the insurer usually asks for")}</h3>
          <ul className="liste-pieces">
            {o.pieces.map((x) => (
              <li key={x.nature}>
                <label><input type="checkbox" checked={cochees.includes(x.nature)}
                  onChange={(e) => setCochees(e.target.checked ? [...cochees, x.nature] : cochees.filter((n) => n !== x.nature))} />
                  <span><strong>{x.libelle}</strong><span className="discret"> — {x.detail}</span></span></label>
                {x.nature === "fiche_de_calcul" && ecrit && (
                  <button className="lien" onClick={() => api.ouvrir(`${base}/fiche-de-calcul`)}>{t("Télécharger la fiche scellée", "Download the sealed calculation sheet")}</button>
                )}
              </li>
            ))}
          </ul>
          <p className="discret">{t(`${cochees.length}/${o.pieces.length} prêtes. Cette liste vous aide, elle ne s'enregistre pas ; votre assureur peut demander d'autres pièces.`,
            `${cochees.length}/${o.pieces.length} ready. This list is there to help you and is not saved; your insurer may ask for other documents.`)}</p>

          {p.part_fonds_payee !== null && (
            <p className="section"><span className="etat bien">{t("Payé", "Paid")}</span> {t(`${montant(p.part_fonds_payee)} par l'assureur`, `${montant(p.part_fonds_payee)} by the insurer`)}
              {p.payee_le && t(` le ${dateFr(p.payee_le)}`, ` on ${dateFr(p.payee_le)}`)}.</p>
          )}
          {ecrit && (
            <form className="formulaire section" onSubmit={declarer}>
              <h3>{p.part_fonds_payee !== null ? t("Corriger le paiement déclaré", "Correct the reported payment") : t("Après la réponse : ce que l'assureur a payé", "After the response: what the insurer paid")}</h3>
              <p className="discret">{t("Sans nom : le montant et la date suffisent pour que vos rapports tiennent compte de ce départ.", "No names: the amount and the date are enough for your reports to take this departure into account.")}</p>
              <div className="grille g3">
                <label>{t("Demandé au fonds (F)", "Requested from the fund (F)")}<input name="demandee" type="number" min={0} defaultValue={o.montant_a_demander} /></label>
                <label>{t("Payé par l'assureur (F)", "Paid by the insurer (F)")}<input name="payee" type="number" min={1} required
                       defaultValue={p.part_fonds_payee ?? undefined} /></label>
                <label>{t("Payé le", "Paid on")}<input name="le" type="date" required defaultValue={p.payee_le ?? undefined} /></label>
              </div>
              <div className="actions"><button className="principal">
                {p.part_fonds_payee !== null ? t("Corriger le paiement", "Correct the payment") : t("Déclarer le paiement", "Report the payment")}</button></div>
              <Erreur erreur={erreurPaiement} />
            </form>
          )}
        </>
      )}
    </Volet>
  );
}
