import { useState } from "react";

import { api } from "../api";
import { Erreur, useCharge, Volet } from "./communs";
import { t } from "../i18n";

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
      <h2 id="nettoyer" style={{ marginTop: 0 }}>{t("Nettoyer le dossier", "Clean up the file")}</h2>
      <p>{t("La plateforme sert à souscrire et à suivre une assurance IFC, pas à garder le personnel. Une fois le service "
        + "en place, l'entreprise télécharge ses documents et fait partir ce qui ne sert plus. Les sceaux et le journal "
        + "restent : chaque document se vérifie toujours par son numéro.",
        "The platform is for taking out and monitoring IFC insurance, not for keeping workforce data. Once the service "
        + "is in place, the company downloads its documents and removes what is no longer needed. The seals and the log "
        + "remain: every document can still be verified by its number.")}</p>
      {ouvert ? <Etapes orgId={orgId} onFermer={() => setOuvert(false)} onFait={() => { setOuvert(false); onFait(); }} />
        : <div className="actions"><button type="button" onClick={() => setOuvert(true)}>{t("Nettoyer le dossier…", "Clean up the file…")}</button></div>}
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
    <Volet titre={t("Dossier nettoyé", "File cleaned up")} onFermer={onFait} className="section">
      <ul>
        {fait.fichiers_alleges > 0 && <li>{t(`${fait.fichiers_alleges} fichier(s) du personnel allégé(s)`, `${fait.fichiers_alleges} workforce file(s) slimmed down`)}</li>}
        {fait.fichiers_supprimes > 0 && <li>{t(`${fait.fichiers_supprimes} fichier(s) du personnel supprimé(s)`, `${fait.fichiers_supprimes} workforce file(s) deleted`)}</li>}
        {fait.etudes_brouillon + fait.versions_brouillon > 0 &&
          <li>{t(`${fait.etudes_brouillon} étude(s) et ${fait.versions_brouillon} version(s) en brouillon supprimée(s)`,
                `${fait.etudes_brouillon} draft study(ies) and ${fait.versions_brouillon} draft version(s) deleted`)}</li>}
        {fait.etudes_emises > 0 && <li>{t(`${fait.etudes_emises} étude(s) émise(s) supprimée(s), leur sceau conservé`, `${fait.etudes_emises} issued study(ies) deleted, their seal kept`)}</li>}
      </ul>
      <p className="discret">{t("Le journal garde la trace du nettoyage.", "The log keeps a record of the clean-up.")}</p>
      <div className="actions"><button className="principal" onClick={onFait}>{t("Fermer", "Close")}</button></div>
    </Volet>
  );
  const rien = !fichiers && !brouillons && !emises;
  return (
    <Volet titre={t("En trois temps", "In three steps")} onFermer={onFermer} className="section">
      <ol className="etapes-nettoyage">
        <li>
          <b>{t("Télécharger l'archive.", "Download the archive.")}</b>{" "}
          {t(`${inv.documents} document(s) scellé(s) en PDF, les études émises en Excel, et un sommaire des numéros à vérifier.`,
             `${inv.documents} sealed document(s) as PDF, issued studies as Excel, and a list of the numbers to verify.`)}
          <div className="actions"><button type="button" className={archive ? "" : "principal"} onClick={telecharger}>
            {archive ? t("Archive téléchargée — la retélécharger", "Archive downloaded — download it again")
                     : t("Télécharger l'archive (ZIP)", "Download the archive (ZIP)")}</button></div>
        </li>
        <li>
          <b>{t("Choisir ce qui part.", "Choose what goes.")}</b>
          <fieldset className="choix-nettoyage">
            <legend>{t(`Le personnel (${inv.fichiers.total} fichier(s), ${inv.fichiers.lignes} ligne(s))`,
                      `Workforce data (${inv.fichiers.total} file(s), ${inv.fichiers.lignes} row(s))`)}</legend>
            <label><input type="radio" name="fichiers" checked={fichiers === "alleger"} onChange={() => setFichiers("alleger")} />
              {t("Alléger : vider les lignes, garder le nom, la date et l'empreinte",
                 "Slim down: empty the rows, keep the name, the date and the fingerprint")}</label>
            <label><input type="radio" name="fichiers" checked={fichiers === "supprimer"} onChange={() => setFichiers("supprimer")} />
              {t("Supprimer ce qu'aucune étude émise ne cite, alléger le reste",
                 "Delete what no issued study cites, slim down the rest")}</label>
            <label><input type="radio" name="fichiers" checked={fichiers === ""} onChange={() => setFichiers("")} />
              {t("Garder tel quel", "Keep as is")}</label>
          </fieldset>
          <label className="case"><input type="checkbox" checked={brouillons} onChange={(e) => setBrouillons(e.target.checked)} />
            {t(`Les brouillons : ${inv.brouillons.etudes} étude(s) et ${inv.brouillons.versions} version(s) de régime`,
               `Drafts: ${inv.brouillons.etudes} study(ies) and ${inv.brouillons.versions} plan version(s)`)}</label>
          <label className="case"><input type="checkbox" checked={emises} onChange={(e) => setEmises(e.target.checked)}
                                         disabled={!inv.etudes_emises.supprimables} />
            {t(`Les études émises et leur rapport : ${inv.etudes_emises.supprimables} sur ${inv.etudes_emises.total}`,
               `Issued studies and their report: ${inv.etudes_emises.supprimables} of ${inv.etudes_emises.total}`)}
            {inv.etudes_emises.citees_par_un_cahier > 0 && t(` (${inv.etudes_emises.citees_par_un_cahier} citée(s) par un cahier des charges restent)`,
              ` (${inv.etudes_emises.citees_par_un_cahier} cited by specifications stay)`)}.
            {" "}{t("Leur sceau reste : le numéro se vérifie toujours.", "Their seal remains: the number can still be verified.")}</label>
        </li>
        <li>
          <b>{t("Confirmer.", "Confirm.")}</b> {t("Écrire", "Type")} <code>{inv.confirmation}</code> :
          <input aria-label={t("Confirmation", "Confirmation")} value={confirmation} onChange={(e) => setConfirmation(e.target.value)} style={{ maxWidth: 200 }} />
          {!archive && <p className="discret">{t("Conseil : télécharger l'archive d'abord.", "Tip: download the archive first.")}</p>}
          <div className="actions">
            <button className="danger" onClick={nettoyer}
                    disabled={rien || confirmation.trim().toUpperCase() !== inv.confirmation}>{t("Nettoyer", "Clean up")}</button>
            <button type="button" onClick={onFermer}>{t("Annuler", "Cancel")}</button>
          </div>
        </li>
      </ol>
      <Erreur erreur={erreur} />
    </Volet>
  );
}
