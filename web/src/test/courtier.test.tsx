import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { dossier, equipe, ORG, ouvrir, simulerApi } from "./outils";

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

describe("nous contacter", () => {
  it("l'entreprise écrit à son conseiller sur WhatsApp ou par courriel ; l'ancien fil se lit, replié", async () => {
    const fil = { cote: "entreprise", messages: [
      { id: "m1", cote: "courtier", auteur: "Awa Nkoulou", texte: "Bonjour, je vous appelle demain.",
        le: "2026-09-27T10:00:00+00:00", lu_le: "2026-09-27T11:00:00+00:00" },
    ] };
    const eq = equipe("lecteur_client");
    eq.membres = eq.membres.map((m) => (m.role === "conseiller" ? { ...m, telephone: "+237699000011" } : m));
    simulerApi({ ...dossier("lecteur_client"), [`/organisations/${ORG}/equipe`]: eq, [`/organisations/${ORG}/messages`]: fil });
    ouvrir(`/dossier/${ORG}/contact`);
    expect(await screen.findByRole("heading", { name: "Nous contacter" })).toBeInTheDocument();
    const whatsapp = await screen.findByRole("link", { name: "Écrire sur WhatsApp" });
    expect(whatsapp.getAttribute("href")).toMatch(/^https:\/\/wa\.me\/237\d+\?text=/);
    expect(screen.getByRole("link", { name: "Écrire un courriel" }).getAttribute("href")).toMatch(/^mailto:/);
    // L'historique reste lisible, on n'y écrit plus.
    expect(await screen.findByText("Bonjour, je vous appelle demain.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Votre message")).toBeNull();
  });

  it("le conseiller voit les personnes de l'entreprise, avec leurs boutons", async () => {
    simulerApi({ ...dossier("conseiller"), [`/organisations/${ORG}/messages`]: { cote: "courtier", messages: [] } });
    ouvrir(`/dossier/${ORG}/messages`);        // l'ancienne adresse mène à la même page
    expect(await screen.findByRole("heading", { name: "Contacter l'entreprise" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Écrire sur WhatsApp" }).length).toBeGreaterThan(0);
  });
});
