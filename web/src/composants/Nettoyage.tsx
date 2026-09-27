import { useState } from "react";

import { api } from "../api";
import { Erreur, useCharge, Volet } from "./communs";

interface Inventaire {
  fichiers: { total: number; actifs: number; lignes: number };
  brouillons: { etudes: number; versions: number };
  etudes_emises: { total: number; supprimables: number; citees_par_un_cahier: number };
  documents: number;
  confirmation: string;
}

/** « Nettoyer le dossier » : télécharger l'archive, choisir ce qui part, confirmer. Les sceaux et le journal restent :
 *  chaque numéro de document se vérifie toujours. */
export function NettoyerDossier({ orgId, onFait }: { orgId: string; onFait: () => void }) {
  const [ouvert, setOuvert] = useState(false);
  return (
    <section className="carte section" aria-labelledby="nettoyer">
      <h2 id="nettoyer" style={{ marginTop: 0 }}>Nettoyer le dossier</h2>
      <p>La plateforme sert à souscrire et à suivre une assurance IFC, pas à garder le personnel. Une fois le service en
        place, l'entreprise télécharge ses documents et fait partir ce qui ne sert plus. Les sceaux et le journal
        restent : chaque document se vérifie toujours par son numéro.</p>
      {ouvert ? <Etapes orgId={orgId} onFermer={() => setOuvert(false)} onFait={() => { setOuvert(false); onFait(); }} />
        : <div className="actions"><button type="button" onClick={() => setOuvert(true)}>Nettoyer le dossier…</button></div>}
    </section>
  );
}

function Etapes({ orgId, onFermer, onFait }: { orgId: string; onFermer: () => void; onFait: () => void }) {
  const { donnee: inv, erreur: erreurLecture } = useCharge(() => api.get<Inventaire>(`/organisations/${orgId}/nettoyage`), [orgId]);
  const [archive, setArchive] = useState(false);
  const [fichiers, setFichiers] = useState<"" | "alleger" | "supprimer">("alleger");
  const [brouillons, setBrouillons] = useState(true);
  const [emises, setEmises] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [erreur, setErreur] = useState<unknown>(null);
  const [fait, setFait] = useState<Record<string, number> | null>(null);
  if (erreurLecture) return <Erreur erreur={erreurLecture} />;
  if (!inv) return null;

  async function telecharger() {
    setErreur(null);
    try { await api.telecharger(`/organisations/${orgId}/archive`, "archive-dossier.zip"); setArchive(true); }
    catch (e) { setErreur(e); }
  }
  async function nettoyer() {
    setErreur(null);
    try {
      setFait(await api.post(`/organisations/${orgId}/nettoyage`, {
        fichiers: fichiers || null, brouillons, etudes_emises: emises, confirmation }));
    } catch (e) { setErreur(e); }
  }
  if (fait) return (
    <Volet titre="Dossier nettoyé" onFermer={onFait} className="section">
      <ul>
        {fait.fichiers_alleges > 0 && <li>{fait.fichiers_alleges} fichier(s) du personnel allégé(s)</li>}
        {fait.fichiers_supprimes > 0 && <li>{fait.fichiers_supprimes} fichier(s) du personnel supprimé(s)</li>}
        {fait.etudes_brouillon + fait.versions_brouillon > 0 &&
          <li>{fait.etudes_brouillon} étude(s) et {fait.versions_brouillon} version(s) en brouillon supprimée(s)</li>}
        {fait.etudes_emises > 0 && <li>{fait.etudes_emises} étude(s) émise(s) supprimée(s), leur sceau conservé</li>}
      </ul>
      <p className="discret">Le journal garde la trace du nettoyage.</p>
      <div className="actions"><button className="principal" onClick={onFait}>Fermer</button></div>
    </Volet>
  );
  const rien = !fichiers && !brouillons && !emises;
  return (
    <Volet titre="En trois temps" onFermer={onFermer} className="section">
      <ol className="etapes-nettoyage">
        <li>
          <b>Télécharger l'archive.</b> {inv.documents} document(s) scellé(s) en PDF, les études émises en Excel, et un
          sommaire des numéros à vérifier.
          <div className="actions"><button type="button" className={archive ? "" : "principal"} onClick={telecharger}>
            {archive ? "Archive téléchargée — la retélécharger" : "Télécharger l'archive (ZIP)"}</button></div>
        </li>
        <li>
          <b>Choisir ce qui part.</b>
          <fieldset className="choix-nettoyage">
            <legend>Le personnel ({inv.fichiers.total} fichier(s), {inv.fichiers.lignes} ligne(s))</legend>
            <label><input type="radio" name="fichiers" checked={fichiers === "alleger"} onChange={() => setFichiers("alleger")} />
              Alléger : vider les lignes, garder le nom, la date et l'empreinte</label>
            <label><input type="radio" name="fichiers" checked={fichiers === "supprimer"} onChange={() => setFichiers("supprimer")} />
              Supprimer ce qu'aucune étude émise ne cite, alléger le reste</label>
            <label><input type="radio" name="fichiers" checked={fichiers === ""} onChange={() => setFichiers("")} />
              Garder tel quel</label>
          </fieldset>
          <label className="case"><input type="checkbox" checked={brouillons} onChange={(e) => setBrouillons(e.target.checked)} />
            Les brouillons : {inv.brouillons.etudes} étude(s) et {inv.brouillons.versions} version(s) de régime</label>
          <label className="case"><input type="checkbox" checked={emises} onChange={(e) => setEmises(e.target.checked)}
                                         disabled={!inv.etudes_emises.supprimables} />
            Les études émises et leur rapport : {inv.etudes_emises.supprimables} sur {inv.etudes_emises.total}
            {inv.etudes_emises.citees_par_un_cahier > 0 && ` (${inv.etudes_emises.citees_par_un_cahier} citée(s) par un cahier des charges restent)`}.
            Leur sceau reste : le numéro se vérifie toujours.</label>
        </li>
        <li>
          <b>Confirmer.</b> Écrire <code>{inv.confirmation}</code> :
          <input aria-label="Confirmation" value={confirmation} onChange={(e) => setConfirmation(e.target.value)} style={{ maxWidth: 200 }} />
          {!archive && <p className="discret">Conseil : télécharger l'archive d'abord.</p>}
          <div className="actions">
            <button className="danger" onClick={nettoyer}
                    disabled={rien || confirmation.trim().toUpperCase() !== inv.confirmation}>Nettoyer</button>
            <button type="button" onClick={onFermer}>Annuler</button>
          </div>
        </li>
      </ol>
      <Erreur erreur={erreur} />
    </Volet>
  );
}
