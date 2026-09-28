import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Erreur, Volet } from "../composants/communs";
import { dateFr, montant } from "../format";
import { t } from "../i18n";
import type { Prestation } from "../types";
import { ExpliquerCalcul } from "../composants/Calcul";
import { useDossier } from "./Dossier";

/** Un départ sans mandat au jour du départ : l'entreprise a traité avec son assureur. La plateforme en garde le
 *  calcul (fiche scellée) et ce que l'assureur a payé, déclaré sans nom, pour l'expérience réelle. */
export function DepartHorsMandat({ p, onFermer, onFait }: { p: Prestation; onFermer: () => void; onFait: () => void }) {
  const d = useDossier();
  const base = `/organisations/${d.org.id}/prestations/${p.id}`;
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
    <Volet titre={t(`Départ hors mandat · matricule ${p.matricule}`, `Departure outside a mandate · staff number ${p.matricule}`)} onFermer={onFermer} className="section">
      <p>{t("Au jour de ce départ, aucun mandat de courtage n'était en vigueur : l'entreprise a traité avec son assureur.",
        "On the day of this departure, no brokerage mandate was in force: the company dealt with its insurer.")}</p>
      <div className="section"><ExpliquerCalcul calcul={p.calcul} du={p.du} salaire={p.salaire_mensuel_reference} /></div>
      {ecrit && (
        <p><button className="lien" onClick={() => api.ouvrir(`${base}/fiche-de-calcul`)}>
          {t("Télécharger la fiche de calcul scellée", "Download the sealed calculation sheet")}</button></p>
      )}
      <>
          {p.part_fonds_payee !== null && (
            <p className="section"><span className="etat bien">{t("Payé", "Paid")}</span> {t(`${montant(p.part_fonds_payee)} par l'assureur`, `${montant(p.part_fonds_payee)} by the insurer`)}
              {p.payee_le && t(` le ${dateFr(p.payee_le)}`, ` on ${dateFr(p.payee_le)}`)}.</p>
          )}
          {ecrit && (
            <form className="formulaire section" onSubmit={declarer}>
              <h3>{p.part_fonds_payee !== null ? t("Corriger le paiement déclaré", "Correct the reported payment") : t("Après la réponse : ce que l'assureur a payé", "After the response: what the insurer paid")}</h3>
              <p className="discret">{t("Sans nom : le montant et la date suffisent pour que vos rapports tiennent compte de ce départ.", "No names: the amount and the date are enough for your reports to take this departure into account.")}</p>
              <div className="grille g3">
                <label>{t("Demandé au fonds (F)", "Requested from the fund (F)")}<input name="demandee" type="number" min={0} defaultValue={p.verse !== null && p.verse < p.du ? p.verse : p.du} /></label>
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
    </Volet>
  );
}
