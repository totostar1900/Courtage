import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api";
import { dateFr } from "../format";
import type { ActionCycle, Cycle, EtatCycle } from "../types";
import { Erreur, useCharge, Volet } from "./communs";
import { t } from "../i18n";

/** Les quatre actes sur le cycle d'un dossier. Une fonction : la langue se lit au rendu. */
const actions = (): Record<ActionCycle, { bouton: string; titre: string; explication: string }> => ({
  suspendre: {
    bouton: t("Suspendre", "Suspend"), titre: t("Suspendre le dossier", "Suspend the file"),
    explication: t("Tout reste lisible et exportable, pour chacun. Rien ne s'émet (ni étude, ni cahier des charges) tant "
      + "que vous ne l'avez pas repris. Rien n'est effacé.",
      "Everything stays readable and exportable, for everyone. Nothing is issued (no study, no specifications) until "
      + "you resume it. Nothing is deleted."),
  },
  cloturer: {
    bouton: t("Clôturer", "Close"), titre: t("Clôturer le dossier", "Close the file"),
    explication: t("Le dossier passe en lecture seule pour tous. Il sera archivé dans 90 jours : le personnel déposé "
      + "sera alors effacé et le dossier ne s'ouvrira plus. Les études, rapports scellés et le journal sont conservés, "
      + "et chaque document reste vérifiable par son numéro. D'ici là, vous pouvez le reprendre.",
      "The file becomes read-only for everyone. It will be archived in 90 days: the uploaded workforce data will then "
      + "be erased and the file will no longer open. Studies, sealed reports and the log are kept, and every document "
      + "remains verifiable by its number. Until then, you can resume it."),
  },
  reprendre: {
    bouton: t("Reprendre", "Resume"), titre: t("Reprendre le dossier", "Resume the file"),
    explication: t("Le dossier redevient ouvert. L'historique garde la trace de l'interruption.",
      "The file is open again. The history keeps a record of the interruption."),
  },
  supprimer: {
    bouton: t("Supprimer", "Delete"), titre: t("Supprimer le dossier", "Delete the file"),
    explication: t("Réservé à un dossier ouvert par erreur, qui n'a encore rien reçu. Il disparaît de toutes les listes "
      + "et ses membres le quittent ; le journal garde la trace de sa création et de sa suppression.",
      "Only for a file opened by mistake that has not yet received anything. It disappears from every list and its "
      + "members leave it; the log keeps a record of its creation and deletion."),
  },
});

/** En tête de chaque page d'un dossier qui n'est pas ouvert : ce que son état permet, et où en savoir plus. */
export function BandeauCycle({ org }: { org: { id: string; etat?: EtatCycle; etat_depuis?: string } }) {
  if (org.etat === "suspendu")
    return (
      <div className="constat avertit bandeau-cycle" role="status">
        <div className="titre">{t(`Dossier suspendu depuis le ${dateFr(org.etat_depuis)}`,
                                    `File suspended since ${dateFr(org.etat_depuis)}`)}</div>
        {t("Tout se lit et s'exporte ; aucune étude ne s'émet et aucun cahier ne part avant sa reprise.",
           "Everything can be read and exported; no study is issued and no specifications are sent until it resumes.")}{" "}
        <Link to={`/dossier/${org.id}/equipe`}>{t("Motif et historique", "Reason and history")}</Link>
      </div>
    );
  if (org.etat === "cloture")
    return (
      <div className="constat informe bandeau-cycle" role="status">
        <div className="titre">{t(`Dossier clôturé le ${dateFr(org.etat_depuis)} : lecture seule`,
                                    `File closed on ${dateFr(org.etat_depuis)}: read-only`)}</div>
        {t("Il sera archivé 90 jours après sa clôture. Exportez d'ici là ce que vous voulez garder.",
           "It will be archived 90 days after closing. Until then, export whatever you want to keep.")}{" "}
        <Link to={`/dossier/${org.id}/equipe`}>{t("Motif et historique", "Reason and history")}</Link>
      </div>
    );
  return null;
}

