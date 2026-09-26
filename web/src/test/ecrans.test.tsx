import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { dossier, etude, ORG, ouvrir, simulerApi } from "./outils";

describe("connexion de développement", () => {
  it("liste les personnes et retient celle choisie", async () => {
    simulerApi({ "/dev/utilisateurs": [{ id: "u-1", nom_affiche: "Awa Nkoulou", email: "a@x", admin_plateforme: false }],
                 "/moi": { organisations: [] } });
    ouvrir("/connexion", null);
    await userEvent.click(await screen.findByText("Awa Nkoulou"));
    expect(localStorage.getItem("courtage:utilisateur")).toBe("u-1");
  });

  it("sans personne choisie, on arrive à la connexion", async () => {
    simulerApi({ "/dev/utilisateurs": [] });
    ouvrir(`/dossier/${ORG}`, null);
    expect(await screen.findByText("Bienvenue")).toBeInTheDocument();
  });
});

describe("le dossier", () => {
  it("montre la prochaine étape et le conseiller", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/etudes/e1`]: etude({ possible: false, motifs: [] }) });
    ouvrir(`/dossier/${ORG}`);
    expect(await screen.findByText("Prochaine étape")).toBeInTheDocument();
    // personnel fait ; le régime vient ensuite (ou la convention seule, qui le rendra fait à l'émission)
    expect(screen.getByRole("heading", { name: "Régime" })).toBeInTheDocument();
    expect(screen.getByText("Awa Nkoulou")).toBeInTheDocument();
  });
});

describe("l'émission d'une étude", () => {
  it("le conseiller voit pourquoi il ne peut pas encore émettre", async () => {
    simulerApi({ ...dossier("conseiller"),
                 [`/organisations/${ORG}/etudes/e1`]: etude({ possible: false, motifs: ["pays_different", "remuneration_absente"] }) });
    ouvrir(`/dossier/${ORG}/etudes/e1`);
    const bouton = await screen.findByRole("button", { name: /Émettre et sceller/ });
    expect(bouton).toBeDisabled();
    expect(screen.getByText(/convention d'un autre pays · conditions de rémunération à fixer/)).toBeInTheDocument();
  });

  it("le client ne peut pas émettre : c'est son conseiller qui le fait", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/etudes/e1`]: etude({ possible: true, motifs: [] }) });
    ouvrir(`/dossier/${ORG}/etudes/e1`);
    expect(await screen.findByText(/Votre conseiller relit puis émet/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Émettre et sceller/ })).not.toBeInTheDocument();
  });

  it("une étude émise ouvre son rapport", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/etudes/e1`]: etude({ possible: false, motifs: [] }, "emise") });
    ouvrir(`/dossier/${ORG}/etudes/e1`);
    expect(await screen.findByRole("button", { name: "Ouvrir le rapport PDF" })).toBeInTheDocument();
  });
});

describe("l'adoption d'un régime", () => {
  const version = (constats: unknown[]) => ({
    id: "v1", regime_id: "r1", nom: "Accord", numero: 1, en_vigueur_du: "2015-03-12", fondement: "accord_entreprise",
    document_reference: "Accord 2015", statut: "analyse", non_conformite_acceptee: false,
    categories: [{ categorie: "*", convention_code: "CI_CCI", bareme: { forme: "tranches_cumulatives", tranches: [{ jusqu_a: null, mois_par_annee: 0.1 }] } }],
    constats,
  });

  it("un régime sous la convention s'adopte seulement en en prenant acte", async () => {
    simulerApi({ ...dossier("admin_client", { [`/organisations/${ORG}/regimes`]: [{ id: "r1", nom: "Accord", versions: [version([
      { niveau: "bloque", code: "sous_le_plancher", message: "Sous la CCI de 1 à 50 ans." }])] }] }) });
    ouvrir(`/dossier/${ORG}/regime`);
    const adopter = await screen.findByRole("button", { name: "Adopter cette version" });
    expect(adopter).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: /donne moins que la convention/ }));
    expect(adopter).toBeEnabled();
  });

  it("le conseiller n'adopte pas", async () => {
    simulerApi({ ...dossier("conseiller", { [`/organisations/${ORG}/regimes`]: [{ id: "r1", nom: "Accord", versions: [version([])] }] }) });
    ouvrir(`/dossier/${ORG}/regime`);
    expect(await screen.findByText("L'adoption appartient à l'entreprise.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Adopter cette version" })).not.toBeInTheDocument();
  });
});

describe("la comparaison des offres", () => {
  it("la moins chère d'abord, marquée", async () => {
    const scen = (cout: number) => [{ scenario: "central", rendement: 0.05, cout_total: 1, cout_net_actualise: cout,
      frais_totaux: 0, fonds_final: 0, annees_decouvert: [], couverture_des_departs_restants: null, annees: [] }];
    const cond = { nom: "", taux_garanti: 0.025, participation_benefices: 0.9, frais_sur_cotisations: 0.04, frais_sur_encours: 0 };
    simulerApi({ ...dossier("admin_client"), [`POST /organisations/${ORG}/etudes/e1/financement`]: {
      plan_amortissement: { deficit_initial: 0, annees: 1, annuite: 0 }, scenario_de_reference: "central",
      classement: ["Sobre", "Chère", "Provision interne"],
      offres: [{ nom: "Chère", interne: false, conditions: cond, scenarios: scen(9_000_000) },
               { nom: "Provision interne", interne: true, conditions: cond, scenarios: scen(20_000_000) },
               { nom: "Sobre", interne: false, conditions: cond, scenarios: scen(5_000_000) }] } });
    ouvrir(`/dossier/${ORG}/etudes/e1/financement`);
    await userEvent.click(await screen.findByRole("button", { name: "Comparer" }));
    await waitFor(() => expect(document.querySelectorAll("[data-offre]")).toHaveLength(3));
    const cartes = [...document.querySelectorAll("[data-offre]")].map((c) => c.getAttribute("data-offre"));
    expect(cartes).toEqual(["Sobre", "Chère", "Provision interne"]);
    expect(within(document.querySelector('[data-offre="Sobre"]') as HTMLElement).getByText("Le moins cher")).toBeInTheDocument();
  });
});

describe("la vérification publique", () => {
  const verif = (authentique: boolean) => ({ numero: "RL-AAAA-BBBB", nature: "etude_ifc", emis_le: "2026-09-26T10:00:00",
    authentique, probant: true, resume: { organisation: "AZITO", date_evaluation: "2019-12-31", dette: 60130415 } });

  it("sans compte, dit si le document est authentique", async () => {
    simulerApi({ "/verifier/RL-AAAA-BBBB": verif(true) });
    ouvrir("/verifier/RL-AAAA-BBBB", null);
    expect(await screen.findByText("Authentique")).toBeInTheDocument();
    expect(screen.getByText("60 130 415 F")).toBeInTheDocument();
  });

  it("dit quand un document a été modifié", async () => {
    simulerApi({ "/verifier/RL-AAAA-BBBB": verif(false) });
    ouvrir("/verifier/RL-AAAA-BBBB", null);
    expect(await screen.findByText(/Non authentique/)).toBeInTheDocument();
  });
});
