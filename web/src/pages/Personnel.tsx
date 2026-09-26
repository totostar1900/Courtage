import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Anomalies, Erreur } from "../composants/communs";
import { dateFr } from "../format";
import type { Fichier } from "../types";
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
      <h1>Votre personnel</h1>
      <p>Un fichier Excel ou CSV : matricule, date de naissance, date d'embauche, salaire, et la catégorie si votre
        régime en distingue. <strong>Aucun nom n'est lu</strong> : une colonne de nom est ignorée sans être ouverte.</p>

      <div className="carte canevas section" style={{ maxWidth: 620 }}>
        <div>
          <strong>Le canevas à remplir</strong>
          <p className="discret" style={{ margin: "4px 0 0" }}>Un classeur Excel aux bonnes colonnes, avec un mode d'emploi
            et un exemple. Rempli, il se dépose tel quel.</p>
        </div>
        <button type="button" onClick={() => telecharger("/referentiel/canevas-personnel", "canevas-personnel.xlsx")}>
          Télécharger le canevas</button>
      </div>
      <Erreur erreur={erreurTelechargement} />

      {peutDeposer && (
        <form className="carte formulaire" onSubmit={deposer} style={{ maxWidth: 620 }}>
          <label>Fichier du personnel<input id="fichier" name="fichier" type="file" accept=".xlsx,.xlsm,.csv" required /></label>
          <div className="grille g2">
            <label>Données arrêtées au<input id="date_donnees" name="date_donnees" type="date" required /></label>
            <label>Les salaires sont
              <select id="periodicite" name="periodicite" defaultValue="">
                <option value="">dits par l'intitulé de colonne</option>
                <option value="mensuel">mensuels</option>
                <option value="annuel">annuels</option>
              </select>
            </label>
          </div>
          <div className="actions"><button className="principal">Déposer</button></div>
          <Erreur erreur={erreur} />
          {depose && (
            <p><span className="etat bien">Déposé</span> {depose.effectif} salariés lus.
              {depose.anomalies.length > 0 && ` ${depose.anomalies.length} point(s) à regarder ci-dessous.`}</p>
          )}
        </form>
      )}

      <div className="section">
        <h2>Fichiers déposés</h2>
        {d.fichiers.length === 0 && <p className="discret">Aucun fichier pour l'instant.</p>}
        <div className="defile">
          <table>
            <thead><tr><th>Fichier</th><th>Données au</th><th className="n">Salariés</th><th>État</th><th /></tr></thead>
            <tbody>
              {d.fichiers.map((f) => {
                const bloquants = f.anomalies.filter((a) => a.niveau === "bloquant").length;
                return [
                  <tr key={f.id} className="cliquable" onClick={() => setOuvert(ouvert === f.id ? null : f.id)}>
                    <td>{f.nom_fichier}<div className="discret">déposé le {dateFr(f.depose_le)}</div></td>
                    <td>{dateFr(f.date_donnees)}</td>
                    <td className="n">{f.effectif}</td>
                    <td>{bloquants ? <span className="etat grave">{bloquants} à corriger</span>
                      : f.anomalies.length ? <span className="etat attention">{f.anomalies.length} à regarder</span>
                      : <span className="etat bien">Complet</span>}</td>
                    <td className="n">
                      <button type="button" className="lien" aria-label={`Télécharger ${f.nom_fichier}`}
                              onClick={(e) => { e.stopPropagation();
                                telecharger(`/organisations/${d.org.id}/fichiers/${f.id}/telechargement`,
                                            `personnel-${f.date_donnees}.xlsx`); }}>Télécharger</button>
                    </td>
                  </tr>,
                  ouvert === f.id && (
                    <tr key={`${f.id}-a`}><td colSpan={5}>
                      <div className="volet-tete"><strong>Contrôles du fichier</strong>
                        <button type="button" className="fermer-volet" onClick={() => setOuvert(null)} aria-label="Fermer" title="Fermer">×</button></div>
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
