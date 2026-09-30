import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    // La vitrine attend la réponse 401 de /moi : sous la charge de la suite complète, plus d'une seconde.
    expect(await screen.findByRole("heading", { name: /chiffrées puis placées/ }, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Essayer sans compte" })).toHaveAttribute("href", "/essai");
    expect(screen.getByRole("link", { name: "S'inscrire" })).toHaveAttribute("href", "/inscription");
    expect(screen.getByText("Gratuit pour l'entreprise")).toBeInTheDocument();
    expect(screen.queryByText(/rémunéré par/)).toBeNull();          // la vitrine ne parle pas de la rémunération du courtier
    // Être rappelé : un bouton du bandeau, qui mène à la carte du rappel.
    expect(screen.getByRole("link", { name: "Être rappelé" })).toHaveAttribute("href", "#vitrine-rappel");
    // Ce que vous obtenez : les assureurs en concurrence d'abord ; puis l'équipe.
    expect(screen.getByRole("heading", { name: "Les assureurs en concurrence pour vous" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "L'expérience à votre service" })).toBeInTheDocument();
    expect(screen.getByText(/plus de 50 ans d'expérience cumulée/)).toBeInTheDocument();
    expect(screen.getByText("Cameroun et Afrique centrale")).toBeInTheDocument();
    expect(screen.getByText("Une connaissance approfondie du secteur de l'assurance")).toBeInTheDocument();
    // La vitrine parle en « nous » : plus de « le courtier » à la troisième personne.
    expect(screen.getByText("Votre courtier en ligne, pour les entreprises de la CEMAC.")).toBeInTheDocument();
    expect(document.querySelector(".vitrine")!.textContent).not.toMatch(/le courtier (vous|confirme|consulte|désigne)|du courtier/);
    // L'aperçu défile ; ses points le mènent à la main.
    const offres = screen.getByRole("button", { name: "Voir : Les offres" });
    expect(offres).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(offres);
    expect(offres).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Offres classées").closest(".apercu-carte")).toHaveClass("visible");
    expect(await screen.findAllByText(/Purpose Capital Courtage/, {}, { timeout: 4000 })).not.toHaveLength(0);
    // L'en-tête propose de se connecter, pas le profil.
    expect(await screen.findByRole("link", { name: "Se connecter" }, { timeout: 4000 })).toHaveAttribute("href", "/connexion");
    expect(screen.queryByRole("link", { name: /Mon profil/ })).toBeNull();
    // La marque : le logotype Nitch en tête, et le cabinet nommé comme exploitant au pied.
    expect(screen.getByRole("link", { name: "Nitch, accueil" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("img", { name: "Nitch" })).toBeInTheDocument();
    expect(screen.getByText(/exploitée par Purpose Capital Courtage/)).toBeInTheDocument();
    // Le visiteur écrit au cabinet sur WhatsApp, depuis le bouton en bas à droite.
    expect(screen.getByRole("link", { name: "Écrire au cabinet sur WhatsApp" }).getAttribute("href"))
      .toMatch(/^https:\/\/wa\.me\/237699000000\?text=/);
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

describe("être trouvé", () => {
  it("chaque page publique a son titre", async () => {
    simulerApi({ "/public/cabinet": CABINET });
    ouvrir("/conditions", null);
    await screen.findByRole("heading", { name: "Conditions d'utilisation" });
    expect(document.title).toBe("Conditions d'utilisation — Nitch");
    ouvrir("/essai", null);
    await waitFor(() => expect(document.title).toBe("Essayer sans compte — Nitch"));
  });
});

describe("la rémunération du courtier", () => {
  it("n'est dite que par les conditions d'utilisation et par le mandat, jamais sur une page de présentation", () => {
    const sources = import.meta.glob(["../**/*.{ts,tsx}", "!../test/**", "!../pages/Legal.tsx"],
      { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    const fautifs = Object.entries(sources)
      .filter(([, texte]) => /rémunér|broker is paid|pays the broker/i.test(texte))
      .map(([chemin]) => chemin);
    expect(Object.keys(sources).length).toBeGreaterThan(20);        // le filtre a bien lu les sources
    expect(fautifs).toEqual([]);
  });
});

describe("les marchés de l'équipe", () => {
  it("ne citent jamais l'Amérique", () => {
    const sources = import.meta.glob(["../**/*.{ts,tsx}", "!../test/**"], { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    expect(Object.entries(sources).filter(([, texte]) => /amérique|america/i.test(texte)).map(([c]) => c)).toEqual([]);
  });
});