/** L'état du dossier, son histoire, et pour le conseiller : suspendre, clôturer, reprendre, supprimer. */
export function EtatDuDossier({ orgId, conseiller, onChange }: { orgId: string; conseiller: boolean; onChange: () => void }) {
  const { donnee: c, erreur, recharger } = useCharge(() => api.get<Cycle>(`/organisations/${orgId}/cycle`), [orgId]);
  const [action, setAction] = useState<ActionCycle | null>(null);
  if (erreur) return <Erreur erreur={erreur} />;
  if (!c) return null;
  const possibles = c.actions.filter((a) => a !== "supprimer" || c.supprimable);
  return (
    <section className="carte section" aria-labelledby="etat-dossier">
      <div className="actions" style={{ justifyContent: "space-between", alignItems: "center", marginTop: 0 }}>
        <h2 id="etat-dossier" style={{ margin: 0 }}>{t("État du dossier", "File status")}</h2>
        <span className={`etat ${c.etat === "ouvert" ? "bien" : c.etat === "suspendu" ? "attention" : "neutre"}`}>
          {c.libelle} {t("depuis le", "since")} {dateFr(c.depuis)}</span>
      </div>
      {c.archivage_prevu && <p>{t("Archivage prévu le ", "Archiving scheduled on ")}<b>{dateFr(c.archivage_prevu)}</b>.</p>}
      {conseiller && possibles.length > 0 && (
        <div className="actions">
          {possibles.map((a) => (
            <button key={a} type="button" className={a === "reprendre" ? "principal" : a === "supprimer" ? "danger" : ""}
                    onClick={() => setAction(a)}>{actions()[a].bouton}</button>
          ))}
        </div>
      )}
      {!conseiller && <p className="discret">{t("Seul le conseiller change l'état du dossier.", "Only the adviser changes the file status.")}</p>}
      {c.historique.length > 0 && (
        <div className="defile section">
          <table>
            <thead><tr><th>{t("Le", "On")}</th><th>{t("État", "Status")}</th><th>{t("Motif", "Reason")}</th><th>{t("Par", "By")}</th></tr></thead>
            <tbody>{c.historique.map((h, i) => (
              <tr key={i}><td>{dateFr(h.le)}</td><td>{h.libelle}</td>
                <td>{[h.motif_libelle, h.motif].filter(Boolean).join(" — ") || "—"}</td><td>{h.par}</td></tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {action && <Changer orgId={orgId} action={action} cycle={c} onFermer={() => setAction(null)}
                          onFait={() => { setAction(null); recharger(); onChange(); }} />}
    </section>
  );
}

function Changer({ orgId, action, cycle, onFermer, onFait }: {
  orgId: string; action: ActionCycle; cycle: Cycle; onFermer: () => void; onFait: () => void;
}) {
  const [erreur, setErreur] = useState<unknown>(null);
  const [code, setCode] = useState("");
  const aller = useNavigate();
  const motifs = cycle.motifs[action];
  async function valider(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await api.post(`/organisations/${orgId}/cycle`, {
        action, motif_code: code || null, motif: String(f.get("motif") ?? "").trim() || null });
      if (action === "supprimer") aller("/");
      else onFait();
    } catch (e) { setErreur(e); }
  }
  const a = actions()[action];
  return (
    <Volet titre={a.titre} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={valider}>
        <p>{a.explication}</p>
        {motifs.length > 0 && (
          <label>{t("Motif", "Reason")}
            <select value={code} onChange={(e) => setCode(e.target.value)} required>
              <option value="" disabled>{t("Choisir…", "Choose…")}</option>
              {motifs.map((m) => <option key={m.code} value={m.code}>{m.libelle}</option>)}
            </select>
          </label>
        )}
        <label>{motifs.length ? t("Précision (facultative, sauf pour « Autre motif »)", "Details (optional, except for “Other reason”)")
                            : t("Pourquoi le dossier reprend", "Why the file is resuming")}
          <textarea name="motif" rows={2} maxLength={500} required={!motifs.length || code === "autre"} /></label>
        <p className="discret">{t("Le motif est daté, signé à votre nom et visible de tous les membres du dossier.", "The reason is dated, signed in your name and visible to every member of the file.")}</p>
        <div className="actions">
          <button className={action === "supprimer" ? "danger" : "principal"}>{a.bouton}</button>
          <button type="button" onClick={onFermer}>{t("Annuler", "Cancel")}</button>
        </div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
