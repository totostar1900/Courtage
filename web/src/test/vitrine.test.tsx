import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { oublierCabinet } from "../cabinet";
import { ouvrir, simulerApi } from "./outils";

const CABINET = { nom: "Purpose Capital Courtage", agrement: "[numéro d'agrément]", adresse: "Douala",
  rccm: "RC/DLA/2024/B/1", courriel: "contact@exemple.cm", telephone: "+237 6 99 00 00 00",
  hebergeur: "Render Services, Inc. (render.com)", conditions_version: "conditions-2026-09", manquants: ["agrement"] };
const NON_CONNECTE = new Response(JSON.stringify({ code: "non_authentifie", message: "Connectez-vous." }),
  { status: 401, headers: { "content-type": "application/json" } });

describe("vitrine et pages légales", () => {
  beforeEach(() => oublierCabinet());

  it("sans session, / montre la vitrine : l'offre, la gratuité, le cabinet, les entrées", async () => {
    simulerApi({ "/moi": () => NON_CONNECTE.clone(), "/public/cabinet": CABINET });
    ouvrir("/", null);
    expect(await screen.findByRole("heading", { name: /chiffrées puis placées/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Essayer sans compte" })).toHaveAttribute("href", "/essai");
    expect(screen.getByRole("link", { name: "S'inscrire" })).toHaveAttribute("href", "/inscription");
    expect(screen.getByText("Gratuit pour l'entreprise.")).toBeInTheDocument();
    expect(await screen.findAllByText(/Purpose Capital Courtage/)).not.toHaveLength(0);
    // L'en-tête propose de se connecter, pas le profil.
    expect(screen.getByRole("link", { name: "Se connecter" })).toHaveAttribute("href", "/connexion");
    expect(screen.queryByRole("link", { name: /Mon profil/ })).toBeNull();
  });

  it("avec une session, / reste l'accueil des dossiers", async () => {
    simulerApi({ "/moi": { id: "u", email: null, admin_plateforme: false, organisations: [] }, "/alertes": {},
                 "/public/cabinet": CABINET });
    ouvrir("/");
    expect(await screen.findByRole("heading", { name: "Vos dossiers" })).toBeInTheDocument();
  });

  it("les pages légales se lisent sans session, avec le cabinet et la version des conditions", async () => {
    simulerApi({ "/public/cabinet": CABINET });
    ouvrir("/conditions", null);
    expect(await screen.findByRole("heading", { name: "Conditions d'utilisation" })).toBeInTheDocument();
    expect(await screen.findByText(/conditions-2026-09/)).toBeInTheDocument();
    expect(screen.getByText(/ne sont pas facturés au client/)).toBeInTheDocument();
    ouvrir("/confidentialite", null);
    expect(await screen.findByText(/jamais de nom/)).toBeInTheDocument();
    ouvrir("/mentions-legales", null);
    expect(await screen.findByText(/hébergés par Render/)).toBeInTheDocument();
    // Le pied de page les relie depuis chaque écran.
    expect(screen.getAllByRole("link", { name: "Confidentialité" }).length).toBeGreaterThan(0);
  });
});
