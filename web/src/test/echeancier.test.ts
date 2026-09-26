import { describe, expect, it } from "vitest";

import { categories, construire, epuisement, graduations } from "../echeancier";
import type { Annee } from "../types";

const part = (effectif: number, prob: number) => ({ effectif, ifc: prob * 1.2, prestations_probables: prob, vapf: prob * 0.8 });
const annees: Annee[] = [
  { annee: 2026, effectif: 2, ifc: 360, prestations_probables: 300, vapf: 240, par_categorie: { Cadre: part(1, 200), "*": part(1, 100) } },
  { annee: 2028, effectif: 1, ifc: 120, prestations_probables: 100, vapf: 80, par_categorie: { "*": part(1, 100) } },
];

describe("l'échéancier mis en forme", () => {
  it("une colonne par année, les années sans départ comprises", () => {
    const v = construire(annees, "prestations_probables", "annuelle", "ensemble", "tout");
    expect(v.colonnes.map((c) => [c.annee, c.total])).toEqual([[2026, 300], [2027, 0], [2028, 100]]);
    expect(v.series).toHaveLength(1);
  });

  it("par catégorie : la plus lourde d'abord, « * » dit « Autres salariés », les parts refont le total", () => {
    const v = construire(annees, "prestations_probables", "annuelle", "categorie", "tout");
    expect(v.series.map((s) => s.libelle)).toEqual(["Cadre", "Autres salariés"]);
    expect(v.colonnes[0].valeurs).toEqual({ Cadre: 200, "*": 100 });
    expect(v.colonnes[0].total).toBe(300);
  });

  it("cumulée, chaque série s'additionne d'année en année ; l'horizon coupe sans repeindre", () => {
    const v = construire(annees, "effectif", "cumulee", "categorie", "tout");
    expect(v.colonnes.map((c) => c.total)).toEqual([2, 2, 3]);
    const court = construire(annees, "effectif", "cumulee", "categorie", 10);
    expect(court.series).toEqual(v.series);
    expect(construire(annees, "vapf", "annuelle", "ensemble", 10).colonnes).toHaveLength(3);
  });

  it("sans découpage enregistré (étude ancienne), le graphique reste d'un seul tenant", () => {
    const anciennes = annees.map(({ par_categorie: _, ...a }) => a);
    const v = construire(anciennes, "ifc", "annuelle", "categorie", "tout");
    expect(v.decoupageDisponible).toBe(false);
    expect(v.series).toHaveLength(1);
  });

  it("au-delà de huit catégories, les dernières se rangent dans « Autres catégories »", () => {
    const beaucoup = { annee: 2026, effectif: 10, ifc: 0, vapf: 0, par_categorie: Object.fromEntries(
      Array.from({ length: 10 }, (_, i) => [`C${i}`, part(1, 100 - i)])) };
    const s = categories([beaucoup]);
    expect(s).toHaveLength(8);
    expect(s[7].libelle).toBe("Autres catégories");
    const v = construire([beaucoup], "effectif", "annuelle", "categorie", "tout");
    expect(v.colonnes[0].valeurs.__autres__).toBe(3);
  });

  it("des graduations rondes, et l'année où le fonds s'épuise", () => {
    expect(graduations(83_000_000)).toEqual([0, 50_000_000, 100_000_000]);
    const v = construire(annees, "prestations_probables", "cumulee", "ensemble", "tout");
    expect(epuisement(v.colonnes, 350)).toBe(2028);
    expect(epuisement(v.colonnes, 1000)).toBeNull();
  });
});

describe("les années sous l'axe", () => {
  it("toutes jusqu'à douze colonnes, puis les multiples de cinq et les bouts", async () => {
    const { reperesAnnees } = await import("../echeancier");
    expect([...reperesAnnees([2026, 2027, 2028])]).toEqual([2026, 2027, 2028]);
    const longues = Array.from({ length: 31 }, (_, i) => 2025 + i);   // 2025 → 2055
    expect([...reperesAnnees(longues)].sort()).toEqual([2025, 2030, 2035, 2040, 2045, 2050, 2055]);
    const decalees = Array.from({ length: 20 }, (_, i) => 2027 + i);  // 2027 → 2046 : 2046 colle à 2045, il se tait
    expect([...reperesAnnees(decalees)].sort()).toEqual([2027, 2030, 2035, 2040, 2045]);
  });
});
