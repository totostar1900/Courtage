import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { oublierCabinet } from "../cabinet";

import { dossier, etude, ORG, ouvrir, simulerApi } from "./outils";

const json = (corps: unknown, status: number) =>
  new Response(JSON.stringify(corps), { status, headers: { "content-type": "application/json" } });

const EN_ATTENTE = {
  etat: "en_attente",
  capacites: { rapport_scelle: false, export_etude: false, notes_regime: false, fiche_de_calcul: false, equipe: false,
               catalogue: false, extraction_claude: false, mandat: false, cahier: false },
  libelles: {}, rccm: "RC/DLA/2020/B/1234", taille: "50_a_250", adresse: null, ville: "Douala",
  demandee_le: "2026-09-28T09:00:00+00:00", decidee_le: null, motif: null,
  echeance: "2026-09-30", expire_le: "2026-10-28",
};

const enAttente = (extra: Record<string, unknown> = {}) =>
  ({ ...dossier("admin_client"), [`/organisations/${ORG}/activation`]: EN_ATTENTE,
     [`/organisations/${ORG}/justificatifs`]: [], ...extra });

const CABINET = { "/public/cabinet": { nom: "Cabinet", agrement: "A1", adresse: "Douala", rccm: "R", courriel: "c@x.cm",
  telephone: "1", hebergeur: "Render", conditions_version: "conditions-2026-09", manquants: [] } };

