import { useState } from "react";

import { api } from "../api";
import { mois } from "../format";
import { useDossier } from "../pages/Dossier";
import type { ModelesDuPays, VersionProposee } from "../types";
import { Erreur, useCharge } from "./communs";

const EXEMPLES = [10, 20, 30];

/** Partir d'un modèle type : un barème calculé depuis la convention, jamais en dessous d'elle. */
export default function ModelesTypes({ onReprendre }: { onReprendre: (v: VersionProposee) => void }) {
  const d = useDossier();
  const [ouvert, setOuvert] = useState(false);
  const { donnee, erreur } = useCharge(
    () => (ouvert ? api.get<ModelesDuPays>(`/referentiel/modeles?pays=${d.org.pays}`) : Promise.resolve(null)), [ouvert]);
  if (!ouvert) {
    return (
      <div className="actions" style={{ marginTop: 0, marginBottom: 14 }}>
        <button type="button" onClick={() => setOuvert(true)}>Partir d'un modèle type</button>
        <span className="discret">Quatre barèmes calculés depuis votre convention, à reprendre et ajuster.</span>
      </div>
    );
  }
  return (
    <div className="carte modeles" style={{ background: "var(--fond)", marginBottom: 14 }}>
      <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>Partir d'un modèle type</h3>
        <button type="button" className="lien" onClick={() => setOuvert(false)}>Fermer</button>
      </div>
      <p className="discret">Chaque modèle est calculé depuis le barème de la convention et ne passe jamais en dessous.
        Il ne vient d'aucune entreprise. Vous le reprenez, l'ajustez, l'enregistrez : l'analyse habituelle suit.</p>
      <Erreur erreur={erreur} />
      {donnee && donnee.modeles.length === 0 && (
        <p>Pas encore de convention préremplie pour {donnee.pays_libelle}, donc pas de modèle type.</p>
      )}
      <div className="grille g2">
        {donnee?.modeles.map((m) => {
          const categories = Object.keys(m.illustration[0].par_categorie);
          const lignes = m.illustration.filter((r) => EXEMPLES.includes(r.anciennete));
          return (
            <div key={m.code} className="carte" data-modele={m.code}>
              <h4 style={{ marginBottom: 2 }}>{m.titre}</h4>
              <div className="discret" style={{ marginBottom: 6 }}>{m.convention.libelle}
                {m.convention.statut === "a_valider" && " · barème à valider"}</div>
              <p style={{ marginTop: 0 }}>{m.description}</p>
              <table>
                <thead><tr><th>Ancienneté</th><th className="n">Convention</th>
                  {categories.map((c) => <th key={c} className="n">{c === "*" ? (categories.length > 1 ? "Autres" : "Modèle") : c}</th>)}</tr></thead>
                <tbody>{lignes.map((r) => (
                  <tr key={r.anciennete}><td>{r.anciennete} ans</td><td className="n">{mois(r.minimum)}</td>
                    {categories.map((c) => <td key={c} className="n">{mois(r.par_categorie[c])}</td>)}</tr>
                ))}</tbody>
              </table>
              <div className="actions">
                <button type="button" className="principal" onClick={() => { onReprendre(m.version); setOuvert(false); }}>
                  Reprendre dans le formulaire</button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
