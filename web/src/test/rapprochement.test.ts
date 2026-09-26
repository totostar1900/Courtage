import { rapprocher } from "../rapprochement";

const somme = (l: ReturnType<typeof rapprocher>) => l.filter((x) => !x.total).reduce((s, x) => s + x.montant, 0);

describe("du passif à la cotisation", () => {
  it("retrouve la cotisation à verser au franc près, frais compris", () => {
    // Les chiffres du tableau de bord : 110,7 + 10,3 − 45,0 ≠ 79,1 tant que les frais ne sont pas montrés.
    const t = { effectif: 40, vapf: 0, dette: 110_739_135, charge: 10_312_480, cotisation_nette: 76_051_615,
                cotisation_totale: 79_093_680 };
    const l = rapprocher(t, 45_000_000, 0.04);
    expect(l.map((x) => x.libelle)).toEqual(["Dette actuarielle", "Charge annuelle", "Fonds constitué",
      "Cotisation nette", "Frais de gestion sur cotisation (4 %)", "Cotisation à verser"]);
    expect(somme(l)).toBe(79_093_680);
    expect(l.find((x) => x.libelle.startsWith("Frais"))!.montant).toBe(3_042_065);
  });

  it("montre l'arrondi quand il existe", () => {
    const t = { effectif: 1, vapf: 0, dette: 100, charge: 50, cotisation_nette: 51, cotisation_totale: 51 };
    const l = rapprocher(t, 100, 0);
    expect(l.find((x) => x.libelle === "Arrondi")!.montant).toBe(1);
    expect(somme(l)).toBe(51);
  });

  it("un fonds qui couvre tout : l'excédent est nommé, la cotisation est nulle", () => {
    const t = { effectif: 1, vapf: 0, dette: 100, charge: 50, cotisation_nette: 0, cotisation_totale: 0 };
    const l = rapprocher(t, 200, 0.04);
    expect(l.find((x) => x.libelle.startsWith("Excédent"))!.montant).toBe(50);
    expect(somme(l)).toBe(0);
  });
});
