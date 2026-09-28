import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { dossier, ORG, ouvrir, simulerApi } from "./outils";

const COURTIER = { id: "adm", email: null, admin_plateforme: true, organisations: [] };

function inscription(id: string, nom: string, extra: Record<string, unknown> = {}) {
  return {
    id, nom, pays: "CM", secteur: "Brasserie", rccm: "RC/DLA/2026/B/1234", taille: "50_a_250", adresse: null,
    ville: "Douala", demandee_le: "2026-09-21T09:00:00+00:00", echeance: "2026-09-23", en_retard: false,
    rccm_depose: true, expire_le: "2026-10-21", messages_non_lus: 0, justificatifs: [],
    demandeur: { nom: "Mme Ngo", fonction: "DRH", telephone: "+237690000001", courriel: "drh@x.cm" }, ...extra,
  };
}

describe("la file des inscriptions", () => {
  it("montre une inscription en retard en rouge, la plus ancienne d'abord", async () => {
    simulerApi({
      "/moi": COURTIER,
      "/inscriptions": { delai_jours_ouvres: 2, inscriptions: [
        inscription("o-a", "Brasseries du Littoral", { en_retard: true, messages_non_lus: 2 }),
        inscription("o-b", "Cimenterie Sud", { rccm_depose: false, echeance: "2026-09-30" }),
      ] },
    });
    ouvrir("/", "adm");
    const carte = await screen.findByRole("article", { name: "Brasseries du Littoral" });
    const retard = within(carte).getByText("en retard");
    expect(retard).toHaveClass("etat", "grave");
    expect(carte).toHaveClass("en-retard");
    expect(within(carte).getByText("2 non lu(s)")).toBeInTheDocument();
    expect(within(carte).getByText("Mme Ngo")).toBeInTheDocument();
    const autre = screen.getByRole("article", { name: "Cimenterie Sud" });
    expect(within(autre).queryByText("en retard")).not.toBeInTheDocument();
    expect(within(autre).getByText("non déposé")).toBeInTheDocument();
    const cartes = screen.getAllByRole("article").map((a) => a.getAttribute("aria-label"));
    expect(cartes).toEqual(["Brasseries du Littoral", "Cimenterie Sud"]);
  });

  it("sans inscription, le dit", async () => {
    simulerApi({ "/moi": COURTIER, "/inscriptions": { delai_jours_ouvres: 2, inscriptions: [] } });
    ouvrir("/", "adm");
    expect(await screen.findByText("Aucune inscription en attente.")).toBeInTheDocument();
  });

  it("un client ne voit pas la file", async () => {
    const appels = simulerApi({ "/moi": { ...COURTIER, admin_plateforme: false } });
    ouvrir("/");
    expect(await screen.findByText("Aucun dossier pour l'instant.")).toBeInTheDocument();
    expect(screen.queryByText("Inscriptions à confirmer")).not.toBeInTheDocument();
    expect(appels.some((a) => a.chemin === "/inscriptions")).toBe(false);
  });

  it("confirmer envoie ce qui a été vérifié et le conseiller choisi, puis relit la file", async () => {
    let decide = false;
    const appels = simulerApi({
      "/moi": COURTIER,
      "/inscriptions/conseillers": { conseillers: [
        { id: "adm", nom: "Le courtier", courriel: null, dossiers: 4, moi: true },
        { id: "c2", nom: "Awa Nkoulou", courriel: "awa@x.cm", dossiers: 1, moi: false }] },
      "/inscriptions": () => ({ delai_jours_ouvres: 2,
        inscriptions: decide ? [] : [inscription("o-a", "Brasseries du Littoral")] }),
      "POST /inscriptions/o-a/decision": () => { decide = true; return { etat: "confirmee" }; },
    });
    ouvrir("/", "adm");
    const carte = await screen.findByRole("article", { name: "Brasseries du Littoral" });
    await userEvent.click(within(carte).getByRole("button", { name: "Confirmer" }));
    const tiroir = screen.getByRole("complementary", { name: "Brasseries du Littoral" });
    const date = within(tiroir).getByLabelText("Date de l'appel");
    await userEvent.clear(date);
    await userEvent.type(date, "2026-09-25");
    await userEvent.type(within(tiroir).getByLabelText("Personne jointe, et à quel titre"), "Mme Ngo, DRH");
    await userEvent.type(within(tiroir).getByLabelText("Note"), "Appel au siège.");
    const choix = within(tiroir).getByLabelText("Conseiller du dossier");
    await waitFor(() => expect(choix).toHaveValue("adm"));                // vous, par défaut
    await userEvent.selectOptions(choix, "c2");
    await userEvent.click(within(tiroir).getByRole("button", { name: "Confirmer l'inscription" }));
    await waitFor(() => expect(appels.some((a) => a.chemin === "/inscriptions/o-a/decision")).toBe(true));
    const envoi = appels.find((a) => a.chemin === "/inscriptions/o-a/decision")!;
    expect(JSON.parse(envoi.init!.body as string)).toEqual({ decision: "confirmer", verification: {
      rccm_recu: true, appel_le: "2026-09-25", habilitation: "Mme Ngo, DRH", note: "Appel au siège." }, conseiller_id: "c2" });
    expect(await screen.findByText("Aucune inscription en attente.")).toBeInTheDocument();
  });

  it("refuser sans motif est impossible", async () => {
    const appels = simulerApi({
      "/moi": COURTIER,
      "/inscriptions": { delai_jours_ouvres: 2, inscriptions: [inscription("o-a", "Brasseries du Littoral")] },
      "POST /inscriptions/o-a/decision": { etat: "refusee" },
    });
    ouvrir("/", "adm");
    const carte = await screen.findByRole("article", { name: "Brasseries du Littoral" });
    await userEvent.click(within(carte).getByRole("button", { name: "Refuser" }));
    const tiroir = screen.getByRole("complementary", { name: "Brasseries du Littoral" });
    const bouton = within(tiroir).getByRole("button", { name: "Refuser l'inscription" });
    expect(bouton).toBeDisabled();
    await userEvent.type(within(tiroir).getByLabelText(/Motif du refus/), "   ");
    expect(bouton).toBeDisabled();
    expect(appels.some((a) => a.chemin === "/inscriptions/o-a/decision")).toBe(false);
    await userEvent.type(within(tiroir).getByLabelText(/Motif du refus/), "RCCM illisible");
    await userEvent.click(bouton);
    await waitFor(() => expect(appels.some((a) => a.chemin === "/inscriptions/o-a/decision")).toBe(true));
    const envoi = appels.find((a) => a.chemin === "/inscriptions/o-a/decision")!;
    expect(JSON.parse(envoi.init!.body as string)).toEqual({ decision: "refuser", motif: "RCCM illisible" });
  });
});

