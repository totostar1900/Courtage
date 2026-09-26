import { describe, expect, it } from "vitest";

import donnees from "./donnees.json";
import { repondre } from "./serveur";

/** Le calcul TypeScript de la démonstration donne les chiffres du moteur Python, au franc près. */
describe("financement de la démonstration", () => {
  it("reproduit la sortie de l'API Python", async () => {
    const R = donnees.reponses as Record<string, any>;
    const reference = R["REFERENCE financement"];
    const chemin = Object.keys(R).find((k) => /^GET \/organisations\/[^/]+\/etudes\/[^/]+$/.test(k)
      && R[k].statut === "emise")!.slice(4);
    const ts = (await repondre("POST", `${chemin}/financement`, {
      horizon: 10, amortissement_annees: 3, offres: [
        { nom: "Assureur A", taux_garanti: 0.025, participation_benefices: 0.85, frais_sur_cotisations: 0.04 },
        { nom: "Assureur B", taux_garanti: 0.02, participation_benefices: 0.9, frais_sur_cotisations: 0.02, frais_sur_encours: 0.005 }],
    }, null)) as any;
    expect(ts.classement).toEqual(reference.classement);
    for (const [i, o] of reference.offres.entries()) {
      for (const [j, s] of o.scenarios.entries()) {
        const t = ts.offres[i].scenarios[j];
        for (const k of ["cout_net_actualise", "cout_total", "frais_totaux", "fonds_final"])
          expect(Math.abs(t[k] - s[k])).toBeLessThanOrEqual(1);
        expect(t.annees_decouvert).toEqual(s.annees_decouvert);
      }
    }
  });

  it("refuse d'écrire", async () => {
    await expect(repondre("POST", "/organisations/x/fichiers", null, null)).rejects.toMatchObject({ code: "demo_lecture_seule" });
  });
});
