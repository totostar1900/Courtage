import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Anomalies, Erreur } from "../composants/communs";
import { MenuActions } from "../composants/MenuActions";
import { dateFr } from "../format";
import { t } from "../i18n";
import type { Fichier } from "../types";
import { useConfirmation } from "../composants/Confirmer";
import { useDossier } from "./Dossier";

export default function Personnel() {
  const d = useDossier();
  const [erreur, setErreur] = useState<unknown>(null);
  const [depose, setDepose] = useState<Fichier | null>(null);
  const [ouvert, setOuvert] = useState<string | null>(null);
  const peutDeposer = d.role !== "lecteur_client";
  const [erreurTelechargement, setErreurTelechargement] = useState<unknown>(null);

  async function telecharger(chemin: string, nom: string) {
    setErreurTelechargement(null);
    try { await api.telecharger(chemin, nom); } catch (e) { setErreurTelechargement(e); }
  }

  const [demander, fenetre] = useConfirmation();

  function agir(f: Fichier, quoi: "supprimer" | "alleger") {
    const n = f.brouillons?.length ?? 0;
    const brouillons = n ? t(` ${n} étude${n > 1 ? "s" : ""} en brouillon qui s'appuie${n > 1 ? "nt" : ""} dessus ${n > 1 ? "partiront" : "partira"} avec.`,
      ` ${n} draft stud${n > 1 ? "ies" : "y"} based on it will go with it.`) : "";
    demander({
      titre: quoi === "supprimer" ? t(`Supprimer « ${f.nom_fichier} »`, `Delete “${f.nom_fichier}”`)
        : t(`Alléger « ${f.nom_fichier} »`, `Slim down “${f.nom_fichier}”`),
      message: <p>{quoi === "supprimer" ? t("Le fichier quitte la plateforme.", "The file leaves the platform.")
        : t("Ses lignes sont vidées ; son nom, sa date et son empreinte restent, et les études émises restent prouvées.",
          "Its rows are emptied; its name, date and fingerprint remain, and issued studies remain provable.")}
        {brouillons}</p>,
      mot: quoi === "supprimer" ? t("SUPPRIMER", "DELETE") : t("ALLEGER", "SLIM"),
      bouton: quoi === "supprimer" ? t("Supprimer", "Delete") : t("Alléger", "Slim down"),
      action: async () => {
        if (quoi === "supprimer") await api.del(`/organisations/${d.org.id}/fichiers/${f.id}`);
        else await api.post(`/organisations/${d.org.id}/fichiers/${f.id}/allegement`);
        d.recharger();
      },
    });
  }

  const actionsFichier = (f: Fichier) => [
    { libelle: t("Télécharger (Excel)", "Download (Excel)"), cache: Boolean(f.vide_le),
      agir: () => telecharger(`/organisations/${d.org.id}/fichiers/${f.id}/telechargement`, `personnel-${f.date_donnees}.xlsx`) },
    { libelle: t("Alléger : vider les lignes, garder l'empreinte", "Slim down: empty the rows, keep the fingerprint"), agir: () => agir(f, "alleger"),
      cache: !peutDeposer || Boolean(f.vide_le) },
    { libelle: t("Supprimer", "Delete"), agir: () => agir(f, "supprimer"), danger: true, cache: !peutDeposer,
      raison: f.etudes_emises ? t(`${f.etudes_emises} étude${f.etudes_emises > 1 ? "s" : ""} émise${f.etudes_emises > 1 ? "s" : ""} le cite${f.etudes_emises > 1 ? "nt" : ""} : l'alléger plutôt.`,
        `${f.etudes_emises} issued stud${f.etudes_emises > 1 ? "ies refer" : "y refers"} to it: slim it down instead.`) : null },
  ];

  async function deposer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setErreur(null);
    const donnees = new FormData(ev.currentTarget);
    if (!donnees.get("periodicite")) donnees.delete("periodicite");
    try {
      setDepose(await api.post<Fichier>(`/organisations/${d.org.id}/fichiers`, donnees));
      d.recharger();
    } catch (e) {
      setErreur(e);
    }
  }

  return (
    <>
      {fenetre}
      <h1>{t("Votre personnel", "Your staff")}</h1>
      <p>{t("Un fichier Excel ou CSV : matricule, date de naissance, date d'embauche, salaire, et la catégorie si votre "
        + "régime en distingue.", "An Excel or CSV file: employee number, date of birth, hire date, salary, and the category if your plan distinguishes them.")}{" "}
        <strong>{t("Aucun nom n'est lu", "No name is read")}</strong>{t(" : une colonne de nom est ignorée sans être ouverte.",
          ": a name column is ignored without being opened.")}</p>

      <div className="carte canevas section" style={{ maxWidth: 620, marginBottom: 16 }}>
        <div>
          <strong>{t("Le canevas à remplir", "The template to fill in")}</strong>
          <p className="discret" style={{ margin: "4px 0 0" }}>{t("Un classeur Excel aux bonnes colonnes, avec un mode d'emploi "
            + "et un exemple. Rempli, il se dépose tel quel.", "An Excel workbook with the right columns, instructions and an example. Once filled in, upload it as is.")}</p>
        </div>
        <button type="button" onClick={() => telecharger("/referentiel/canevas-personnel", "canevas-personnel.xlsx")}>
          {t("Télécharger le canevas", "Download the template")}</button>
      </div>
      <Erreur erreur={erreurTelechargement} />

      {peutDeposer && (
        <form className="carte formulaire" onSubmit={deposer} style={{ maxWidth: 620 }}>
          <label>{t("Fichier du personnel", "Staff file")}<input id="fichier" name="fichier" type="file" accept=".xlsx,.xlsm,.csv" required /></label>
          <div className="grille g2">
            <label>{t("Données arrêtées au", "Data as at")}<input id="date_donnees" name="date_donnees" type="date" required /></label>
            <label>{t("Les salaires sont", "Salaries are")}
              <select id="periodicite" name="periodicite" defaultValue="">
                <option value="">{t("dits par l'intitulé de colonne", "given by the column heading")}</option>
                <option value="mensuel">{t("mensuels", "monthly")}</option>
                <option value="annuel">{t("annuels", "annual")}</option>
              </select>
            </label>
          </div>
          <div className="actions"><button className="principal">{t("Déposer", "Upload")}</button></div>
          <Erreur erreur={erreur} />
          {depose && (
            <p><span className="etat bien">{t("Déposé", "Uploaded")}</span> {t(`${depose.effectif} salariés lus.`, `${depose.effectif} employees read.`)}
              {depose.anomalies.length > 0 && t(` ${depose.anomalies.length} point(s) à regarder ci-dessous.`,
                ` ${depose.anomalies.length} point(s) to review below.`)}</p>
          )}
        </form>
      )}

      <div className="section">
        <h2>{t("Fichiers déposés", "Uploaded files")}</h2>
        {d.fichiers.length === 0 && <p className="discret">{t("Aucun fichier pour l'instant.", "No file yet.")}</p>}
        <div className="defile">
          <table>
            <thead><tr><th>{t("Fichier", "File")}</th><th>{t("Données au", "Data as at")}</th><th className="n">{t("Salariés", "Employees")}</th>
              <th>{t("État", "Status")}</th><th /></tr></thead>
            <tbody>
              {d.fichiers.map((f) => {
                const bloquants = f.anomalies.filter((a) => a.niveau === "bloquant").length;
                return [
                  <tr key={f.id} className="cliquable" onClick={() => setOuvert(ouvert === f.id ? null : f.id)}>
                    <td>{f.nom_fichier}<div className="discret">{t(`déposé le ${dateFr(f.depose_le)}`, `uploaded on ${dateFr(f.depose_le)}`)}</div></td>
                    <td>{dateFr(f.date_donnees)}</td>
                    <td className="n">{f.vide_le ? <span className="discret" title={t("Lignes vidées : nom, date et empreinte gardés", "Rows emptied: name, date and fingerprint kept")}>{t("allégé", "slimmed down")}</span> : f.effectif}</td>
                    <td>{bloquants ? <span className="etat grave">{t(`${bloquants} à corriger`, `${bloquants} to fix`)}</span>
                      : f.anomalies.length ? <span className="etat attention">{t(`${f.anomalies.length} à regarder`, `${f.anomalies.length} to review`)}</span>
                      : <span className="etat bien">{t("Complet", "Complete")}</span>}</td>
                    <td className="n" onClick={(e) => e.stopPropagation()}>
                      <MenuActions libelle={t(`Actions sur ${f.nom_fichier}`, `Actions on ${f.nom_fichier}`)} actions={actionsFichier(f)} />
                    </td>
                  </tr>,
                  ouvert === f.id && (
                    <tr key={`${f.id}-a`}><td colSpan={5}>
                      <div className="volet-tete"><strong>{t("Contrôles du fichier", "File checks")}</strong>
                        <button type="button" className="fermer-volet" onClick={() => setOuvert(null)} aria-label={t("Fermer", "Close")} title={t("Fermer", "Close")}>×</button></div>
                      <Anomalies anomalies={f.anomalies} /></td></tr>
                  ),
                ];
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