describe("les messages du dossier", () => {
  it("un lecteur écrit à son conseiller et voit son message", async () => {
    const fil = { cote: "entreprise", messages: [
      { id: "m1", cote: "courtier", auteur: "Awa Nkoulou", texte: "Bonjour, je vous appelle demain.",
        le: "2026-09-27T10:00:00+00:00", lu_le: "2026-09-27T11:00:00+00:00" },
    ] };
    const appels = simulerApi({
      ...dossier("lecteur_client"),
      [`/organisations/${ORG}/messages`]: fil,
      [`POST /organisations/${ORG}/messages`]: { ...fil, messages: [...fil.messages,
        { id: "m2", cote: "entreprise", auteur: "Mme DRH", texte: "Merci, à demain.", le: "2026-09-28T08:00:00+00:00", lu_le: null }] },
    });
    ouvrir(`/dossier/${ORG}/messages`);
    expect(await screen.findByText("Bonjour, je vous appelle demain.")).toBeInTheDocument();
    // la lecture relit le dossier : le compteur du rail se met à jour
    await waitFor(() => expect(appels.filter((a) => a.chemin === `/organisations/${ORG}/messages/non-lus`).length).toBeGreaterThan(1));
    await userEvent.type(screen.getByLabelText("Votre message"), "Merci, à demain.");
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));
    expect(await screen.findByText("Merci, à demain.")).toBeInTheDocument();
    const envoi = appels.find((a) => a.chemin === `/organisations/${ORG}/messages` && a.init?.method === "POST")!;
    expect(JSON.parse(envoi.init!.body as string)).toEqual({ texte: "Merci, à demain." });
    expect(screen.getByLabelText("Votre message")).toHaveValue("");
  });

  it("un fil vide dit qui répond", async () => {
    simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/messages`]: { cote: "entreprise", messages: [] } });
    ouvrir(`/dossier/${ORG}/messages`);
    expect(await screen.findByText(/Votre conseiller vous répond ici/)).toBeInTheDocument();
  });

  it("Ctrl+Entrée envoie", async () => {
    const appels = simulerApi({ ...dossier("admin_client"),
      [`/organisations/${ORG}/messages`]: { cote: "entreprise", messages: [] },
      [`POST /organisations/${ORG}/messages`]: { cote: "entreprise", messages: [
        { id: "m2", cote: "entreprise", auteur: "Mme DRH", texte: "Question", le: "2026-09-28T08:00:00+00:00", lu_le: null }] } });
    ouvrir(`/dossier/${ORG}/messages`);
    await userEvent.type(await screen.findByLabelText("Votre message"), "Question{Control>}{Enter}{/Control}");
    await waitFor(() => expect(appels.some((a) => a.init?.method === "POST")).toBe(true));
    expect(await screen.findByText("Question")).toBeInTheDocument();
  });
});
