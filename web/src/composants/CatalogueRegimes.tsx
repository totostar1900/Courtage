import { useState } from "react";

import { api } from "../api";
import { mois, pct } from "../format";
import { t } from "../i18n";
import { useDossier } from "../pages/Dossier";
import type { Catalogue, GroupeCatalogue, RegimeCatalogue, VersionProposee } from "../types";
import { Erreur, useCharge } from "./communs";
import { CONVENTION_PAR_PAYS } from "./EditeurCategories";
import { raisonActivation } from "../activation";

/** Partir du régime d'une autre entreprise, sans savoir laquelle : des groupes d'au moins cinq. */
export default function CatalogueRegimes({ onReprendre }: { onReprendre: (v: VersionProposee) => void }) {
  const d = useDossier();
  const [ouvert, setOuvert] = useState(false);
  const { donnee, erreur } = useCharge(
    () => (ouvert && !raisonActivation(d.activation, "catalogue") ? api.get<Catalogue>("/catalogue/regimes") : Promise.resolve(null)), [ouvert]);

  function reprendre(g: GroupeCatalogue, r: RegimeCatalogue) {
    // La convention reste si elle est visible et du même pays ; sinon, celle du pays de l'entreprise.
    const convention = r.convention_code && g.pays === d.org.pays ? r.convention_code : CONVENTION_PAR_PAYS[d.org.pays] ?? "";
    onReprendre({ en_vigueur_du: null, fondement: "accord_entreprise",
                  document_reference: t("Inspiré d'un régime du catalogue anonyme", "Based on a plan from the anonymous catalogue"),
                  categories: r.categories.map((c) => ({ ...c, convention_code: convention })) });
    setOuvert(false);
  }

  const attente = raisonActivation(d.activation, "catalogue");
  if (!ouvert || attente) {
    return (
      <div className="actions" style={{ marginTop: 0, marginBottom: 14 }}>
        <button type="button" onClick={() => setOuvert(true)} disabled={!!attente} title={attente ?? undefined}>
          {t("Partir du catalogue anonyme", "Start from the anonymous catalogue")}</button>
        <span className="discret">{attente ?? t("Les régimes que d'autres entreprises ont partagés, sans leur nom.",
          "Plans that other companies have shared, without their name.")}</span>
      </div>
    );
  }
  return (
    <div className="carte modeles" style={{ background: "var(--fond)", marginBottom: 14 }}>
      <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>{t("Partir du catalogue anonyme", "Start from the anonymous catalogue")}</h3>
        <button type="button" className="lien" onClick={() => setOuvert(false)}>{t("Fermer", "Close")}</button>
      </div>
      <p className="discret">{t("Des régimes adoptés par d'autres entreprises, qui ont accepté de les partager. Aucun nom, "
        + "aucun document, aucune date : un régime ne se montre que dans un groupe d'au moins cinq entreprises.",
        "Plans adopted by other companies that agreed to share them. No name, no document, no date: a plan is shown "
        + "only within a group of at least five companies.")}</p>
      <Erreur erreur={erreur} />
      {donnee && donnee.groupes.length === 0 && (
        <p>{t(`Le catalogue s'ouvre quand au moins ${donnee.seuil} entreprises ont partagé leur régime. `
          + `Aujourd'hui : ${donnee.entreprises}. Vous pouvez partager le vôtre depuis sa version adoptée.`,
          `The catalogue opens once at least ${donnee.seuil} companies have shared their plan. `
          + `Today: ${donnee.entreprises}. You can share yours from its adopted version.`)}</p>
      )}
      {donnee?.groupes.map((g) => (
        <div key={g.libelle} className="section" data-groupe={g.libelle}>
          <h4 style={{ marginBottom: 2 }}>{g.libelle}</h4>
          <div className="discret" style={{ marginBottom: 8 }}>{t(`${g.entreprises} entreprises`, `${g.entreprises} companies`)}</div>
          <div className="grille g2">
            {g.regimes.map((r, i) => {
              const categories = Object.keys(r.illustration[0].par_categorie);
              return (
                <div key={r.id} className="carte" data-regime={r.id}>
                  <h4 style={{ marginBottom: 2 }}>{t(`Régime ${i + 1}`, `Plan ${i + 1}`)}</h4>
                  {r.ecart_convention_20_ans !== null && (
                    <div className="discret" style={{ marginBottom: 6 }}>
                      {r.ecart_convention_20_ans >= 0.005 ? t(`${pct(r.ecart_convention_20_ans, 0)} au-dessus de sa convention`,
                          `${pct(r.ecart_convention_20_ans, 0)} above its collective agreement`)
                        : r.ecart_convention_20_ans <= -0.005 ? t(`${pct(-r.ecart_convention_20_ans, 0)} sous sa convention`,
                          `${pct(-r.ecart_convention_20_ans, 0)} below its collective agreement`)
                        : t("au niveau de sa convention", "level with its collective agreement")}{t(" à 20 ans", " at 20 years")}</div>
                  )}
                  <table>
                    <thead><tr><th>{t("Ancienneté", "Length of service")}</th>
                      {categories.map((c) => <th key={c} className="n">{c === "*" ? (categories.length > 1 ? t("Autres", "Others") : t("Indemnité", "Benefit")) : c}</th>)}</tr></thead>
                    <tbody>{r.illustration.map((l) => (
                      <tr key={l.anciennete}><td>{t(`${l.anciennete} ans`, `${l.anciennete} years`)}</td>
                        {categories.map((c) => <td key={c} className="n">{mois(l.par_categorie[c])}</td>)}</tr>
                    ))}</tbody>
                  </table>
                  <div className="actions">
                    <button type="button" className="principal" onClick={() => reprendre(g, r)}>{t("Reprendre dans le formulaire", "Use in the form")}</button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
