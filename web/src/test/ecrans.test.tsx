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

describe("la prise en charge", () => {
  const calcul = { anciennete: 20, mois: 7.25, plancher_applique: false,
                   source: { type: "convention" as const, convention_code: "CI_CCI", libelle: "la CCI" } };
  const depart = (service: string, dossier: unknown = null) => ({ id: "p1", matricule: "A-017", categorie: null, motif: "retraite",
    date_naissance: null, date_embauche: "2000-01-01", date_depart: "2020-01-01", salaire_mensuel_reference: 500000, du: 3625000,
    calcul, verse: 3625000, part_fonds_demandee: null, part_fonds_payee: null, payee_le: null, soldee: false, origine: "saisie",
    import_id: null, note: null, remplace_id: null, motif_correction: null, service, constats: [], dossier });
  const liste = (p: unknown) => ({ prestations: [p], totaux: { nombre: 1, retraites: 1, autres_departs: 0, du: 3625000, verse: 3625000, part_fonds_payee: 0 } });
  const contrat = { service: "courtage", en_vigueur: null, historique: [], constats: [] };
  const dossierPEC = (statut: string, extra: object = {}) => ({ id: "d1", matricule: "A-017", date_depart: "2020-01-01", prestation_id: "p1",
    montant_demande: 3625000, statut, numero: null, assureur: "Assureur A", numero_police: "IFC-7", mandat_reference: "Mandat",
    evenements: [{ etape: "declare", le: "2026-09-20", montant: null, motif: null, numero: null }],
    beneficiaire: { qualite: "salarie", nom: "KOUASSI", prenoms: "Aya", date_naissance: null, piece_type: "cni",
      piece_numero: "CI-1", telephone: null, moyen_paiement: "virement", coordonnees_paiement: "CI93" },
    pieces: [], identite_effacee: false, efface_le: null, constats: [], ...extra });

  it("en courtage, l'entreprise ouvre le dossier et l'identité part dans le dossier seulement", async () => {
    const appels = simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/prestations`]: liste(depart("courtage")),
      [`/organisations/${ORG}/contrats`]: contrat, [`POST /organisations/${ORG}/dossiers`]: dossierPEC("declare"),
      [`/organisations/${ORG}/dossiers/d1`]: dossierPEC("declare") });
    ouvrir(`/dossier/${ORG}/departs`);
    await userEvent.click(await screen.findByText("A-017"));
    await userEvent.click(screen.getByRole("button", { name: "Demander la prise en charge" }));
    expect(screen.getByLabelText("Montant demandé au fonds (F)")).toHaveValue(3625000);
    await userEvent.type(screen.getByLabelText("Nom"), "KOUASSI");
    await userEvent.type(screen.getByLabelText("Numéro de la pièce"), "CI-1");
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir le dossier" }));
    expect(await screen.findByRole("heading", { name: "Prise en charge · matricule A-017" })).toBeInTheDocument();
    const corps = JSON.parse(appels.find((a) => a.init?.method === "POST")!.init!.body as string);
    expect(corps).toMatchObject({ prestation_id: "p1", montant_demande: 3625000,
                                  beneficiaire: { nom: "KOUASSI", piece_numero: "CI-1", piece_type: "cni", qualite: "salarie" } });
  });

  it("en comparaison, pas de dossier : l'entreprise s'adresse à son assureur", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/prestations`]: liste(depart("comparaison")),
      [`/organisations/${ORG}/contrats`]: { ...contrat, service: "comparaison" } });
    ouvrir(`/dossier/${ORG}/departs`);
    await userEvent.click(await screen.findByText("A-017"));
    expect(screen.getByText(/Aucune identité n.est recueillie ici/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Demander la prise en charge" })).not.toBeInTheDocument();
  });

  it("le conseiller vérifie un dossier déclaré", async () => {
    const appels = simulerApi({ ...dossier("conseiller"), [`/organisations/${ORG}/dossiers/d1`]: dossierPEC("declare"),
      [`POST /organisations/${ORG}/dossiers/d1/verification`]: dossierPEC("verifie") });
    ouvrir(`/dossier/${ORG}/dossiers/d1`);
    expect(await screen.findByText("KOUASSI Aya")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Dossier complet" }));
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith("/verification"))).toBe(true));
  });

  it("transmis : le conseiller note la réponse de l'assureur ; un retard se voit", async () => {
    const appels = simulerApi({ ...dossier("conseiller"), [`/organisations/${ORG}/dossiers/d1`]: dossierPEC("transmis", {
      numero: "PC-AAAA-BBBB", constats: [{ niveau: "avertit", code: "retard_assureur", message: "Sans réponse depuis 45 jours." }] }),
      [`POST /organisations/${ORG}/dossiers/d1/reponse`]: dossierPEC("paye") });
    ouvrir(`/dossier/${ORG}/dossiers/d1`);
    expect(await screen.findByText("Sans réponse depuis 45 jours.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la réponse" }));
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith("/reponse"))).toBe(true));
    const corps = JSON.parse(appels.find((a) => a.chemin.endsWith("/reponse"))!.init!.body as string);
    expect(corps).toMatchObject({ paye: true, montant: 3625000 });
  });

  it("en lecture, ni identité ni pièces", async () => {
    simulerApi({ ...dossier("lecteur_client"), [`/organisations/${ORG}/dossiers/d1`]: dossierPEC("paye", {
      beneficiaire: null, efface_le: "2027-03-10" }) });
    ouvrir(`/dossier/${ORG}/dossiers/d1`);
    expect(await screen.findByText("Visible par l'entreprise et son conseiller seulement.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pièces" })).not.toBeInTheDocument();
    expect(screen.getByText(/seront effacées le 10\/03\/2027/)).toBeInTheDocument();
  });
});

