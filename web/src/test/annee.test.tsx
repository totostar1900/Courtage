import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { dossier, ORG, ouvrir, simulerApi } from "./outils";

describe("l'année du dossier", () => {
  it("le tableau de bord dit la prochaine évaluation et l'état de chaque étape", async () => {
    simulerApi({ ...dossier("admin_client"), "/alertes": [], [`/organisations/${ORG}/alertes`]: [],
      [`/organisations/${ORG}/calendrier`]: { derniere: "2025-12-31", prochaine: "2026-12-31", etapes: [
        { code: "personnel", libelle: "Mettre à jour le personnel", echeance: "2027-01-30", fait_le: "2026-12-31", etat: "fait", pour: "entreprise", lien: "personnel", cle: "p" },
        { code: "evaluation", libelle: "Émettre l'évaluation de l'année", echeance: "2027-03-01", fait_le: null, etat: "bientot", pour: "conseiller", lien: "etudes", cle: "e" }] } });
    ouvrir(`/dossier/${ORG}`);
    const zone = (await screen.findByRole("heading", { name: "L'année du dossier" })).closest("section")!;
    expect(within(zone).getByText(/la prochaine est au 31\/12\/2026/)).toBeInTheDocument();
    expect(within(zone).getByRole("link", { name: "Émettre l'évaluation de l'année" })).toHaveAttribute("href", `/dossier/${ORG}/etudes`);
    expect(within(zone).getByText("Bientôt")).toBeInTheDocument();
    expect(within(zone).getByText("Fait")).toBeInTheDocument();
  });

  it("sans étude émise, rien ne s'affiche", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/alertes`]: [],
      [`/organisations/${ORG}/calendrier`]: { derniere: null, prochaine: null, etapes: [] } });
    ouvrir(`/dossier/${ORG}`);
    await screen.findByRole("heading", { name: "Où en est votre dossier" });
    expect(screen.queryByRole("heading", { name: "L'année du dossier" })).toBeNull();
  });
});
