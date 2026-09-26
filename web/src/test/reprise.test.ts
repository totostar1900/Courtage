import { beforeEach, describe, expect, it } from "vitest";

import { ilYa, lireReprise, noterReprise } from "../reprise";

describe("reprendre où l'on s'était arrêté", () => {
  beforeEach(() => localStorage.clear());

  it("chaque personne a sa propre reprise", () => {
    noterReprise("u1", { org: "o1", chemin: "/dossier/o1/etudes/e1", pages: ["Études", "Étude au 31/12/2025"], quand: 1 });
    expect(lireReprise("u1")?.chemin).toBe("/dossier/o1/etudes/e1");
    expect(lireReprise("u2")).toBeNull();
  });

  it("une valeur abîmée ou étrangère au dossier est ignorée", () => {
    localStorage.setItem("courtage:reprise:u1", "{pas du json");
    expect(lireReprise("u1")).toBeNull();
    localStorage.setItem("courtage:reprise:u1", JSON.stringify({ org: "o1", chemin: "https://ailleurs.example", pages: [], quand: 1 }));
    expect(lireReprise("u1")).toBeNull();
  });

  it("le temps écoulé se dit simplement", () => {
    const t = new Date(2026, 8, 26, 12, 0).getTime();
    expect(ilYa(t, t + 20_000)).toBe("à l'instant");
    expect(ilYa(t, t + 12 * 60_000)).toBe("il y a 12 min");
    expect(ilYa(t, t + 3 * 3_600_000)).toBe("il y a 3 h");
    expect(ilYa(t, t + 30 * 3_600_000)).toBe("hier");
    expect(ilYa(t, t + 4 * 86_400_000)).toBe("il y a 4 jours");
    expect(ilYa(t, t + 20 * 86_400_000)).toBe("le 26/09/2026");
  });
});
