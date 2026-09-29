import { useState } from "react";

import { api } from "../api";
import { dateFr } from "../format";
import { t } from "../i18n";
import { Erreur, useCharge } from "./communs";

interface Demande { id: string; nom: string; entreprise: string; telephone: string; courriel: string | null;
  creneau: string; message: string | null; recue_le: string; statut: "a_rappeler" | "rappelee" | "sans_suite";
  note: string | null; traitee_le: string | null; traitee_par: string | null }

const creneaux = (): Record<string, string> => ({ matin: t("le matin", "morning"), apres_midi: t("l'après-midi", "afternoon"),
  indifferent: t("indifférent", "any time") });
const statuts = (): Record<Demande["statut"], [string, string]> => ({ a_rappeler: [t("À rappeler", "To call"), "attention"],
  rappelee: [t("Rappelée", "Called back"), "bien"], sans_suite: [t("Sans suite", "No follow-up"), "neutre"] });

/** Les demandes de rappel de la vitrine, pour le courtier : à rappeler d'abord, les plus anciennes en tête. */
export default function DemandesRappel() {
  const { donnee, erreur, recharger } = useCharge(() => api.get<Demande[]>("/rappels"), []);
  const [erreurAction, setErreurAction] = useState<unknown>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  if (!donnee || donnee.length === 0) return erreur ? <Erreur erreur={erreur} /> : null;
  const aRappeler = donnee.filter((d) => d.statut === "a_rappeler").length;
  async function traiter(d: Demande, statut: Demande["statut"]) {
    const note = statut === "a_rappeler" ? null : (notes[d.id] ?? "").trim() || null;
    setErreurAction(null);
    try { await api.put(`/rappels/${d.id}`, { statut, note }); recharger(); } catch (e) { setErreurAction(e); }
  }
  return (
    <section className="section" aria-labelledby="demandes-rappel">
      <h2 id="demandes-rappel">{t("Demandes de rappel", "Callback requests")}
        {aRappeler > 0 && <>{" "}<span className="etat attention">{t(`${aRappeler} à rappeler`, `${aRappeler} to call`)}</span></>}</h2>
      <Erreur erreur={erreurAction} />
      <div className="defile"><table>
        <thead><tr><th>{t("Reçue le", "Received on")}</th><th>{t("Qui", "Who")}</th><th>{t("Téléphone", "Phone")}</th>
          <th>{t("Message", "Message")}</th><th>{t("État", "Status")}</th><th aria-label={t("Actions", "Actions")} /></tr></thead>
        <tbody>{donnee.map((d) => {
          const [libelle, style] = statuts()[d.statut];
          return (
            <tr key={d.id}>
              <td>{dateFr(d.recue_le)}</td>
              <td>{d.nom}<div className="discret">{d.entreprise}{d.courriel && <> · {d.courriel}</>}</div></td>
              <td><a href={`tel:${d.telephone}`}>{d.telephone}</a><div className="discret">{creneaux()[d.creneau]}</div></td>
              <td className="discret">{d.message ?? "—"}{d.note && <div>{t("Note : ", "Note: ")}{d.note}</div>}</td>
              <td><span className={`etat ${style}`}>{libelle}</span></td>
              <td className="n">{d.statut === "a_rappeler" ? <>
                <input aria-label={t(`Note sur la demande de ${d.nom}`, `Note on ${d.nom}'s request`)} placeholder={t("Note…", "Note…")}
                       value={notes[d.id] ?? ""} onChange={(e) => setNotes({ ...notes, [d.id]: e.target.value })} />{" "}
                <button className="lien" type="button" onClick={() => traiter(d, "rappelee")}>{t("Rappelée", "Called back")}</button>{" "}
                <button className="lien" type="button" onClick={() => traiter(d, "sans_suite")}>{t("Sans suite", "No follow-up")}</button></>
                : <button className="lien" type="button" onClick={() => traiter(d, "a_rappeler")}>{t("Rouvrir", "Reopen")}</button>}</td>
            </tr>
          );
        })}</tbody>
      </table></div>
    </section>
  );
}
