import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ouvrir, simulerApi } from "./outils";

const COURTIER = { id: "adm", email: null, admin_plateforme: true, organisations: [] };
const ETAPES = ["inscrit", "confirme", "accompagnement_demande", "mandat_propose", "sous_mandat", "consultation", "offre_choisie", "en_vigueur"];
const LIB: Record<string, string> = { inscrit: "Inscrit, à confirmer", confirme: "Confirmé", accompagnement_demande: "Accompagnement demandé",
  mandat_propose: "Mandat proposé", sous_mandat: "Sous mandat", consultation: "En consultation", offre_choisie: "Offre choisie",
  en_vigueur: "Police en vigueur" };

const TABLEAU = {
  etapes: ETAPES.map((code) => ({ code, libelle: LIB[code], n: code === "confirme" || code === "en_vigueur" ? 1 : 0 })),
  dossiers: [
    { id: "o-a", nom: "Brasseries du Littoral", pays: "CM", etape: "en_vigueur", depuis: "2026-09-01", jours: 28, conseillers: ["M. Eto"],
      portefeuille: { polices: [{ assureur: "Assureur Vie", statut: "en_vigueur", numero: "P-1" }], primes_en_retard: 1,
        prochaine_etape: { libelle: "Relevé du personnel", echeance: "2026-11-30", etat: "a_venir" }, prises_en_charge_ouvertes: 2,
        alertes_graves: 0 } },
    { id: "o-b", nom: "Cimenterie Sud", pays: "CM", etape: "confirme", depuis: "2026-09-20", jours: 9, conseillers: [] },
  ],
};

describe("le pipeline et le portefeuille", () => {
  it("compte les dossiers par étape et montre ce qui attend un dossier sous mandat", async () => {
    simulerApi({ "/moi": COURTIER, "/portefeuille": TABLEAU });
    ouvrir("/portefeuille", "adm");
    const pipeline = await screen.findByRole("region", { name: "Le pipeline" });
    const vigueur = within(within(pipeline).getByRole("list")).getByText("Police en vigueur").closest("li")!;
    expect(within(vigueur).getByText("1")).toBeInTheDocument();
    expect(within(pipeline).getByRole("link", { name: "Cimenterie Sud" })).toHaveAttribute("href", "/dossier/o-b");

    const portefeuille = screen.getByRole("region", { name: "Le portefeuille" });
    expect(within(portefeuille).queryByText("Cimenterie Sud")).toBeNull();
    const ligne = within(portefeuille).getByRole("link", { name: "Brasseries du Littoral" }).closest("tr")!;
    expect(within(ligne).getByText("Relevé du personnel")).toBeInTheDocument();
    expect(within(ligne).getByText("1")).toHaveClass("etat", "grave");
  });
});
