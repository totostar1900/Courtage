import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { oublierCabinet } from "../cabinet";
import { ouvrir, simulerApi } from "./outils";

const NON_CONNECTE = new Response(JSON.stringify({ code: "non_authentifie", message: "Connectez-vous." }),
  { status: 401, headers: { "content-type": "application/json" } });

describe("être rappelé", () => {
  beforeEach(() => oublierCabinet());

  it("le visiteur laisse son numéro depuis la vitrine, avec son accord", async () => {
    const appels = simulerApi({ "/moi": () => NON_CONNECTE.clone(), "/public/cabinet": {},
      "POST /public/rappel": { message: "Merci : le courtier vous rappelle au créneau choisi." } });
    ouvrir("/", null);
    const zone = (await screen.findByRole("heading", { name: "Parler à un conseiller" }, { timeout: 4000 })).closest("section")!;
    await userEvent.type(within(zone).getByLabelText("Votre nom"), "Paul Mbarga");
    await userEvent.type(within(zone).getByLabelText("Entreprise"), "Brasseries du Littoral");
    await userEvent.type(within(zone).getByLabelText("Téléphone"), "699123456");
    await userEvent.selectOptions(within(zone).getByLabelText("Quand vous appeler ?"), "matin");
    const bouton = within(zone).getByRole("button", { name: "Être rappelé" });
    expect(bouton).toBeDisabled();                                   // l'accord d'abord
    await userEvent.click(within(zone).getByRole("checkbox", { name: /J'accepte d'être rappelé/ }));
    await userEvent.click(bouton);
    expect(await within(zone).findByText("Merci : le courtier vous rappelle au créneau choisi.")).toBeInTheDocument();
    const corps = JSON.parse(String(appels.find((a) => a.chemin === "/public/rappel")!.init!.body));
    expect(corps).toEqual({ nom: "Paul Mbarga", entreprise: "Brasseries du Littoral", telephone: "+237699123456", courriel: null,
      creneau: "matin", message: null, accord: true, site_web: null });
  });

  it("le courtier voit les demandes et les passe « rappelée », avec une note", async () => {
    const appels = simulerApi({ "/moi": { id: "u", email: null, admin_plateforme: true, organisations: [] }, "/alertes": {},
      "/inscriptions": { inscriptions: [], delai_jours_ouvres: 2 }, "/assureurs/comptes": { assureurs: [] },
      "/rappels": [{ id: "d1", nom: "Paul Mbarga", entreprise: "Brasseries du Littoral", telephone: "+237699123456",
        courriel: null, creneau: "matin", message: "180 salariés", recue_le: "2026-09-29T10:00:00", statut: "a_rappeler",
        note: null, traitee_le: null, traitee_par: null }],
      "PUT /rappels/d1": {} });
    ouvrir("/");
    const zone = (await screen.findByRole("heading", { name: /Demandes de rappel/ })).closest("section")!;
    expect(within(zone).getByText("1 à rappeler")).toBeInTheDocument();
    await userEvent.type(within(zone).getByLabelText("Note sur la demande de Paul Mbarga"), "RDV le 3/10");
    await userEvent.click(within(zone).getByRole("button", { name: "Rappelée" }));
    await waitFor(() => expect(appels.some((a) => a.init?.method === "PUT")).toBe(true));
    expect(JSON.parse(String(appels.find((a) => a.init?.method === "PUT")!.init!.body))).toEqual({ statut: "rappelee", note: "RDV le 3/10" });
  });
});
