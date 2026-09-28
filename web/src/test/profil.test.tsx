import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { dossier, ORG, ouvrir, simulerApi } from "./outils";

const profil = {
  id: "u", nom_affiche: "Awa Kouassi", telephone: "+237699001122", email: "awa@exemple.cm", email_verifie_le: "2026-09-28T10:00:00",
  admin_plateforme: false, cree_le: "2026-09-28T10:00:00",
  dossiers: [{ id: ORG, nom: "AZITO", pays: "CI", role: "admin_client", fonction: "DRH", activation: "confirmee" }],
  sessions: [
    { id: "s1", cree_le: "2026-09-28T10:00:00", derniere_activite: "2026-09-28T11:00:00", agent: "Mozilla/5.0 (Windows NT 10.0) Chrome/130", courante: true },
    { id: "s2", cree_le: "2026-09-20T10:00:00", derniere_activite: "2026-09-21T11:00:00", agent: "Mozilla/5.0 (Linux; Android 14) Chrome/130", courante: false }],
};

describe("l'espace profil", () => {
  it("s'ouvre depuis le bouton en haut à droite, et dit qui je suis", async () => {
    simulerApi({ ...dossier("admin_client"), "/moi/profil": profil });
    ouvrir(`/dossier/${ORG}`);
    await userEvent.click(await screen.findByRole("link", { name: "Mon profil" }));
    expect(await screen.findByRole("heading", { name: "Mon profil" })).toBeInTheDocument();
    expect(screen.getByText("Awa Kouassi")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "AZITO" })).toHaveAttribute("href", `/dossier/${ORG}`);
    expect(screen.getByText("Chrome · Android")).toBeInTheDocument();
  });

  it("change le nom affiché et déconnecte un autre appareil", async () => {
    const appels = simulerApi({ ...dossier("admin_client"), "/moi/profil": profil,
      "PATCH /moi/profil": { ...profil, nom_affiche: "Awa K." }, "DELETE /moi/sessions/s2": profil });
    ouvrir("/profil");
    await userEvent.click(await screen.findByRole("button", { name: "Modifier mon nom" }));
    const champ = screen.getByLabelText("Nom affiché");
    await userEvent.clear(champ);
    await userEvent.type(champ, "Awa K.");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(appels.some((a) => a.init?.method === "PATCH")).toBe(true));
    const ligne = screen.getByText("Chrome · Android").closest("tr")!;
    await userEvent.click(within(ligne).getByRole("button", { name: "Déconnecter" }));
    await waitFor(() => expect(appels.some((a) => a.chemin === "/moi/sessions/s2" && a.init?.method === "DELETE")).toBe(true));
  });
});