describe("inscription", () => {
  beforeEach(() => oublierCabinet());

  it("les deux codes, la personne, l'entreprise, puis le dossier", async () => {
    let essais = 0;
    const appels = simulerApi({
      ...enAttente(), ...CABINET,
      "POST /inscription/code": { message: "Un code vient d'être envoyé. Il expire dans 10 minutes." },
      "POST /inscription/verification": (init?: RequestInit) => {
        const corps = JSON.parse(init!.body as string);
        if (corps.nature === "telephone" && essais++ === 0)
          return json({ code: "code_invalide", message: "Code incorrect ou expiré. Demandez-en un nouveau.", details: {} }, 401);
        return { preuve: `preuve-${corps.nature}` };
      },
      "POST /inscription": () => json({ organisation_id: ORG, utilisateur: { id: "u", nom_affiche: "Mme DRH" },
                                        activation: EN_ATTENTE }, 201),
    });
    ouvrir("/inscription", null);

    // Le téléphone : un mauvais code d'abord, puis le bon.
    const tel = document.querySelector<HTMLElement>('[data-canal="telephone"]')!;
    await userEvent.type(within(tel).getByLabelText("Téléphone"), "699123456");
    await userEvent.click(within(tel).getByRole("button", { name: "Recevoir un code" }));
    await userEvent.type(await within(tel).findByLabelText("Code reçu par message"), "000000");
    await userEvent.click(within(tel).getByRole("button", { name: "Vérifier" }));
    expect(await within(tel).findByText("Code incorrect ou expiré. Demandez-en un nouveau.")).toBeInTheDocument();
    const code = within(tel).getByLabelText("Code reçu par message");
    await userEvent.clear(code);
    await userEvent.type(code, "123456");
    await userEvent.click(within(tel).getByRole("button", { name: "Vérifier" }));
    await waitFor(() => expect(document.querySelector('p[data-canal="telephone"]')).toHaveTextContent("✓ Téléphone : +237699123456 vérifié"));

    const suite = screen.getByRole("button", { name: "Continuer" });
    expect(suite).toBeDisabled();            // le courriel n'est pas encore vérifié

    const courriel = document.querySelector<HTMLElement>('[data-canal="courriel"]')!;
    await userEvent.type(within(courriel).getByLabelText("Courriel"), "drh@azito.cm");
    await userEvent.click(within(courriel).getByRole("button", { name: "Recevoir un code" }));
    await userEvent.type(await within(courriel).findByLabelText("Code reçu par courriel"), "654321");
    await userEvent.click(within(courriel).getByRole("button", { name: "Vérifier" }));
    await waitFor(() => expect(document.querySelector('p[data-canal="courriel"]')).toHaveTextContent("✓ Courriel : drh@azito.cm vérifié"));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));

    await userEvent.type(screen.getByLabelText("Nom et prénom"), "Mme DRH");
    await userEvent.type(screen.getByLabelText("Fonction"), "DRH");
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));

    expect(screen.getByText(/Le document RCCM pourra être envoyé après l'inscription/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Raison sociale"), "AZITO");
    await userEvent.selectOptions(screen.getByLabelText("Pays"), "GA");
    await userEvent.type(screen.getByLabelText("Numéro RCCM"), "RC/LBV/2020/B/99");
    await userEvent.selectOptions(screen.getByLabelText("Taille"), "moins_de_50");
    await userEvent.type(screen.getByLabelText("Ville"), "Libreville");
    // Les conditions s'acceptent avant de créer le compte.
    expect(screen.getByRole("button", { name: "Créer mon compte" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "conditions d'utilisation" })).toHaveAttribute("href", "/conditions");
    await userEvent.click(screen.getByRole("checkbox", { name: /J'ai lu et j'accepte/ }));
    await userEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));

    expect(await screen.findByText(/Inscription en attente de confirmation/)).toBeInTheDocument();
    const envoi = appels.find((a) => a.chemin === "/inscription" && a.init?.method === "POST")!;
    expect(JSON.parse(envoi.init!.body as string)).toEqual({
      telephone: "+237699123456", preuve_telephone: "preuve-telephone", courriel: "drh@azito.cm", preuve_courriel: "preuve-courriel",
      nom: "Mme DRH", fonction: "DRH",
      entreprise: { nom: "AZITO", pays: "GA", rccm: "RC/LBV/2020/B/99", taille: "moins_de_50", secteur: null, adresse: null,
                    ville: "Libreville" },
      conditions: "conditions-2026-09",
    });
  });

  it("une entreprise déjà inscrite : l'erreur du serveur s'affiche", async () => {
    simulerApi({
      ...CABINET,
      "POST /inscription/code": { message: "Un code vient d'être envoyé." },
      "POST /inscription/verification": { preuve: "p" },
      "POST /inscription": () => json({ code: "entreprise_deja_inscrite",
        message: "Cette entreprise est déjà inscrite : adressez-vous à son administrateur.", details: {} }, 409),
    });
    ouvrir("/inscription", null);
    for (const [canal, libelle, code, cible] of [["telephone", "Téléphone", "Code reçu par message", "699123456"],
                                                  ["courriel", "Courriel", "Code reçu par courriel", "a@b.cm"]]) {
      const zone = document.querySelector<HTMLElement>(`[data-canal="${canal}"]`)!;
      await userEvent.type(within(zone).getByLabelText(libelle), cible);
      await userEvent.click(within(zone).getByRole("button", { name: "Recevoir un code" }));
      await userEvent.type(await within(zone).findByLabelText(code), "123456");
      await userEvent.click(within(zone).getByRole("button", { name: "Vérifier" }));
      await waitFor(() => expect(document.querySelector(`p[data-canal="${canal}"]`)).toHaveTextContent("✓"));
    }
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
    await userEvent.type(screen.getByLabelText("Nom et prénom"), "Mme DRH");
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
    await userEvent.type(screen.getByLabelText("Raison sociale"), "AZITO");
    await userEvent.type(screen.getByLabelText("Numéro RCCM"), "RC 1234");
    await userEvent.click(screen.getByRole("checkbox", { name: /J'ai lu et j'accepte/ }));
    await userEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Cette entreprise est déjà inscrite");
  });

  it("l'essai en cours est annoncé", async () => {
    simulerApi({});
    sessionStorage.setItem("courtage:essai", "{}");
    ouvrir("/inscription", null);
    expect(await screen.findByText("Votre essai sera repris dans votre dossier.")).toBeInTheDocument();
    sessionStorage.removeItem("courtage:essai");
  });

  it("la connexion mène à l'inscription et à l'essai", async () => {
    simulerApi({ "/auth/mode": { mode: "session" } });
    ouvrir("/connexion", null);
    expect(await screen.findByRole("link", { name: "Créer votre compte" })).toHaveAttribute("href", "/inscription");
    expect(screen.getByRole("link", { name: "Essayer sans compte" })).toHaveAttribute("href", "/essai");
  });
});

