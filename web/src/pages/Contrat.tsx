import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { Constats, Erreur, useCharge, Volet } from "../composants/communs";
import { dateFr } from "../format";
import { t } from "../i18n";
import type { ContratsDossier } from "../types";
import { MenuActions } from "../composants/MenuActions";
import { useConfirmation } from "../composants/Confirmer";
import { useDossier } from "./Dossier";

// Lu au rendu (la langue peut changer) : une fonction, pas une constante figée à l'import.
const departs = () => [
  t("Vous nous déclarez le départ ; nous montons le dossier de prise en charge et le transmettons à l'assureur.",
    "You report the departure to us; we prepare the claim file and send it to the insurer."),
  t("Nous suivons le paiement et vous alertons si l'assureur dépasse le délai prévu.",
    "We follow the payment and alert you if the insurer goes past the agreed deadline."),
  t("Pour ce dossier seulement, nous recueillons l'identité du bénéficiaire ; elle n'entre dans aucun rapport.",
    "For this claim file only, we collect the beneficiary's identity; it never appears in any report."),
];
// Un contrat enregistré avant le courtage seul peut dire « comparaison » : il reste lisible.
const libelleService = (s: string) => (s === "courtage" ? t("Courtage", "Brokerage") : t("Comparaison (ancien service)", "Comparison (former service)"));

/** Le service que nous vous rendons, et ce qu'il change le jour où un salarié part. */
export default function Contrat() {
  const d = useDossier();
  const { donnee, erreur, recharger } = useCharge(() => api.get<ContratsDossier>(`/organisations/${d.org.id}/contrats`), []);
  const [params] = useSearchParams();
  const retenu = params.get("assureur");
  const [ouvert, setOuvert] = useState(Boolean(retenu));
  const [demander, fenetre] = useConfirmation();
  if (erreur) return <Erreur erreur={erreur} />;
  if (!donnee) return <p className="discret">{t("Chargement…", "Loading…")}</p>;
  const c = donnee.en_vigueur;
  const sousMandat = donnee.service === "courtage";

  return (
    <>
      {fenetre}
      <h1>{t("Votre contrat", "Your contract")}</h1>
      <p>{t("Nous sommes votre courtier : mandatés par vous, entre vous et l'assureur. Le contrat de courtage naît de la signature du mandat.",
        "We are your broker: appointed by you, between you and the insurer. The brokerage contract starts when the mandate is signed.")}</p>

      <div className="carte section" data-service={donnee.service}>
        <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
          <h2 style={{ margin: 0 }}>{sousMandat ? t("Courtage", "Brokerage") : t("Sans mandat", "No mandate")}</h2>
          <span className={`etat ${sousMandat ? "bien" : "neutre"}`}>
            {c && sousMandat ? t(`depuis le ${dateFr(c.en_vigueur_du)}`, `since ${dateFr(c.en_vigueur_du)}`) : t("aucun mandat en vigueur", "no mandate in force")}</span>
        </div>
        {sousMandat && c ? (
          <>
            <div className="lignes-offre">
              <div><span>{t("Assureur", "Insurer")}</span><strong>{c.assureur ?? t("à placer", "to be placed")}</strong></div>
              {c.numero_police && <div><span>{t("Police", "Policy")}</span><span>{c.numero_police}{c.date_effet_police && t(` · effet le ${dateFr(c.date_effet_police)}`, ` · effective ${dateFr(c.date_effet_police)}`)}</span></div>}
              {c.mandat_reference && <div><span>{t("Mandat", "Mandate")}</span><span>{c.mandat_reference}</span></div>}
              {c.note && <div><span>{t("Note", "Note")}</span><span>{c.note}</span></div>}
            </div>
            <h3 className="section">{t("Quand un salarié part", "When an employee leaves")}</h3>
            <ul>{departs().map((x) => <li key={x}>{x}</li>)}</ul>
          </>
        ) : (
          <p style={{ marginTop: 8 }}>{t("Signez un mandat de courtage : nous consultons les assureurs, plaçons votre engagement et portons ensuite vos départs en retraite. Sans frais pour vous.",
            "Sign a brokerage mandate: we consult insurers, place your liability and then handle your retirements. At no cost to you.")}</p>
        )}
        <div className="actions">
          <Link to="/guide/contrat">{t("Le courtage : le guide", "Brokerage: the guide")}</Link>
          {!sousMandat && <Link to="../accompagnement">{t("Demander un accompagnement en courtage →", "Request brokerage support →")}</Link>}
        </div>
      </div>

      {donnee.constats.length > 0 && <div className="section"><Constats constats={donnee.constats} /></div>}

      {donnee.historique.length > 0 && (
        <div className="section">
          <h2>{t("Historique", "History")}</h2>
          <div className="defile"><table>
            <thead><tr><th>{t("Depuis le", "Since")}</th><th>{t("Service", "Service")}</th><th>{t("Assureur", "Insurer")}</th><th>{t("Police", "Policy")}</th><th aria-label={t("Actions", "Actions")} /></tr></thead>
            <tbody>{donnee.historique.map((h) => (
              <tr key={h.id}><td>{dateFr(h.en_vigueur_du)}</td><td>{libelleService(h.service)}</td>
                <td>{h.assureur ?? "—"}</td><td>{h.numero_police ?? "—"}</td>
                <td className="n">{d.role === "conseiller" && (
                  <MenuActions libelle={t(`Actions sur le contrat du ${dateFr(h.en_vigueur_du)}`, `Actions on the contract of ${dateFr(h.en_vigueur_du)}`)} actions={[
                    { libelle: t("Supprimer (saisi par erreur)", "Delete (entered by mistake)"), danger: true, raison: h.raison_de_garder ?? null,
                      agir: () => demander({
                        titre: t("Supprimer ce contrat", "Delete this contract"), message: <p>{t("Saisi par erreur ? Le journal garde la trace de la suppression.", "Entered by mistake? The log keeps a record of the deletion.")}</p>,
                        mot: t("SUPPRIMER", "DELETE"),
                        action: async () => { await api.del(`/organisations/${d.org.id}/contrats/${h.id}`); recharger(); },
                      }) },
                  ]} />)}</td></tr>
            ))}</tbody>
          </table></div>
        </div>
      )}

      {d.role === "conseiller" && (
        <div className="section">
          {ouvert
            ? <NouveauContrat assureur={retenu} onFermer={() => setOuvert(false)} onFait={() => { setOuvert(false); recharger(); }} />
            : <button className="principal" onClick={() => setOuvert(true)}>{t("Enregistrer un contrat", "Record a contract")}</button>}
        </div>
      )}
    </>
  );
}

