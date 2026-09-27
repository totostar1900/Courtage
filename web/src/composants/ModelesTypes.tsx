import { useState } from "react";

import { api } from "../api";
import { mois } from "../format";
import { t } from "../i18n";
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
        <button type="button" onClick={() => setOuvert(true)}>{t("Partir d'un modèle type", "Start from a model")}</button>
        <span className="discret">{t("Quatre barèmes calculés depuis votre convention, à reprendre et ajuster.",
          "Four scales calculated from your collective agreement, to reuse and adjust.")}</span>
      </div>
    );
  }
  return (
    <div className="carte modeles" style={{ background: "var(--fond)", marginBottom: 14 }}>
      <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>{t("Partir d'un modèle type", "Start from a model")}</h3>
        <button type="button" className="lien" onClick={() => setOuvert(false)}>{t("Fermer", "Close")}</button>
      </div>
      <p className="discret">{t("Chaque modèle est calculé depuis le barème de la convention et ne passe jamais en dessous. "
        + "Il ne vient d'aucune entreprise. Vous le reprenez, l'ajustez, l'enregistrez : l'analyse habituelle suit.",
        "Each model is calculated from the collective agreement's scale and never falls below it. It comes from no "
        + "company. You reuse it, adjust it, save it: the usual review follows.")}</p>
      <Erreur erreur={erreur} />
      {donnee && donnee.modeles.length === 0 && (
        <p>{t(`Pas encore de convention préremplie pour ${donnee.pays_libelle}, donc pas de modèle type.`,
          `No prefilled collective agreement for ${donnee.pays_libelle} yet, so no model.`)}</p>
      )}
      <div className="grille g2">
        {donnee?.modeles.map((m) => {
          const categories = Object.keys(m.illustration[0].par_categorie);
          const lignes = m.illustration.filter((r) => EXEMPLES.includes(r.anciennete));
          return (
            <div key={m.code} className="carte" data-modele={m.code}>
              <h4 style={{ marginBottom: 2 }}>{m.titre}</h4>
              <div className="discret" style={{ marginBottom: 6 }}>{m.convention.libelle}
                {m.convention.statut === "a_valider" && t(" · barème à valider", " · scale to be validated")}</div>
              <p style={{ marginTop: 0 }}>{m.description}</p>
              <table>
                <thead><tr><th>{t("Ancienneté", "Length of service")}</th><th className="n">{t("Convention", "Agreement")}</th>
                  {categories.map((c) => <th key={c} className="n">{c === "*" ? (categories.length > 1 ? t("Autres", "Others") : t("Modèle", "Model")) : c}</th>)}</tr></thead>
                <tbody>{lignes.map((r) => (
                  <tr key={r.anciennete}><td>{t(`${r.anciennete} ans`, `${r.anciennete} years`)}</td><td className="n">{mois(r.minimum)}</td>
                    {categories.map((c) => <td key={c} className="n">{mois(r.par_categorie[c])}</td>)}</tr>
                ))}</tbody>
              </table>
              <div className="actions">
                <button type="button" className="principal" onClick={() => { onReprendre(m.version); setOuvert(false); }}>
                  {t("Reprendre dans le formulaire", "Use in the form")}</button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
