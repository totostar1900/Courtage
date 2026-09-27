import { describe, expect, it } from "vitest";

import { bilan, categorieParlante, categories, confondues, couleur, courbe, NEUTRE, nomsCourts, type Variante } from "../comparatif";

const variante = (nom: string, ifc: Record<string, number>, courbes: Record<string, number[]>, dette = 100): Variante => ({
  nom, totaux: { effectif: 3, vapf: dette, dette, charge: 10, cotisation_nette: 0, cotisation_totale: 0 },
  cotisation_initiale: 0, ecart_convention: 0, courbes, ifc_par_salarie: ifc,
  categorie_par_salarie: { M1: "Cadre", M2: "Employé", M3: "Employé" },
});
const conv = variante("Convention seule", { M1: 1000, M2: 500, M3: 400 }, { "*": [0, 1, 2] });
const v1 = variante("Accord IFC Démo, version 1", { M1: 1500, M2: 500, M3: 400.5 }, { Cadre: [0, 2, 4], "*": [0, 1, 2] });
const v2 = variante("Accord IFC Démo, version 2", { M1: 900, M2: 700, M3: 400 }, { "*": [0, 1.5, 3] });

describe("le comparatif des régimes", () => {
  it("compte qui gagne et qui perd, salarié par salarié ; un franc d'écart est un arrondi", () => {
    const b = bilan(conv, v1);
    expect([b.gagnent, b.inchanges, b.perdent]).toEqual([1, 2, 0]);
    expect(b.plusGrosGain).toEqual({ matricule: "M1", montant: 500 });
    const c = bilan(conv, v2);
    expect([c.gagnent, c.inchanges, c.perdent]).toEqual([1, 1, 1]);
    expect(c.perteMoyenne).toBe(-100);
    expect(c.ecartTotal).toBe(100);
    expect(bilan(conv, v2, "Employé").gagnent).toBe(1);
    expect(bilan(conv, v2, "Cadre").perdent).toBe(1);
  });

  it("lit la règle de la catégorie, sinon celle des autres", () => {
    expect(courbe(v1, "Cadre")).toEqual([0, 2, 4]);
    expect(courbe(v1, "Employé")).toEqual([0, 1, 2]);
    expect(categories(conv)).toEqual(["Employé", "Cadre"]);
  });

  it("ouvre la courbe sur la catégorie où les régimes diffèrent, et dit quand ils se confondent", () => {
    expect(categorieParlante([conv, v1])).toBe("Cadre");
    expect(confondues([conv, v1], "Employé")).toEqual(["Accord IFC Démo, version 1"]);
    expect(confondues([conv, v1], "Cadre")).toEqual([]);
  });

  it("raccourcit les noms sans les rendre identiques ; la référence reste neutre", () => {
    expect(nomsCourts([conv.nom, v1.nom, v2.nom])).toEqual(["Convention seule", "version 1", "version 2"]);
    expect(nomsCourts([conv.nom, v1.nom])).toEqual([conv.nom, v1.nom]);
    expect(nomsCourts(["Convention seule", "Idée A", "Idée B"])).toEqual(["Convention seule", "Idée A", "Idée B"]);
    expect(couleur(0)).toBe(NEUTRE);
    expect(couleur(1)).not.toBe(couleur(2));
  });
});
