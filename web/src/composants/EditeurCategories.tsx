import type { Categorie } from "../types";

export const CONVENTION_PAR_PAYS: Record<string, string> = { CI: "CI_CCI", CM: "CM_COMMERCE" };
const EVENEMENTS = [
  ["depart_anticipe", "départ anticipé"],
  ["licenciement_economique", "licenciement économique"],
  ["deces", "décès en activité"],
] as const;

export function categorieVide(pays: string, nom = "*"): Categorie {
  return {
    categorie: nom, convention_code: CONVENTION_PAR_PAYS[pays] ?? "",
    bareme: { forme: "tranches_cumulatives", tranches: [
      { jusqu_a: 5, mois_par_annee: 0.3 }, { jusqu_a: 10, mois_par_annee: 0.35 }, { jusqu_a: null, mois_par_annee: 0.4 }] },
    anciennete_minimale: 0, plafond_mois: null, arrondi: "annees", base_salaire: "dernier", avec_primes: false,
    evenements: ["retraite"],
  };
}

/** Des catégories de personnel, chacune avec son barème par tranches et ses conditions. */
export function EditeurCategories({ categories, onChange, pays }: {
  categories: Categorie[]; onChange: (c: Categorie[]) => void; pays: string;
}) {
  const maj = (i: number, champ: Partial<Categorie>) =>
    onChange(categories.map((c, j) => (j === i ? { ...c, ...champ } : c)));
  const majTranche = (i: number, k: number, champ: { jusqu_a?: number | null; mois_par_annee?: number }) => {
    const tranches = (categories[i].bareme.tranches ?? []).map((t, l) => (l === k ? { ...t, ...champ } : t));
    maj(i, { bareme: { ...categories[i].bareme, tranches } });
  };

  return (
    <div className="grille">
      {categories.map((c, i) => (
        <div key={i} className="carte" style={{ background: "var(--fond)" }}>
          <div className="grille g3">
            <label>Catégorie
              <input value={c.categorie} onChange={(e) => maj(i, { categorie: e.target.value })}
                     placeholder="* pour tout le personnel" aria-label={`Nom de la catégorie ${i + 1}`} />
            </label>
            <label>Convention plancher
              <input value={c.convention_code} onChange={(e) => maj(i, { convention_code: e.target.value })} />
            </label>
            <label>Base de salaire
              <select value={c.base_salaire} onChange={(e) => maj(i, { base_salaire: e.target.value as Categorie["base_salaire"] })}>
                <option value="dernier">dernier salaire</option>
                <option value="moyenne_12_mois">moyenne des 12 derniers mois</option>
              </select>
            </label>
          </div>
          <h3 style={{ marginTop: 12 }}>Barème : mois de salaire par année d'ancienneté</h3>
          {(c.bareme.tranches ?? []).map((t, k) => (
            <div key={k} className="actions" style={{ marginTop: 4 }}>
              <span className="discret" style={{ width: 90 }}>
                {t.jusqu_a === null ? "au-delà" : `jusqu'à`}
              </span>
              {t.jusqu_a !== null && (
                <input type="number" min={1} style={{ width: 80 }} value={t.jusqu_a}
                       onChange={(e) => majTranche(i, k, { jusqu_a: Number(e.target.value) })} aria-label="ans" />
              )}
              {t.jusqu_a !== null && <span className="discret">ans</span>}
              <input type="number" step={1} min={0} max={300} style={{ width: 90 }}
                     value={Math.round(t.mois_par_annee * 1000) / 10}
                     onChange={(e) => majTranche(i, k, { mois_par_annee: Number(e.target.value) / 100 })}
                     aria-label={`taux de la tranche ${k + 1}`} />
              <span className="discret">% d'un mois</span>
            </div>
          ))}
          <div className="grille g3" style={{ marginTop: 12 }}>
            <label>Ancienneté minimale (ans)
              <input type="number" min={0} value={c.anciennete_minimale ?? 0}
                     onChange={(e) => maj(i, { anciennete_minimale: Number(e.target.value) })} />
            </label>
            <label>Plafond (mois de salaire)
              <input type="number" min={0} value={c.plafond_mois ?? ""} placeholder="aucun"
                     onChange={(e) => maj(i, { plafond_mois: e.target.value ? Number(e.target.value) : null })} />
            </label>
            <label>Primes dans la base
              <select value={c.avec_primes ? "oui" : "non"} onChange={(e) => maj(i, { avec_primes: e.target.value === "oui" })}>
                <option value="non">non</option><option value="oui">oui</option>
              </select>
            </label>
          </div>
          <div className="actions">
            <span className="discret">Couvre aussi :</span>
            {EVENEMENTS.map(([cle, libelle]) => (
              <label key={cle} style={{ display: "flex", gap: 6, fontWeight: 400 }}>
                <input type="checkbox" checked={c.evenements?.includes(cle) ?? false}
                       onChange={(e) => maj(i, { evenements: e.target.checked
                         ? [...(c.evenements ?? ["retraite"]), cle]
                         : (c.evenements ?? []).filter((x) => x !== cle) })} />
                {libelle}
              </label>
            ))}
            {categories.length > 1 && (
              <button type="button" onClick={() => onChange(categories.filter((_, j) => j !== i))}>Retirer</button>
            )}
          </div>
        </div>
      ))}
      <div>
        <button type="button" onClick={() => onChange([...categories, categorieVide(pays, "")])}>
          Ajouter une catégorie
        </button>
      </div>
    </div>
  );
}

export function resumeBareme(c: Categorie): string {
  if (c.bareme.forme !== "tranches_cumulatives") return "paliers";
  let debut = 1;
  return (c.bareme.tranches ?? []).map((t) => {
    const taux = `${Math.round(t.mois_par_annee * 1000) / 10} %`;
    const txt = t.jusqu_a === null ? `${taux} au-delà de ${debut - 1} ans` : `${taux} de ${debut} à ${t.jusqu_a} ans`;
    if (t.jusqu_a !== null) debut = t.jusqu_a + 1;
    return txt;
  }).join(" · ");
}
