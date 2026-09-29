import { useState, type FormEvent } from "react";

import { api } from "../api";
import { dateFr } from "../format";
import { t } from "../i18n";
import { Erreur, useCharge } from "./communs";

interface Consultation {
  id: string; assureur: string; contact_nom: string | null; contact_courriel: string; envoyee_le: string;
  envoyee_par: string; ouverte_le: string | null; repondue_le: string | null; relances: number;
  relancee_le: string | null; annulee_le: string | null; expire_le: string;
  etat: "envoyee" | "ouverte" | "repondue" | "close" | "annulee";
}

const etats = (): Record<Consultation["etat"], [string, string]> => ({
  envoyee: [t("Envoyée", "Sent"), "neutre"], ouverte: [t("Ouverte", "Opened"), "attention"],
  repondue: [t("Répondue", "Answered"), "bien"], close: [t("Close sans réponse", "Closed, no response"), "grave"],
  annulee: [t("Annulée", "Cancelled"), "neutre"] });

/** Qui a été consulté, quand, et où en est chacun : la preuve d'une mise en concurrence loyale. Le conseiller consulte
 *  depuis ici ; l'assureur reçoit un lien personnel par courriel et dépose son offre sans compte. */
export default function Consultations({ base, orgId, conseiller, ouverte }: { base: string; orgId: string;
  conseiller: boolean; ouverte: boolean }) {
  const { donnee, erreur, recharger } = useCharge(() => api.get<Consultation[]>(`${base}/consultations`), [base]);
  const [ajout, setAjout] = useState(false);
  const [erreurAction, setErreurAction] = useState<unknown>(null);
  async function agir(chemin: string) {
    setErreurAction(null);
    try { await api.post(`/organisations/${orgId}/consultations/${chemin}`, {}); recharger(); } catch (e) { setErreurAction(e); }
  }
  async function consulter(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreurAction(null);
    try {
      await api.post(`${base}/consultations`, { assureur: String(f.get("assureur") ?? "").trim(),
        contact_nom: String(f.get("contact_nom") ?? "").trim() || null, contact_courriel: String(f.get("contact_courriel") ?? "").trim() });
      setAjout(false); recharger();
    } catch (e) { setErreurAction(e); }
  }
  return (
    <section className="carte section" aria-labelledby="consultations">
      <div className="actions" style={{ justifyContent: "space-between", marginTop: 0 }}>
        <h2 id="consultations" style={{ margin: 0 }}>{t("Assureurs consultés", "Insurers consulted")}</h2>
        {conseiller && ouverte && !ajout && <button type="button" onClick={() => setAjout(true)}>{t("Consulter un assureur", "Consult an insurer")}</button>}
      </div>
      <p className="discret">{t("Chaque assureur reçoit par courriel un lien personnel, valable jusqu'à la date limite : il lit le cahier et dépose son offre sans compte. Son offre rejoint les réponses ci-dessous, classée avec les autres.",
        "Each insurer receives a personal link by email, valid until the deadline: it reads the specifications and uploads its offer without an account. Its offer joins the responses below, ranked with the others.")}</p>
      {ajout && (
        <form className="formulaire" onSubmit={consulter} aria-label={t("Consulter un assureur", "Consult an insurer")}>
          <div className="grille-2">
            <label>{t("Assureur", "Insurer")}<input name="assureur" required minLength={2} /></label>
            <label>{t("Contact (nom)", "Contact (name)")}<input name="contact_nom" /></label>
            <label>{t("Adresse électronique du contact", "Contact's email address")}<input name="contact_courriel" type="email" required /></label>
          </div>
          <div className="actions"><button className="principal">{t("Envoyer le cahier", "Send the specifications")}</button>
            <button type="button" onClick={() => setAjout(false)}>{t("Annuler", "Cancel")}</button></div>
        </form>
      )}
      <Erreur erreur={erreur ?? erreurAction} />
      {donnee && donnee.length === 0 && <p className="discret">{t("Aucun assureur consulté depuis la plateforme.", "No insurer consulted from the platform.")}</p>}
      {donnee && donnee.length > 0 && (
        <div className="defile"><table>
          <thead><tr><th>{t("Assureur", "Insurer")}</th><th>{t("Envoyé le", "Sent on")}</th><th>{t("Ouvert le", "Opened on")}</th>
            <th>{t("Répondu le", "Answered on")}</th><th>{t("État", "Status")}</th><th aria-label={t("Actions", "Actions")} /></tr></thead>
          <tbody>{donnee.map((c) => {
            const [libelle, style] = etats()[c.etat];
            const attend = c.etat === "envoyee" || c.etat === "ouverte";
            return (
              <tr key={c.id}>
                <td>{c.assureur}<div className="discret">{[c.contact_nom, c.contact_courriel].filter(Boolean).join(" · ")}</div></td>
                <td>{dateFr(c.envoyee_le)}{c.relances > 0 && <div className="discret">{t(`${c.relances} relance(s), la dernière le ${dateFr(c.relancee_le)}`, `${c.relances} reminder(s), last on ${dateFr(c.relancee_le)}`)}</div>}</td>
                <td>{c.ouverte_le ? dateFr(c.ouverte_le) : "—"}</td>
                <td>{c.repondue_le ? dateFr(c.repondue_le) : "—"}</td>
                <td><span className={`etat ${style}`}>{libelle}</span></td>
                <td className="n">{conseiller && attend && <>
                  <button className="lien" type="button" onClick={() => agir(`${c.id}/relance`)}>{t("Relancer", "Send a reminder")}</button>{" "}
                  <button className="lien" type="button" onClick={() => agir(`${c.id}/annulation`)}>{t("Annuler", "Cancel")}</button></>}</td>
              </tr>
            );
          })}</tbody>
        </table></div>
      )}
    </section>
  );
}
