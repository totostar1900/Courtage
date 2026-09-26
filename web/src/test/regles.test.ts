import { describe, expect, it, vi } from "vitest";

import { api, ErreurApi } from "../api";
import { dateFr, millions, montant, pct } from "../format";
import { etapes } from "../parcours";

describe("formats", () => {
  it("écrit les francs entiers, les taux et les dates à la française", () => {
    expect(montant(60130415.4)).toBe("60 130 415 F");
    expect(montant(null)).toBe("—");
    expect(millions(60130415)).toBe("60,1 M F");
    expect(pct(0.035)).toBe("3,5 %");
    expect(dateFr("2019-12-31")).toBe("31/12/2019");
  });
});

describe("erreurs de l'API", () => {
  it("rend le code et les motifs d'une erreur métier", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ code: "emission_refusee", message: "Refusée.", details: { motifs: ["pays_different"] } }),
      { status: 409, headers: { "content-type": "application/json" } })));
    const e = (await api.post("/x").catch((x) => x)) as ErreurApi;
    expect(e).toBeInstanceOf(ErreurApi);
    expect([e.statut, e.code, e.details.motifs]).toEqual([409, "emission_refusee", ["pays_different"]]);
  });

  it("traduit une erreur de validation en message lisible", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ detail: [{ msg: "Input should be greater than or equal to 1" }] }),
      { status: 422, headers: { "content-type": "application/json" } })));
    const e = (await api.post("/x").catch((x) => x)) as ErreurApi;
    expect(e.code).toBe("requete_invalide");
    expect(e.message).toContain("greater than");
  });
});

describe("parcours", () => {
  const vide = { fichiers: 0, versions: 0, versionsAdoptees: 0, etudesEmises: 0, etudesBrouillon: 0, fiches: 0 };

  it("commence par le personnel", () => {
    const e = etapes(vide);
    expect(e.find((x) => x.suivant)?.cle).toBe("personnel");
  });

  it("le régime est facultatif : une étude émise sur la convention le rend fait", () => {
    const e = etapes({ ...vide, fichiers: 1, etudesEmises: 1 });
    expect(e.find((x) => x.cle === "regime")?.fait).toBe(true);
    expect(e.find((x) => x.suivant)?.cle).toBe("financement");
  });

  it("tout est fait quand le cahier des charges est parti", () => {
    expect(etapes({ ...vide, fichiers: 1, etudesEmises: 1, fiches: 1 }).some((x) => x.suivant)).toBe(false);
  });
});