describe("en comparaison, l'orientation vers l'assureur", () => {
  const calcul = { anciennete: 20, mois: 7.25, plancher_applique: false,
                   source: { type: "convention" as const, convention_code: "CI_CCI", libelle: "la CCI" } };
  const p = { id: "p1", matricule: "A-017", categorie: null, motif: "retraite", date_naissance: null, date_embauche: "2000-01-01",
    date_depart: "2020-01-01", salaire_mensuel_reference: 500000, du: 3625000, calcul, verse: 3625000, part_fonds_demandee: null,
    part_fonds_payee: null, payee_le: null, soldee: false, origine: "saisie", import_id: null, note: null, remplace_id: null,
    motif_correction: null, service: "comparaison", constats: [], dossier: null };
  const orientationB = { prestation_id: "p1", service: "comparaison", qui_s_en_occupe: "entreprise", assureur: "Assureur B",
    numero_police: "IFC-B-12", date_effet_police: null, du: 3625000, verse: 3625000, montant_a_demander: 3625000, calcul,
    delai_jours: 30, delai_exige: false, message: "Adressez la demande à Assureur B.",
    pieces: [{ nature: "courrier_demande", libelle: "La demande de l'entreprise", detail: "Un courrier signé." },
             { nature: "fiche_de_calcul", libelle: "La fiche de calcul de la plateforme", detail: "Scellée." }] };
  const base = () => ({ ...dossier("admin_client"),
    [`/organisations/${ORG}/prestations`]: { prestations: [p], totaux: { nombre: 1, retraites: 1, autres_departs: 0, du: 3625000, verse: 3625000, part_fonds_payee: 0 } },
    [`/organisations/${ORG}/contrats`]: { service: "comparaison", en_vigueur: null, historique: [], constats: [] },
    [`/organisations/${ORG}/prestations/p1/orientation`]: orientationB });

  it("dit à qui, combien, avec quelles pièces, puis reçoit le paiement déclaré", async () => {
    const appels = simulerApi({ ...base(), [`POST /organisations/${ORG}/prestations/p1/paiement`]: { ...p, part_fonds_payee: 3500000 } });
    ouvrir(`/dossier/${ORG}/departs`);
    await userEvent.click(await screen.findByText("A-017"));
    await userEvent.click(screen.getByRole("button", { name: "Préparer la demande à l'assureur" }));
    expect(await screen.findByText("Adressez la demande à Assureur B.")).toBeInTheDocument();
    expect(screen.getByText("Assureur B")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Télécharger la fiche scellée" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /La demande de l'entreprise/ }));
    expect(screen.getByText(/1\/2 prêtes/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Payé par l'assureur (F)"), "3500000");
    await userEvent.type(screen.getByLabelText("Payé le"), "2020-03-01");
    await userEvent.click(screen.getByRole("button", { name: "Déclarer le paiement" }));
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith("/paiement"))).toBe(true));
    const corps = JSON.parse(appels.find((a) => a.chemin.endsWith("/paiement"))!.init!.body as string);
    expect(corps).toEqual({ part_fonds_demandee: 3625000, part_fonds_payee: 3500000, payee_le: "2020-03-01" });
  });

  it("en lecture, l'orientation se lit sans déclarer ni télécharger", async () => {
    simulerApi({ ...base(), ...dossier("lecteur_client") , [`/organisations/${ORG}/prestations`]: base()[`/organisations/${ORG}/prestations`],
      [`/organisations/${ORG}/contrats`]: base()[`/organisations/${ORG}/contrats`], [`/organisations/${ORG}/prestations/p1/orientation`]: orientationB });
    ouvrir(`/dossier/${ORG}/departs`);
    await userEvent.click(await screen.findByText("A-017"));
    await userEvent.click(screen.getByRole("button", { name: "Préparer la demande à l'assureur" }));
    expect(await screen.findByText("Adressez la demande à Assureur B.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Déclarer le paiement" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Télécharger la fiche scellée" })).not.toBeInTheDocument();
  });
});

describe("l'expérience réelle", () => {
  const experience = {
    etude_precedente: { date_evaluation: "2018-12-31" },
    attendu_contre_reel: [{ annee: 2019, attendu_retraites: 2, attendu_prestations: 4000000, reel_retraites: 1, reel_du: 3625000, reel_verse: 3625000 }],
    rotation: { taux: 0.065, departs: 6, annees: 4, effectif: 23, taux_hypothese: 0.02, credible: true,
      proposition: { taux_turnover: 0.065, justification: "Rotation observée : 6 départs." }, message: "Rotation observée 6,5 % par an, contre 2,0 % supposés : à discuter." },
    paiements_du_fonds: { depuis: "2018-12-31", montant: 3000000 },
  };

  it("l'étude montre l'attendu contre le réel et propose la rotation sans l'appliquer", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/etudes/e1`]: { ...etude({ possible: true, motifs: [] }), experience } });
    ouvrir(`/dossier/${ORG}/etudes/e1`);
    const bloc = within(await screen.findByText("L'expérience réelle").then((h) => h.closest("[data-experience]") as HTMLElement));
    expect(bloc.getByText("2019")).toBeInTheDocument();
    expect(bloc.getByText("Hypothèse proposée : 6,5 %")).toBeInTheDocument();
    expect(bloc.getByText(/n'est pas appliquée à cette étude/)).toBeInTheDocument();
    expect(bloc.getByRole("link", { name: "Préparer une étude avec cette rotation" }).getAttribute("href")).toContain("turnover=0.065");
    expect(bloc.getByText(/Le fonds a payé 3 000 000 F/)).toBeInTheDocument();
  });

  it("la nouvelle étude reprend la rotation proposée, à confirmer et justifiée", async () => {
    const appels = simulerApi({ ...dossier("admin_client"), [`POST /organisations/${ORG}/etudes`]: { ...etude({ possible: true, motifs: [] }), id: "e2" },
      [`/organisations/${ORG}/etudes/e2`]: etude({ possible: true, motifs: [] }) });
    ouvrir(`/dossier/${ORG}/etudes?turnover=0.065&justification=${encodeURIComponent("Rotation observée : 6 départs.")}`);
    expect(await screen.findByLabelText("Rotation retenue (% par an)")).toHaveValue(6.5);
    await userEvent.click(screen.getByRole("button", { name: "Calculer" }));
    await waitFor(() => expect(appels.some((a) => a.init?.method === "POST")).toBe(true));
    const corps = JSON.parse(appels.find((a) => a.init?.method === "POST")!.init!.body as string);
    expect(corps.hypotheses).toEqual({ taux_turnover: 0.065 });
    expect(corps.justification).toBe("Rotation observée : 6 départs.");
  });

  it("sans proposition, le formulaire ne touche à aucune hypothèse", async () => {
    const appels = simulerApi({ ...dossier("admin_client"), [`POST /organisations/${ORG}/etudes`]: { ...etude({ possible: true, motifs: [] }), id: "e2" },
      [`/organisations/${ORG}/etudes/e2`]: etude({ possible: true, motifs: [] }) });
    ouvrir(`/dossier/${ORG}/etudes`);
    await userEvent.click(await screen.findByRole("button", { name: "Calculer" }));
    await waitFor(() => expect(appels.some((a) => a.init?.method === "POST")).toBe(true));
    expect(JSON.parse(appels.find((a) => a.init?.method === "POST")!.init!.body as string).hypotheses).toBeUndefined();
  });
});

describe("les réponses des assureurs", () => {
  const critere = (critere: string, libelle: string, sens: string, demande: number | boolean, offert: number | boolean | null, conforme: boolean | null) =>
    ({ critere, libelle, sens, demande, offert, conforme });
  const reponse = (id: string, assureur: string, rang: number, cout: number, conforme: boolean, extra: object = {}) => ({
    id, assureur, recue_le: "2026-09-20", taux_garanti: 0.03, participation_benefices: 0.9, frais_sur_cotisations: 0.02,
    frais_sur_encours: 0.004, delai_paiement_jours: 20, transfert_preavis_mois: 3, transfert_penalite: 0,
    accepte_etude_plateforme: true, reporting_annuel: true, historique_participation: null, commentaire: null,
    conformite: [critere("taux_garanti", "Taux garanti", "min", 0.025, 0.03, true),
                 critere("transfert_penalite", "Pénalité de transfert", "max", 0, conforme ? 0 : 0.05, conforme)],
    conforme, tardive: false, rang, cout_net_actualise: cout, offre: null, remplace_id: null, motif_correction: null, ...extra });
  const fiches = { [`/organisations/${ORG}/fiches`]: [{ id: "f1", numero: "RL-AAAA-BBBB", etude_id: "e1", date_limite_reponse: "2026-10-26", emise_le: "2026-09-26" }] };
  const reponses = (choix: unknown = null) => ({ fiche_id: "f1", date_limite_reponse: "2026-10-26", conditions: {},
    reponses: [reponse("r1", "Piège", 1, 50_000_000, false), reponse("r2", "Assureur A", 2, 60_000_000, true)],
    recommandee: "r2", comparaison: null, choix });

  it("classées, la recommandée est la moins chère des conformes ; un autre choix se motive", async () => {
    const appels = simulerApi({ ...dossier("admin_client", fiches), [`/organisations/${ORG}/fiches/f1/reponses`]: reponses(),
      [`POST /organisations/${ORG}/fiches/f1/choix`]: reponses({ reponse_id: "r1", assureur: "Piège", motif: "Service", choisi_le: "2026-09-26T10:00:00", recommandee: false }) });
    ouvrir(`/dossier/${ORG}/cahier/f1`);
    const piege = within(await screen.findByText("1. Piège").then((h) => h.closest("[data-reponse]") as HTMLElement));
    expect(piege.getByText("1 écart")).toBeInTheDocument();
    const a = within(document.querySelector('[data-reponse="Assureur A"]') as HTMLElement);
    expect(a.getByText("Recommandée")).toBeInTheDocument();
    expect(a.getByRole("button", { name: "Retenir Assureur A" })).toBeEnabled();
    expect(piege.getByRole("button", { name: "Retenir Piège" })).toBeDisabled();
    await userEvent.type(piege.getByLabelText("Pourquoi Piège"), "Service");
    await userEvent.click(piege.getByRole("button", { name: "Retenir Piège" }));
    await waitFor(() => expect(appels.some((x) => x.chemin.endsWith("/choix"))).toBe(true));
    expect(JSON.parse(appels.find((x) => x.chemin.endsWith("/choix"))!.init!.body as string)).toEqual({ reponse_id: "r1", motif: "Service" });
  });

  it("le conseiller saisit une réponse : la grille part en JSON, l'offre à côté", async () => {
    const appels = simulerApi({ ...dossier("conseiller", fiches), [`/organisations/${ORG}/fiches/f1/reponses`]: { ...reponses(), reponses: [] },
      [`POST /organisations/${ORG}/fiches/f1/reponses`]: reponse("r3", "Assureur C", 1, 1, true) });
    ouvrir(`/dossier/${ORG}/cahier/f1`);
    await userEvent.click(await screen.findByRole("button", { name: "Saisir une réponse" }));
    await userEvent.type(screen.getByLabelText("Assureur"), "Assureur C");
    await userEvent.type(screen.getByLabelText("Taux garanti (%)"), "2.8");
    await userEvent.type(screen.getByLabelText("Participation (%)"), "90");
    await userEvent.type(screen.getByLabelText("Frais sur cotisations (%)"), "2");
    await userEvent.type(screen.getByLabelText("Frais sur encours (%/an)"), "0.5");
    await userEvent.upload(screen.getByLabelText("L'offre de l'assureur (PDF, facultatif)"), new File(["%PDF"], "offre.pdf"));
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la réponse" }));
    await waitFor(() => expect(appels.some((x) => x.init?.method === "POST")).toBe(true));
    const corps = appels.find((x) => x.init?.method === "POST")!.init!.body as FormData;
    const donnees = JSON.parse(corps.get("donnees") as string);
    expect(donnees).toMatchObject({ assureur: "Assureur C", taux_garanti: 0.028, participation_benefices: 0.9,
                                    frais_sur_encours: 0.005, delai_paiement_jours: null, accepte_etude_plateforme: null });
    expect((corps.get("offre") as File).name).toBe("offre.pdf");
    expect(screen.queryByRole("button", { name: /Retenir/ })).not.toBeInTheDocument();
  });

  it("attribué : le choix se lit, et le conseiller enregistre le contrat", async () => {
    simulerApi({ ...dossier("conseiller", fiches), [`/organisations/${ORG}/fiches/f1/reponses`]: reponses({
      reponse_id: "r2", assureur: "Assureur A", motif: null, choisi_le: "2026-09-26T10:00:00", recommandee: true }) });
    ouvrir(`/dossier/${ORG}/cahier/f1`);
    expect(await screen.findByRole("heading", { name: "Attribué à Assureur A" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Enregistrer le contrat avec Assureur A" }).getAttribute("href")).toContain("contrat?assureur=Assureur%20A");
    expect(screen.queryByRole("button", { name: "Saisir une réponse" })).not.toBeInTheDocument();
  });
});

describe("partir d'un texte existant", () => {
  const cemac = { CM: "Cameroun", GA: "Gabon", CG: "Congo", TD: "Tchad", CF: "Centrafrique", GQ: "Guinée équatoriale" };
  const camerounais = (role: "admin_client" | "conseiller" = "admin_client") => ({ ...dossier(role),
    "/moi": { id: "u", email: null, admin_plateforme: false, organisations: [{ id: ORG, nom: "Démo CM", pays: "CM", role }] } });
  const proposition = { id: "x1", moteur: "claude", modele: "claude-opus-5", envoie_a_un_tiers: true, pays_couverts: cemac,
    version: { en_vigueur_du: "2024-02-01", fondement: "accord_entreprise", document_reference: "Accord IFC 2024",
      categories: [{ categorie: "*", convention_code: "CM_COMMERCE", bareme: { forme: "tranches_cumulatives", tranches: [
        { jusqu_a: 5, mois_par_annee: 0.45 }, { jusqu_a: null, mois_par_annee: 0.8 }] }, anciennete_minimale: 0,
        plafond_mois: null, arrondi: "annees", base_salaire: "moyenne_12_mois", avec_primes: false, evenements: ["retraite"] }] },
    verifications: [
      { champ: "* · barème", valeur: [{ jusqu_a: 5, mois_par_annee: 0.45 }, { jusqu_a: null, mois_par_annee: 0.8 }],
        citation: "45 % d'un mois de salaire pour chacune des 5 premières années", retrouvee: true },
      { champ: "date d'effet", valeur: "2024-02-01", citation: "en vigueur le 1er mars 2024", retrouvee: false }],
    constats: [{ niveau: "avertit", code: "citation_introuvable", message: "Un passage cité est introuvable." }] };

  it("l'accord avant l'envoi, chaque valeur avec son passage, puis le formulaire prérempli", async () => {
    const appels = simulerApi({ ...camerounais(), "/extraction/mode": { moteur: "claude", modele: "claude-opus-5", envoie_a_un_tiers: true, pays_couverts: cemac },
      [`POST /organisations/${ORG}/regimes/extraction`]: proposition });
    ouvrir(`/dossier/${ORG}/regime`);
    await userEvent.click(await screen.findByRole("button", { name: "Décrire un régime" }));
    await userEvent.upload(await screen.findByLabelText("Le texte (PDF ou texte brut)"), new File(["accord"], "accord.pdf"));
    const lire = screen.getByRole("button", { name: "Lire le texte" });
    expect(lire).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: /envoyé à Anthropic/ }));
    await userEvent.click(lire);
    expect(await screen.findByText("Un passage cité est introuvable.")).toBeInTheDocument();
    expect(screen.getByText("introuvable")).toBeInTheDocument();
    expect(screen.getByText("45 % jusqu'à 5 ans ; 80 % au-delà")).toBeInTheDocument();
    const corps = appels.find((a) => a.init?.method === "POST")!.init!.body as FormData;
    expect(corps.get("consentement")).toBe("true");
    await userEvent.click(screen.getByRole("button", { name: "Reprendre dans le formulaire" }));
    expect(screen.getByLabelText("En vigueur à partir du")).toHaveValue("2024-02-01");
    expect(screen.getByLabelText("Document")).toHaveValue("Accord IFC 2024");
    expect(screen.getByLabelText("Nom")).toHaveValue("Accord IFC 2024");
  });

  it("hors CEMAC, la lecture assistée n'est pas proposée", async () => {
    simulerApi({ ...dossier("admin_client"), "/extraction/mode": { moteur: "regles", modele: null, envoie_a_un_tiers: false, pays_couverts: cemac } });
    ouvrir(`/dossier/${ORG}/regime`);
    await userEvent.click(await screen.findByRole("button", { name: "Décrire un régime" }));
    expect(await screen.findByText(/réservée pour l'instant aux pays de la CEMAC/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Lire le texte" })).not.toBeInTheDocument();
  });

  it("le moteur à règles ne demande pas d'accord : rien ne part", async () => {
    simulerApi({ ...camerounais(), "/extraction/mode": { moteur: "regles", modele: null, envoie_a_un_tiers: false, pays_couverts: cemac } });
    ouvrir(`/dossier/${ORG}/regime`);
    await userEvent.click(await screen.findByRole("button", { name: "Décrire un régime" }));
    await userEvent.upload(await screen.findByLabelText("Le texte (PDF ou texte brut)"), new File(["x"], "accord.txt"));
    expect(screen.getByRole("button", { name: "Lire le texte" })).toBeEnabled();
    expect(screen.queryByRole("checkbox", { name: /Anthropic/ })).not.toBeInTheDocument();
    expect(screen.getByText(/sans envoi à un tiers/)).toBeInTheDocument();
  });
});

describe("une plateforme neuve", () => {
  it("l'administrateur ouvre un dossier client, qu'il suit", async () => {
    const appels = simulerApi({
      "/moi": { id: "u", email: null, admin_plateforme: true, organisations: [] },
      "POST /organisations": { id: ORG, nom: "Brasseries", pays: "GA", secteur: null },
    });
    ouvrir("/");
    await userEvent.click(await screen.findByRole("button", { name: "Ouvrir un dossier client" }));
    await userEvent.type(screen.getByLabelText("Entreprise"), "Brasseries");
    await userEvent.selectOptions(screen.getByLabelText("Pays"), "GA");
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir le dossier" }));
    await waitFor(() => expect(appels.some((a) => a.chemin === "/organisations")).toBe(true));
    const envoi = appels.find((a) => a.chemin === "/organisations")!;
    expect(JSON.parse(envoi.init!.body as string)).toEqual({ nom: "Brasseries", pays: "GA", secteur: null, suivre: true });
  });

  it("un client n'a pas ce bouton", async () => {
    simulerApi({ "/moi": { id: "u", email: null, admin_plateforme: false, organisations: [] } });
    ouvrir("/");
    expect(await screen.findByText("Aucun dossier pour l'instant.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ouvrir un dossier client" })).not.toBeInTheDocument();
  });

  it("le conseiller inscrit la DRH par son numéro", async () => {
    const appels = simulerApi({ ...dossier("conseiller"),
      [`POST /organisations/${ORG}/membres`]: { utilisateur_id: "d", telephone: "+237699001122", role: "admin_client" } });
    ouvrir(`/dossier/${ORG}/equipe`);
    expect(await screen.findByRole("heading", { name: "Équipe du dossier" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Nom"), "Mme DRH");
    await userEvent.type(screen.getByLabelText("Téléphone"), "699001122");
    await userEvent.click(screen.getByRole("button", { name: "Inscrire" }));
    await waitFor(() => expect(appels.some((a) => a.chemin === `/organisations/${ORG}/membres`)).toBe(true));
    const envoi = appels.find((a) => a.chemin === `/organisations/${ORG}/membres`)!;
    expect(JSON.parse(envoi.init!.body as string)).toEqual({ nom_affiche: "Mme DRH", telephone: "699001122", role: "admin_client" });
  });
});

describe("les modèles types", () => {
  const camerounais = () => ({ ...dossier("admin_client"),
    "/moi": { id: "u", email: null, admin_plateforme: false, organisations: [{ id: ORG, nom: "Démo CM", pays: "CM", role: "admin_client" }] } });
  const bareme = (taux: number) => ({ forme: "tranches_cumulatives", tranches: [{ jusqu_a: null, mois_par_annee: taux }] });
  const categorie = (nom: string, taux: number) => ({ categorie: nom, convention_code: "CM_COMMERCE", bareme: bareme(taux),
    anciennete_minimale: 0, plafond_mois: null, arrondi: "annees", base_salaire: "dernier", avec_primes: false, evenements: ["retraite"] });
  const modele = (code: string, titre: string, categories: ReturnType<typeof categorie>[]) => ({
    code: `CM_COMMERCE:${code}`, modele: code, titre, description: `${titre}, expliqué.`,
    convention: { code: "CM_COMMERCE", libelle: "Commerce (Cameroun)", statut: "valide" },
    version: { en_vigueur_du: null, fondement: "accord_entreprise", document_reference: `Modèle type de la plateforme : ${titre}`, categories },
    illustration: [10, 20, 30].map((n) => ({ anciennete: n, minimum: n * 0.5,
      par_categorie: Object.fromEntries(categories.map((c) => [c.categorie, n * c.bareme.tranches[0].mois_par_annee])) })) });
  const modeles = { pays: "CM", pays_libelle: "Cameroun", modeles: [
    modele("minimum", "Minimum conventionnel", [categorie("*", 0.5)]),
    modele("cadres", "Cadres favorisés", [categorie("Cadre", 0.75), categorie("*", 0.5)])] };

  it("se lit face à la convention, puis se reprend dans le formulaire", async () => {
    const appels = simulerApi({ ...camerounais(), "/extraction/mode": { moteur: "regles", modele: null, envoie_a_un_tiers: false, pays_couverts: { CM: "Cameroun" } },
      "/referentiel/modeles": modeles });
    ouvrir(`/dossier/${ORG}/regime`);
    await userEvent.click(await screen.findByRole("button", { name: "Décrire un régime" }));
    await userEvent.click(await screen.findByRole("button", { name: "Partir d'un modèle type" }));
    const cadres = (await screen.findByText("Cadres favorisés")).closest("[data-modele]") as HTMLElement;
    expect(within(cadres).getByRole("columnheader", { name: "Cadre" })).toBeInTheDocument();
    expect(within(cadres).getByRole("columnheader", { name: "Autres" })).toBeInTheDocument();
    const vingt = within(cadres).getByRole("row", { name: /^20 ans/ });
    expect(within(vingt).getAllByRole("cell").map((c) => c.textContent)).toEqual(["20 ans", "10 mois", "15 mois", "10 mois"]);
    expect(appels.some((a) => a.chemin === "/referentiel/modeles")).toBe(true);
    await userEvent.click(within(cadres).getByRole("button", { name: "Reprendre dans le formulaire" }));
    expect(screen.getByLabelText("Document")).toHaveValue("Modèle type de la plateforme : Cadres favorisés");
    expect(screen.queryByText("Minimum conventionnel")).not.toBeInTheDocument();   // la liste se referme
  });

  it("un pays sans convention préremplie le dit", async () => {
    simulerApi({ ...camerounais(), "/extraction/mode": { moteur: "regles", modele: null, envoie_a_un_tiers: false, pays_couverts: {} },
      "/referentiel/modeles": { pays: "GA", pays_libelle: "Gabon", modeles: [] } });
    ouvrir(`/dossier/${ORG}/regime`);
    await userEvent.click(await screen.findByRole("button", { name: "Décrire un régime" }));
    await userEvent.click(await screen.findByRole("button", { name: "Partir d'un modèle type" }));
    expect(await screen.findByText(/Pas encore de convention préremplie pour Gabon/)).toBeInTheDocument();
  });
});

describe("l'échéancier des départs", () => {
  const avec = () => ({ ...etude({ possible: false, motifs: [] }), echeancier: [
    { annee: 2021, effectif: 1, ifc: 3_000_000, prestations_probables: 2_900_000, vapf: 2_800_000 },
    { annee: 2023, effectif: 2, ifc: 8_000_000, prestations_probables: 7_100_000, vapf: 6_000_000 }] });

  it("chaque barre dit son année dans une bulle : départs, montants, part et cumul", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/etudes/e1`]: avec() });
    ouvrir(`/dossier/${ORG}/etudes/e1`);
    const barre = await screen.findByRole("button", { name: /^2023 : 2 départs/ });
    await userEvent.hover(barre);
    const bulle = screen.getByRole("tooltip");
    expect(within(bulle).getByText("2023")).toBeInTheDocument();
    expect(within(bulle).getByText("2 départs à la retraite")).toBeInTheDocument();
    expect(bulle).toHaveTextContent(/Prestations probables\s*7\s100\s000/);
    expect(bulle).toHaveTextContent(/Si tous partent\s*8\s000\s000/);
    expect(bulle).toHaveTextContent(/Valeur actuelle\s*6\s000\s000/);
    expect(bulle).toHaveTextContent(/Part du total\s*71/);          // 7,1 sur 10 M
    expect(bulle).toHaveTextContent(/Cumul depuis 2021\s*10\s000\s000/);
    await userEvent.unhover(barre);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("une année sans départ le dit, et la bulle s'ouvre aussi d'un toucher ou au clavier", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/etudes/e1`]: avec() });
    ouvrir(`/dossier/${ORG}/etudes/e1`);
    await userEvent.click(await screen.findByRole("button", { name: /^2022/ }));
    expect(screen.getByRole("tooltip")).toHaveTextContent("Aucun départ à la retraite prévu");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    await userEvent.tab({ shift: true });                              // de 2022 à 2021, au clavier
    expect(screen.getByRole("button", { name: /^2021/ })).toHaveFocus();
    expect(screen.getByRole("tooltip")).toHaveTextContent("1 départ à la retraite");
  });
});
