import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { dossier, etude, ORG, ouvrir, simulerApi } from "./outils";

const NON_CONNECTE = () => new Response(JSON.stringify({ code: "non_authentifie", message: "Connectez-vous." }),
  { status: 401, headers: { "content-type": "application/json" } });

describe("connexion", () => {
  it("par téléphone : le numéro, puis le code", async () => {
    const appels = simulerApi({
      "/auth/mode": { mode: "session" },
      "POST /auth/code": { message: "Si ce numéro est inscrit, un code vient d'être envoyé." },
      "POST /auth/verification": { utilisateur: { id: "u", nom_affiche: "Mme Test" } },
      "/moi": { id: "u", email: null, admin_plateforme: false, organisations: [] },
    });
    ouvrir("/connexion", null);
    await userEvent.type(await screen.findByLabelText("Téléphone"), "699123456");
    await userEvent.click(screen.getByRole("button", { name: "Recevoir un code" }));
    const code = await screen.findByLabelText("Code reçu");
    expect(code).toHaveValue("");            // le numéro ne reste pas dans la case du code
    await userEvent.type(code, "123456");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByText("Vos dossiers")).toBeInTheDocument();
    const verification = appels.find((a) => a.chemin === "/auth/verification")!;
    expect(JSON.parse(verification.init!.body as string)).toEqual({ telephone: "699123456", code: "123456" });
    expect(new Headers(verification.init!.headers).get("X-Courtage")).toBe("1");
    expect(screen.queryByText("Mode développement")).not.toBeInTheDocument();
  });

  it("en développement, on peut aussi choisir une personne", async () => {
    simulerApi({ "/auth/mode": { mode: "entete_dev" },
                 "/dev/utilisateurs": [{ id: "u-1", nom_affiche: "Awa Nkoulou", email: "a@x", admin_plateforme: false }],
                 "/moi": NON_CONNECTE });
    ouvrir("/connexion", null);
    await userEvent.click(await screen.findByText("Awa Nkoulou"));
    expect(localStorage.getItem("courtage:utilisateur")).toBe("u-1");
  });

  it("sans session, un dossier renvoie à la connexion", async () => {
    simulerApi({ "/auth/mode": { mode: "session" }, "/moi": NON_CONNECTE });
    ouvrir(`/dossier/${ORG}`, null);
    expect(await screen.findByRole("heading", { name: "Connexion" })).toBeInTheDocument();
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

    // Le volet des résultats se referme ; le formulaire reste.
    await userEvent.click(screen.getByRole("button", { name: "Fermer" }));
    expect(document.querySelectorAll("[data-offre]")).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Comparer" })).toBeInTheDocument();
  });
});