describe("inscription en attente", () => {
  it("le bandeau : l'échéance, l'effacement, et le dépôt du RCCM", async () => {
    let deposes: unknown[] = [];
    const appels = simulerApi(enAttente({
      [`/organisations/${ORG}/justificatifs`]: (init?: RequestInit) => {
        if (init?.method === "POST") {
          deposes = [{ id: "j1", nature: "rccm", nom_fichier: "rccm.pdf", depose_le: "2026-09-28T10:00:00+00:00" }];
          return json({ id: "j1", nom_fichier: "rccm.pdf" }, 201);
        }
        return deposes;
      },
    }));
    ouvrir(`/dossier/${ORG}`);
    const bandeau = (await screen.findByText(/Inscription en attente de confirmation/)).closest(".bandeau-activation") as HTMLElement;
    expect(bandeau).toHaveTextContent("votre conseiller vous contacte d'ici le 30/09/2026 (2 jours ouvrés)");
    expect(bandeau).toHaveTextContent("Une inscription non confirmée est effacée le 28/10/2026.");
    expect(within(bandeau).getByRole("link", { name: "Contacter votre conseiller" })).toHaveAttribute("href", `/dossier/${ORG}/contact`);

    const fichier = new File(["%PDF-1.4"], "rccm.pdf", { type: "application/pdf" });
    await userEvent.upload(within(bandeau).getByLabelText(/Votre document RCCM/), fichier);
    expect(await within(bandeau).findByText(/rccm\.pdf — déposé le 28\/09\/2026/)).toBeInTheDocument();
    const depot = appels.find((a) => a.chemin === `/organisations/${ORG}/justificatifs` && a.init?.method === "POST")!;
    const corps = depot.init!.body as FormData;
    expect(corps).toBeInstanceOf(FormData);
    expect((corps.get("fichier") as File).name).toBe("rccm.pdf");
  });

  it("un dossier confirmé n'a pas de bandeau", async () => {
    simulerApi(dossier("admin_client"));
    ouvrir(`/dossier/${ORG}`);
    await screen.findByText("Tableau de bord du dossier");
    expect(screen.queryByText(/Inscription en attente/)).not.toBeInTheDocument();
    expect(document.querySelector(".dossier")).not.toHaveClass("non-confirmee");
  });

  it("l'export Excel d'une étude en brouillon est grisé, avec la raison ; le filigrane est posé", async () => {
    simulerApi(enAttente({ [`/organisations/${ORG}/etudes/e1`]: etude({ possible: true, motifs: [] }) }));
    ouvrir(`/dossier/${ORG}/etudes/e1`);
    const bouton = await screen.findByRole("button", { name: "Exporter en Excel" });
    expect(bouton).toBeDisabled();
    expect(bouton).toHaveAttribute("title", "Après confirmation de votre inscription par votre conseiller.");
    expect(document.querySelector(".dossier")).toHaveClass("non-confirmee");
    expect(document.querySelector(".resultats-brouillon")).toHaveAttribute("data-filigrane", "Estimation — non scellée");
  });

  it("le retrait de l'inscription n'est plus offert à l'écran", async () => {
    simulerApi(enAttente({}));
    ouvrir(`/dossier/${ORG}`);
    await screen.findByText(/Inscription en attente de confirmation/);
    expect(screen.queryByRole("button", { name: "Retirer mon inscription" })).not.toBeInTheDocument();
  });

  it("refusée : le motif, et le conseiller à contacter", async () => {
    simulerApi(enAttente({ [`/organisations/${ORG}/activation`]: { ...EN_ATTENTE, etat: "refusee",
      motif: "Le RCCM ne correspond pas à l'entreprise.", echeance: undefined, expire_le: undefined } }));
    ouvrir(`/dossier/${ORG}`);
    expect(await screen.findByText("Inscription refusée")).toBeInTheDocument();
    expect(screen.getByText(/Le RCCM ne correspond pas à l'entreprise\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Contacter votre conseiller" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retirer mon inscription" })).not.toBeInTheDocument();
  });
});
