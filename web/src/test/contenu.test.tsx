import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ouvrir, simulerApi } from "./outils";

const conventions = { version: "2026-09-26", pays_couverts: { CM: "Cameroun" }, conventions: [
  { pays: "CM", code: "CM_COMMERCE", libelle: "Convention collective nationale du commerce du Cameroun (révisée)", statut: "valide",
    en_vigueur_du: "2024-01-16", en_vigueur_au: null, en_vigueur_aujourd_hui: true, verification: "Taux concordants entre quatre sources secondaires.",
    sources: [{ titre: "Droit social en pratique", url: "https://exemple.cm/source" }],
    illustration: [{ anciennete: 5, mois: 1.25 }, { anciennete: 10, mois: 2.5 }] },
  { pays: "CM", code: "CM_BANQUES", libelle: "Convention des banques (révisée)", statut: "a_valider", en_vigueur_du: "2024-11-18",
    en_vigueur_au: null, en_vigueur_aujourd_hui: true, verification: null, sources: [], illustration: [{ anciennete: 5, mois: 1.25 }, { anciennete: 10, mois: 2.5 }] },
  { pays: "GA", code: "GA_X", libelle: "Gabon", statut: "valide", en_vigueur_du: "2020-01-01", en_vigueur_au: null,
    en_vigueur_aujourd_hui: true, verification: null, sources: [], illustration: [] }] };

describe("les pages de contenu", () => {
  it("/ifc explique, sans compte, et mène à l'essai", async () => {
    simulerApi({});
    ouvrir("/ifc", null);
    expect(await screen.findByRole("heading", { name: "Les indemnités de fin de carrière", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Comment la financer" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Essayer sans compte" })[0]).toHaveAttribute("href", "/essai");
    expect(document.title).toBe("Les indemnités de fin de carrière — Courtage");
  });

  it("/ifc/cameroun lit les barèmes du référentiel, sourcés, et seulement ceux du Cameroun", async () => {
    simulerApi({ "/referentiel/conventions": conventions });
    ouvrir("/ifc/cameroun", null);
    const tableau = await screen.findByRole("table");
    expect(within(tableau).getByText("Convention collective nationale du commerce du Cameroun (révisée)")).toBeInTheDocument();
    expect(within(tableau).getByText(/barème provisoire/)).toBeInTheDocument();
    expect(within(tableau).queryByText("Gabon")).toBeNull();
    expect(screen.getByRole("link", { name: "Droit social en pratique" })).toHaveAttribute("href", "https://exemple.cm/source");
    expect(screen.getByText(/la plateforme n'émet pas d'avis sur ce point/)).toBeInTheDocument();
    expect(screen.queryByText(/à valider/i)).toBeNull();
  });
});