describe("les chiffres clés se réconcilient", () => {
  it("dette + charge − fonds = cotisation nette ; + frais = cotisation à verser", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/etudes/e1`]: etude({ possible: true, motifs: [] }) });
    ouvrir(`/dossier/${ORG}/etudes/e1`);
    const tableau = within((await screen.findByText("Du passif à la cotisation")).closest(".rapprochement") as HTMLElement);
    expect(tableau.getByText("2 991 437 F")).toBeInTheDocument();            // la nette
    expect(tableau.getByText(/Frais de gestion sur cotisation \(4 %\)/)).toBeInTheDocument();
    expect(tableau.getByText("119 658 F")).toBeInTheDocument();              // les frais
    expect(tableau.getAllByText("3 111 095 F")).toHaveLength(1);            // le total
    expect(screen.getByText("dont 119 658 F de frais (4 %)")).toBeInTheDocument();
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

describe("le contrat : courtage ou comparaison", () => {
  const vide = { service: "comparaison", en_vigueur: null, historique: [], constats: [] };

  it("sans contrat, l'entreprise lit qu'elle est en comparaison et traite avec son assureur", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/contrats`]: vide });
    ouvrir(`/dossier/${ORG}/contrat`);
    expect(await screen.findByRole("heading", { name: "Comparaison" })).toBeInTheDocument();
    expect(screen.getByText("par défaut : aucun contrat enregistré")).toBeInTheDocument();
    expect(screen.getByText(/Vous vous adressez directement à votre assureur/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enregistrer un contrat" })).not.toBeInTheDocument();
  });

  it("le conseiller enregistre un courtage : le mandat est exigé, et seulement là", async () => {
    const appels = simulerApi({ ...dossier("conseiller"), [`/organisations/${ORG}/contrats`]: {
      ...vide, constats: [{ niveau: "avertit", code: "commission_sans_mandat", message: "Commission sans mandat." }] } });
    ouvrir(`/dossier/${ORG}/contrat`);
    expect(await screen.findByText("Commission sans mandat.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer un contrat" }));
    expect(screen.getByLabelText("Référence du mandat")).toBeRequired();
    await userEvent.selectOptions(screen.getByLabelText("Service"), "comparaison");
    expect(screen.queryByLabelText("Référence du mandat")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Service"), "courtage");
    await userEvent.type(screen.getByLabelText("À partir du"), "2026-01-01");
    await userEvent.type(screen.getByLabelText("Assureur"), "Assureur A");
    await userEvent.type(screen.getByLabelText("Référence du mandat"), "Mandat du 15/12/2025");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(appels.some((a) => a.init?.method === "POST")).toBe(true));
    const corps = JSON.parse(appels.find((a) => a.init?.method === "POST")!.init!.body as string);
    expect(corps).toMatchObject({ service: "courtage", assureur: "Assureur A", mandat_reference: "Mandat du 15/12/2025",
                                  en_vigueur_du: "2026-01-01", numero_police: null });
  });

  it("en courtage, l'entreprise lit que nous portons ses prestations", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/contrats`]: { ...vide, service: "courtage",
      en_vigueur: { id: "c1", en_vigueur_du: "2026-01-01", service: "courtage", assureur: "Assureur A", numero_police: "IFC-42",
                    date_effet_police: null, mandat_reference: "Mandat du 15/12/2025", note: null } } });
    ouvrir(`/dossier/${ORG}/contrat`);
    expect(await screen.findByRole("heading", { name: "Courtage" })).toBeInTheDocument();
    expect(screen.getByText("depuis le 01/01/2026")).toBeInTheDocument();
    expect(screen.getByText(/nous montons le dossier de prise en charge/)).toBeInTheDocument();
    expect(screen.getByText("Assureur A")).toBeInTheDocument();
  });
});

describe("les départs", () => {
  const calcul = { anciennete: 20, mois: 7.25, plancher_applique: false,
                   source: { type: "convention" as const, convention_code: "CI_CCI", libelle: "la CCI de Côte d'Ivoire" } };
  const depart = { id: "p1", matricule: "A-017", categorie: null, motif: "retraite", date_naissance: null,
    date_embauche: "2000-01-01", date_depart: "2020-01-01", salaire_mensuel_reference: 500000, du: 3625000, calcul,
    verse: 3000000, part_fonds_demandee: null, part_fonds_payee: null, payee_le: null, soldee: false, origine: "saisie",
    import_id: null, note: null, remplace_id: null, motif_correction: null, service: "comparaison",
    constats: [{ niveau: "avertit", code: "verse_sous_le_du", message: "Versé 3 000 000 F, dû 3 625 000 F." }] };
  const liste = { prestations: [depart], totaux: { nombre: 1, retraites: 1, autres_departs: 0, du: 3625000, verse: 3000000, part_fonds_payee: 0 } };
  const contrat = { service: "comparaison", en_vigueur: null, historique: [], constats: [] };

  it("la liste dit le dû recalculé, et le détail l'explique", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/prestations`]: liste, [`/organisations/${ORG}/contrats`]: contrat });
    ouvrir(`/dossier/${ORG}/departs`);
    const ligne = await screen.findByText("A-017");
    expect(screen.getAllByText("3 625 000 F").length).toBeGreaterThan(0);
    expect(screen.getByText(/directement à votre assureur/)).toBeInTheDocument();
    await userEvent.click(ligne);
    expect(screen.getByText(/ans d'ancienneté ouvrent droit à/)).toHaveTextContent("7,25 × 500 000 F = 3 625 000 F");
    expect(screen.getByText("Versé 3 000 000 F, dû 3 625 000 F.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Fermer" }));
    expect(screen.queryByText(/ans d'ancienneté ouvrent droit à/)).not.toBeInTheDocument();
  });

  it("déclarer : le dû se calcule avant d'enregistrer, et rien ne nomme le salarié", async () => {
    const appels = simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/prestations`]: { prestations: [], totaux: liste.totaux },
      [`/organisations/${ORG}/contrats`]: contrat,
      [`POST /organisations/${ORG}/prestations/apercu`]: { du: 3625000, calcul, constats: [], service: "comparaison" },
      [`POST /organisations/${ORG}/prestations`]: depart });
    ouvrir(`/dossier/${ORG}/departs`);
    await userEvent.click(await screen.findByRole("button", { name: "Déclarer un départ" }));
    await userEvent.type(screen.getByLabelText("Matricule"), "A-017");
    await userEvent.type(screen.getByLabelText("Date d'embauche"), "2000-01-01");
    await userEvent.type(screen.getByLabelText("Date de départ"), "2020-01-01");
    await userEvent.type(screen.getByLabelText("Salaire mensuel de référence (F)"), "500000");
    await userEvent.click(screen.getByRole("button", { name: "Calculer le dû" }));
    await waitFor(() => expect(document.querySelector("[data-apercu]")).toHaveTextContent("7,25 × 500 000 F = 3 625 000 F"));
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer le départ" }));
    await waitFor(() => expect(appels.filter((a) => a.init?.method === "POST")).toHaveLength(2));
    const corps = JSON.parse(appels.filter((a) => a.init?.method === "POST")[1].init!.body as string);
    expect(corps).toMatchObject({ matricule: "A-017", motif: "retraite", salaire_mensuel_reference: 500000, verse: null });
    expect(Object.keys(corps).some((k) => /nom|prenom|telephone/.test(k))).toBe(false);
  });

  it("l'historique : un aperçu, et rien ne s'enregistre tant qu'il reste un point bloquant", async () => {
    simulerApi({ ...dossier("conseiller"), [`/organisations/${ORG}/prestations`]: { prestations: [], totaux: liste.totaux },
      [`/organisations/${ORG}/contrats`]: contrat,
      [`POST /organisations/${ORG}/prestations/import`]: { lignes: [{ numero: 3, matricule: "B-001", motif: "retraite",
        date_embauche: "2000-01-01", date_depart: "2020-01-01", salaire_mensuel_reference: 500000, du: 3625000, verse: null,
        part_fonds_payee: null, calcul, constats: [] }], colonnes: {}, colonnes_ignorees: ["Nom"], enregistrees: 0,
        anomalies: [{ niveau: "bloquant", code: "motif_inconnu", message: "Motif inconnu : « Mutation ».", ligne: 5 }] } });
    ouvrir(`/dossier/${ORG}/departs`);
    await userEvent.click(await screen.findByRole("button", { name: "Reprendre l'historique (tableur)" }));
    await userEvent.upload(screen.getByLabelText("Fichier (xlsx ou csv)"), new File(["x"], "departs.xlsx"));
    await userEvent.click(screen.getByRole("button", { name: "Lire le fichier" }));
    expect(await screen.findByText("B-001")).toBeInTheDocument();
    expect(screen.getByText("Colonnes ignorées : Nom.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enregistrer les 1 départs" })).toBeDisabled();
  });

  it("en lecture, on consulte sans déclarer", async () => {
    simulerApi({ ...dossier("lecteur_client"), [`/organisations/${ORG}/prestations`]: liste, [`/organisations/${ORG}/contrats`]: contrat });
    ouvrir(`/dossier/${ORG}/departs`);
    expect(await screen.findByText("A-017")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Déclarer un départ" })).not.toBeInTheDocument();
  });
});