function NouveauContrat({ assureur, onFermer, onFait }: { assureur?: string | null; onFermer: () => void; onFait: () => void }) {
  const d = useDossier();
  const [erreur, setErreur] = useState<unknown>(null);
  async function enregistrer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const texte = (k: string) => (String(f.get(k) ?? "").trim() || null);
    setErreur(null);
    try {
      await api.post(`/organisations/${d.org.id}/contrats`, {
        en_vigueur_du: f.get("en_vigueur_du"), service: "courtage", assureur: texte("assureur"), numero_police: texte("numero_police"),
        date_effet_police: texte("date_effet_police"), mandat_reference: texte("mandat_reference"),
        note: texte("note") });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre={t("Enregistrer un contrat", "Record a contract")} onFermer={onFermer}>
      <form className="formulaire" onSubmit={enregistrer}>
        <p className="discret">{t("Un contrat ne se modifie pas : un nouveau prend effet à sa date, l'ancien reste dans l'historique. Saisi par erreur, il se supprime depuis son menu ⋮, tant qu'aucun dossier ni aucun départ ne s'appuie dessus.",
          "A contract is never edited: a new one takes effect on its date and the old one stays in the history. If entered by mistake, it can be deleted from its ⋮ menu, as long as no claim file or departure relies on it.")}</p>
        <div className="grille g3">
          <label>{t("À partir du", "Effective from")}<input name="en_vigueur_du" type="date" required /></label>
          <label>{t("Assureur", "Insurer")}<input name="assureur" defaultValue={assureur ?? ""} /></label>
          <label>{t("Numéro de police", "Policy number")}<input name="numero_police" /></label>
          <label>{t("Effet de la police", "Policy effective date")}<input name="date_effet_police" type="date" /></label>
          <label>{t("Référence du mandat", "Mandate reference")}<input name="mandat_reference" required placeholder={t("MC-XXXX-XXXX ou mandat papier du 15/12/2025", "MC-XXXX-XXXX or paper mandate of 15/12/2025")} /></label>
        </div>
        <label>{t("Note", "Note")}<input name="note" /></label>
        <div className="actions"><button className="principal">{t("Enregistrer", "Save")}</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
