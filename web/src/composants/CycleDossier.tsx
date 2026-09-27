import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api";
import { dateFr } from "../format";
import type { ActionCycle, Cycle, EtatCycle } from "../types";
import { Erreur, useCharge, Volet } from "./communs";

const ACTIONS: Record<ActionCycle, { bouton: string; titre: string; explication: string }> = {
  suspendre: {
    bouton: "Suspendre", titre: "Suspendre le dossier",
    explication: "Tout reste lisible et exportable, pour chacun. Rien ne s'émet (ni étude, ni cahier des charges) tant "
      + "que vous ne l'avez pas repris. Rien n'est effacé.",
  },
  cloturer: {
    bouton: "Clôturer", titre: "Clôturer le dossier",
    explication: "Le dossier passe en lecture seule pour tous. Il sera archivé dans 90 jours : le personnel déposé "
      + "sera alors effacé et le dossier ne s'ouvrira plus. Les études, rapports scellés et le journal sont conservés, "
      + "et chaque document reste vérifiable par son numéro. D'ici là, vous pouvez le reprendre.",
  },
  reprendre: {
    bouton: "Reprendre", titre: "Reprendre le dossier",
    explication: "Le dossier redevient ouvert. L'historique garde la trace de l'interruption.",
  },
  supprimer: {
    bouton: "Supprimer", titre: "Supprimer le dossier",
    explication: "Réservé à un dossier ouvert par erreur, qui n'a encore rien reçu. Il disparaît de toutes les listes "
      + "et ses membres le quittent ; le journal garde la trace de sa création et de sa suppression.",
  },
};

/** En tête de chaque page d'un dossier qui n'est pas ouvert : ce que son état permet, et où en savoir plus. */
export function BandeauCycle({ org }: { org: { id: string; etat?: EtatCycle; etat_depuis?: string } }) {
  if (org.etat === "suspendu")
    return (
      <div className="constat avertit bandeau-cycle" role="status">
        <div className="titre">Dossier suspendu depuis le {dateFr(org.etat_depuis)}</div>
        Tout se lit et s'exporte ; aucune étude ne s'émet et aucun cahier ne part avant sa reprise.{" "}
        <Link to={`/dossier/${org.id}/equipe`}>Motif et historique</Link>
      </div>
    );
  if (org.etat === "cloture")
    return (
      <div className="constat informe bandeau-cycle" role="status">
        <div className="titre">Dossier clôturé le {dateFr(org.etat_depuis)} : lecture seule</div>
        Il sera archivé 90 jours après sa clôture. Exportez d'ici là ce que vous voulez garder.{" "}
        <Link to={`/dossier/${org.id}/equipe`}>Motif et historique</Link>
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
        <h2 id="etat-dossier" style={{ margin: 0 }}>État du dossier</h2>
        <span className={`etat ${c.etat === "ouvert" ? "bien" : c.etat === "suspendu" ? "attention" : "neutre"}`}>
          {c.libelle} depuis le {dateFr(c.depuis)}</span>
      </div>
      {c.archivage_prevu && <p>Archivage prévu le <b>{dateFr(c.archivage_prevu)}</b>.</p>}
      {conseiller && possibles.length > 0 && (
        <div className="actions">
          {possibles.map((a) => (
            <button key={a} type="button" className={a === "reprendre" ? "principal" : a === "supprimer" ? "danger" : ""}
                    onClick={() => setAction(a)}>{ACTIONS[a].bouton}</button>
          ))}
        </div>
      )}
      {!conseiller && <p className="discret">Seul le conseiller change l'état du dossier.</p>}
      {c.historique.length > 0 && (
        <div className="defile section">
          <table>
            <thead><tr><th>Le</th><th>État</th><th>Motif</th><th>Par</th></tr></thead>
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
  const a = ACTIONS[action];
  return (
    <Volet titre={a.titre} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={valider}>
        <p>{a.explication}</p>
        {motifs.length > 0 && (
          <label>Motif
            <select value={code} onChange={(e) => setCode(e.target.value)} required>
              <option value="" disabled>Choisir…</option>
              {motifs.map((m) => <option key={m.code} value={m.code}>{m.libelle}</option>)}
            </select>
          </label>
        )}
        <label>{motifs.length ? "Précision (facultative, sauf pour « Autre motif »)" : "Pourquoi le dossier reprend"}
          <textarea name="motif" rows={2} maxLength={500} required={!motifs.length || code === "autre"} /></label>
        <p className="discret">Le motif est daté, signé à votre nom et visible de tous les membres du dossier.</p>
        <div className="actions">
          <button className={action === "supprimer" ? "danger" : "principal"}>{a.bouton}</button>
          <button type="button" onClick={onFermer}>Annuler</button>
        </div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
