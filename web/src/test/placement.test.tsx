import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { dossier, ORG, ouvrir, simulerApi } from "./outils";

const appel = (extra: Record<string, unknown> = {}) => ({
  id: "a1", reference: "AP-2026-01", montant: 5_000_000, echeance: "2026-10-30", premiere: true, etat: "a_payer",
  coordonnees: { banque: "Société Générale Cameroun", titulaire: "Assureur SA", iban: "CM2199999000000000000001", bic: null },
  controle: "modifie", ne_pas_payer: true, a_confirmer: true, contre_appel: null, virement: null, encaisse_le: null,
  pieces: [], ...extra });
const police = (appels: unknown[]) => ({
  id: "p1", assureur: "Assureur A", numero_police: "IFC-001", date_effet: "2026-10-01", periodicite: "annuelle",
  signee_le: "2026-09-29", choix_id: null,
  statut: { code: "signee", libelle: "Signée", etapes: [
    { code: "retenue", libelle: "Offre retenue", fait: true, le: "2026-09-20" },
    { code: "recue", libelle: "Police reçue", fait: true, le: "2026-09-25" },
    { code: "signee", libelle: "Signée", fait: true, le: "2026-09-29" },
    { code: "premiere_prime", libelle: "Première prime encaissée", fait: false, le: null },
    { code: "en_vigueur", libelle: "En vigueur", fait: false, le: null }] },
  pieces: [], appels, releves: { releves: [], etude: null } });
const tableau = (appels: unknown[]) => ({ polices: [police(appels)], offres_a_placer: [], periodicites: ["annuelle"] });

describe("le placement", () => {
  it("l'entreprise lit « ne pas payer » tant que les coordonnées ne sont pas confirmées, puis déclare son virement", async () => {
    const appels = simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/placement`]: tableau([appel()]),
      [`POST /organisations/${ORG}/appels/a1/virement`]: appel({ etat: "declare" }) });
    ouvrir(`/dossier/${ORG}/placement`);
    expect(await screen.findByText("Ne pas payer : coordonnées bancaires à confirmer par votre conseiller.")).toBeInTheDocument();
    expect(screen.getByText("CM2199999000000000000001")).toBeInTheDocument();
    expect(screen.getByText(/Différentes du compte enregistré/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enregistrer le contre-appel" })).toBeNull();   // le conseiller seul
    // Le formulaire ne s'offre pas à côté de « Ne pas payer » : un virement déjà fait se déclare sur demande.
    expect(screen.queryByRole("button", { name: "Déclarer le virement" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Un virement a déjà été fait ? Le déclarer" }));
    await userEvent.type(screen.getByLabelText("Viré le"), "2026-09-29");
    await userEvent.type(screen.getByLabelText("Référence bancaire"), "VIR-778");
    await userEvent.click(screen.getByRole("button", { name: "Déclarer le virement" }));
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith("/virement"))).toBe(true));
    expect(JSON.parse(String(appels.find((a) => a.chemin.endsWith("/virement"))!.init!.body)))
      .toEqual({ vire_le: "2026-09-29", montant: 5_000_000, reference: "VIR-778" });
  });

  it("le conseiller enregistre le contre-appel, au numéro qu'il connaît", async () => {
    const appels = simulerApi({ ...dossier("conseiller"), [`/organisations/${ORG}/placement`]: tableau([appel()]),
      [`POST /organisations/${ORG}/appels/a1/contre-appel`]: appel({ a_confirmer: false, ne_pas_payer: false }) });
    ouvrir(`/dossier/${ORG}/placement`);
    await userEvent.type(await screen.findByLabelText("Confirmé par (nom, service)"), "M. Kamga, comptabilité");
    await userEvent.type(screen.getByLabelText("Au numéro"), "+237 233 42 00 00");
    await userEvent.type(screen.getByLabelText("Le"), "2026-09-29");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer le contre-appel" }));
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith("/contre-appel"))).toBe(true));
    // Pas de quittance : le conseiller la dépose avant de confirmer l'encaissement.
    expect(screen.getByLabelText("Déposer la quittance de l'assureur")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirmer l'encaissement" })).toBeNull();
  });

  it("la frise dit où en est la police ; un appel conforme ne bloque rien", async () => {
    simulerApi({ ...dossier("lecteur_client"), [`/organisations/${ORG}/placement`]: tableau([
      appel({ controle: "conforme", ne_pas_payer: false, a_confirmer: false, etat: "encaisse", encaisse_le: "2026-10-02" })]) });
    ouvrir(`/dossier/${ORG}/placement`);
    const frise = await screen.findByRole("list", { name: "Étapes" });
    expect(within(frise).getByText("Signée")).toBeInTheDocument();
    expect(screen.queryByText(/Ne pas payer/)).toBeNull();
    expect(screen.getByText(/Conforme au compte que le courtier a enregistré/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Déclarer le virement" })).toBeNull();          // lecture seule
  });

  it("le courtier tient le registre des comptes, avec le contre-appel", async () => {
    const appels = simulerApi({ "/moi": { id: "u", email: null, admin_plateforme: true, organisations: [] }, "/alertes": {},
      "/inscriptions": { inscriptions: [], delai_jours_ouvres: 2 }, "/assureurs/comptes": { assureurs: [] },
      "POST /assureurs/comptes": { id: "c1" } });
    ouvrir("/");
    await userEvent.click(await screen.findByRole("button", { name: "Enregistrer un compte" }));
    for (const [champ, valeur] of [["Assureur", "Assureur A"], ["Banque", "SGC"], ["Titulaire", "Assureur A SA"],
      ["IBAN / RIB", "CM2110003001000512345678"], ["Confirmé par (nom, service)", "Mme Ngo"], ["Au numéro", "+237 233 42 00 00"],
      ["Le", "2026-09-29"]] as const) {
      await userEvent.type(screen.getByLabelText(champ), valeur);
    }
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(appels.some((a) => a.chemin === "/assureurs/comptes" && a.init?.method === "POST")).toBe(true));
    expect(JSON.parse(String(appels.find((a) => a.init?.method === "POST")!.init!.body)))
      .toMatchObject({ assureur: "Assureur A", verifie_aupres: "Mme Ngo", verifie_telephone: "+237 233 42 00 00" });
  });
});
