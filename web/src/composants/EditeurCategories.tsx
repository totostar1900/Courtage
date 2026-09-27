import { t } from "../i18n";
import type { Categorie } from "../types";

export const CONVENTION_PAR_PAYS: Record<string, string> = { CI: "CI_CCI", CM: "CM_COMMERCE" };
const evenements = () => [
  ["depart_anticipe", t("départ anticipé", "early departure")],
  ["licenciement_economique", t("licenciement économique", "redundancy")],
  ["deces", t("décès en activité", "death in service")],
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
    const tranches = (categories[i].bareme.tranches ?? []).map((tr, l) => (l === k ? { ...tr, ...champ } : tr));
    maj(i, { bareme: { ...categories[i].bareme, tranches } });
  };

  return (
    <div className="grille">
      {categories.map((c, i) => (
        <div key={i} className="carte" style={{ background: "var(--fond)" }}>
          <div className="grille g3">
            <label>{t("Catégorie", "Category")}
              <input value={c.categorie} onChange={(e) => maj(i, { categorie: e.target.value })}
                     placeholder={t("* pour tout le personnel", "* for all staff")} aria-label={t(`Nom de la catégorie ${i + 1}`, `Name of category ${i + 1}`)} />
            </label>
            <label>{t("Convention plancher", "Floor agreement")}
              <input value={c.convention_code} onChange={(e) => maj(i, { convention_code: e.target.value })} />
            </label>
            <label>{t("Base de salaire", "Salary basis")}
              <select value={c.base_salaire} onChange={(e) => maj(i, { base_salaire: e.target.value as Categorie["base_salaire"] })}>
                <option value="dernier">{t("dernier salaire", "last salary")}</option>
                <option value="moyenne_12_mois">{t("moyenne des 12 derniers mois", "average of the last 12 months")}</option>
              </select>
            </label>
          </div>
          <h3 style={{ marginTop: 12 }}>{t("Barème : mois de salaire par année d'ancienneté", "Scale: months of salary per year of service")}</h3>
          {(c.bareme.tranches ?? []).map((tr, k) => (
            <div key={k} className="actions" style={{ marginTop: 4 }}>
              <span className="discret" style={{ width: 90 }}>
                {tr.jusqu_a === null ? t("au-delà", "beyond") : t(`jusqu'à`, "up to")}
              </span>
              {tr.jusqu_a !== null && (
                <input type="number" min={1} style={{ width: 80 }} value={tr.jusqu_a}
                       onChange={(e) => majTranche(i, k, { jusqu_a: Number(e.target.value) })} aria-label={t("ans", "years")} />
              )}
              {tr.jusqu_a !== null && <span className="discret">{t("ans", "years")}</span>}
              <input type="number" step={1} min={0} max={300} style={{ width: 90 }}
                     value={Math.round(tr.mois_par_annee * 1000) / 10}
                     onChange={(e) => majTranche(i, k, { mois_par_annee: Number(e.target.value) / 100 })}
                     aria-label={t(`taux de la tranche ${k + 1}`, `rate for band ${k + 1}`)} />
              <span className="discret">{t("% d'un mois", "% of a month")}</span>
            </div>
          ))}
          <div className="grille g3" style={{ marginTop: 12 }}>
            <label>{t("Ancienneté minimale (ans)", "Minimum length of service (years)")}
              <input type="number" min={0} value={c.anciennete_minimale ?? 0}
                     onChange={(e) => maj(i, { anciennete_minimale: Number(e.target.value) })} />
            </label>
            <label>{t("Plafond (mois de salaire)", "Cap (months of salary)")}
              <input type="number" min={0} value={c.plafond_mois ?? ""} placeholder={t("aucun", "none")}
                     onChange={(e) => maj(i, { plafond_mois: e.target.value ? Number(e.target.value) : null })} />
            </label>
            <label>{t("Primes dans la base", "Bonuses in the basis")}
              <select value={c.avec_primes ? "oui" : "non"} onChange={(e) => maj(i, { avec_primes: e.target.value === "oui" })}>
                <option value="non">{t("non", "no")}</option><option value="oui">{t("oui", "yes")}</option>
              </select>
            </label>
          </div>
          <div className="actions">
            <span className="discret">{t("Couvre aussi :", "Also covers:")}</span>
            {evenements().map(([cle, libelle]) => (
              <label key={cle} style={{ display: "flex", gap: 6, fontWeight: 400 }}>
                <input type="checkbox" checked={c.evenements?.includes(cle) ?? false}
                       onChange={(e) => maj(i, { evenements: e.target.checked
                         ? [...(c.evenements ?? ["retraite"]), cle]
                         : (c.evenements ?? []).filter((x) => x !== cle) })} />
                {libelle}
              </label>
            ))}
            {categories.length > 1 && (
              <button type="button" onClick={() => onChange(categories.filter((_, j) => j !== i))}>{t("Retirer", "Remove")}</button>
            )}
          </div>
        </div>
      ))}
      <div>
        <button type="button" onClick={() => onChange([...categories, categorieVide(pays, "")])}>
          {t("Ajouter une catégorie", "Add a category")}
        </button>
      </div>
    </div>
  );
}

export function resumeBareme(c: Categorie): string {
  if (c.bareme.forme !== "tranches_cumulatives") return t("paliers", "steps");
  let debut = 1;
  return (c.bareme.tranches ?? []).map((tr) => {
    const taux = `${Math.round(tr.mois_par_annee * 1000) / 10} %`;
    const txt = tr.jusqu_a === null ? t(`${taux} au-delà de ${debut - 1} ans`, `${taux} beyond ${debut - 1} years`)
      : t(`${taux} de ${debut} à ${tr.jusqu_a} ans`, `${taux} from ${debut} to ${tr.jusqu_a} years`);
    if (tr.jusqu_a !== null) debut = tr.jusqu_a + 1;
    return txt;
  }).join(" · ");
}
