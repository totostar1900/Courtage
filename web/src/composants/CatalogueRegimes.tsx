import { useState } from "react";

import { api } from "../api";
import { mois, pct } from "../format";
import { useDossier } from "../pages/Dossier";
import type { Catalogue, GroupeCatalogue, RegimeCatalogue, VersionProposee } from "../types";
import { Erreur, useCharge } from "./communs";
import { CONVENTION_PAR_PAYS } from "./EditeurCategories";

/** Partir du régime d'une autre entreprise, sans savoir laquelle : des groupes d'au moins cinq. */
export default function CatalogueRegimes({ onReprendre }: { onReprendre: (v: VersionProposee) => void }) {
  const d = useDossier();
  const [ouvert, setOuvert] = useState(false);
  const { donnee, erreur } = useCharge(
    () => (ouvert ? api.get<Catalogue>("/catalogue/regimes") : Promise.resolve(null)), [ouvert]);

  function reprendre(g: GroupeCatalogue, r: RegimeCatalogue) {
    // La convention reste si elle est visible et du même pays ; sinon, celle du pays de l'entreprise.
    const convention = r.convention_code && g.pays === d.org.pays ? r.convention_code : CONVENTION_PAR_PAYS[d.org.pays] ?? "";
    onReprendre({ en_vigueur_du: null, fondement: "accord_entreprise",
                  document_reference: "Inspiré d'un régime du catalogue anonyme",
                  categories: r.categories.map((c) => ({ ...c, convention_code: convention })) });
    setOuvert(false);
  }

  if (!ouvert) {
    return (
      <div className="actions" style={{ marginTop: 0, marginBottom: 14 }}>
        <button type="button" onClick={() => setOuvert(true)}>Partir du catalogue anonyme</button>
        <span className="discret">Les régimes que d'autres entreprises ont partagés, sans leur nom.</span>
      </div>
    );
  }
  return (
    <div className="carte modeles" style={{ background: "var(--fond)", marginBottom: 14 }}>
      <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>Partir du catalogue anonyme</h3>
        <button type="button" className="lien" onClick={() => setOuvert(false)}>Fermer</button>
      </div>
      <p className="discret">Des régimes adoptés par d'autres entreprises, qui ont accepté de les partager. Aucun nom,
        aucun document, aucune date : un régime ne se montre que dans un groupe d'au moins cinq entreprises.</p>
      <Erreur erreur={erreur} />
      {donnee && donnee.groupes.length === 0 && (
        <p>Le catalogue s'ouvre quand au moins {donnee.seuil} entreprises ont partagé leur régime.
          Aujourd'hui : {donnee.entreprises}. Vous pouvez partager le vôtre depuis sa version adoptée.</p>
      )}
      {donnee?.groupes.map((g) => (
        <div key={g.libelle} className="section" data-groupe={g.libelle}>
          <h4 style={{ marginBottom: 2 }}>{g.libelle}</h4>
          <div className="discret" style={{ marginBottom: 8 }}>{g.entreprises} entreprises</div>
          <div className="grille g2">
            {g.regimes.map((r, i) => {
              const categories = Object.keys(r.illustration[0].par_categorie);
              return (
                <div key={r.id} className="carte" data-regime={r.id}>
                  <h4 style={{ marginBottom: 2 }}>Régime {i + 1}</h4>
                  {r.ecart_convention_20_ans !== null && (
                    <div className="discret" style={{ marginBottom: 6 }}>
                      {r.ecart_convention_20_ans >= 0.005 ? `${pct(r.ecart_convention_20_ans, 0)} au-dessus de sa convention`
                        : r.ecart_convention_20_ans <= -0.005 ? `${pct(-r.ecart_convention_20_ans, 0)} sous sa convention`
                        : "au niveau de sa convention"} à 20 ans</div>
                  )}
                  <table>
                    <thead><tr><th>Ancienneté</th>
                      {categories.map((c) => <th key={c} className="n">{c === "*" ? (categories.length > 1 ? "Autres" : "Indemnité") : c}</th>)}</tr></thead>
                    <tbody>{r.illustration.map((l) => (
                      <tr key={l.anciennete}><td>{l.anciennete} ans</td>
                        {categories.map((c) => <td key={c} className="n">{mois(l.par_categorie[c])}</td>)}</tr>
                    ))}</tbody>
                  </table>
                  <div className="actions">
                    <button type="button" className="principal" onClick={() => reprendre(g, r)}>Reprendre dans le formulaire</button>
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
