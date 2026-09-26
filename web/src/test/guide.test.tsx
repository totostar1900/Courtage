import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ASTUCES } from "../guide/astuces";
import { CHAPITRES } from "../guide/chapitres";
import { GLOSSAIRE } from "../guide/glossaire";
import { LECONS } from "../guide/lecons";
import { VISITE_DOSSIER } from "../guide/visite";
import { dossier, etude, ORG, ouvrir, simulerApi } from "./outils";

describe("le texte du guide se tient", () => {
  const chapitres = new Set(CHAPITRES.map((c) => c.id));
  const lecons = new Set(LECONS.map((l) => l.id));

  it("chaque renvoi mène quelque part", () => {
    for (const a of ASTUCES) {
      if (a.chapitre) expect(chapitres, a.texte).toContain(a.chapitre);
      if (a.lecon) expect(lecons, a.texte).toContain(a.lecon);
    }
    for (const d of Object.values(GLOSSAIRE)) if (d.chapitre) expect(chapitres, d.terme).toContain(d.chapitre);
    expect(new Set(CHAPITRES.map((c) => c.id)).size).toBe(CHAPITRES.length);
  });

  it("chaque question a sa bonne réponse parmi ses choix", () => {
    for (const l of LECONS) expect(l.quiz.bonne, l.id).toBeLessThan(l.quiz.choix.length);
  });

  it("chaque étape de la visite pointe un élément que le code pose", () => {
    const racine = join(__dirname, "..");
    const sources = [racine, join(racine, "pages"), join(racine, "composants")]
      .flatMap((d) => readdirSync(d).filter((f) => f.endsWith(".tsx")).map((f) => readFileSync(join(d, f), "utf-8")))
      .join("\n");
    for (const e of VISITE_DOSSIER) expect(sources, e.cible).toContain(`data-visite="${e.cible}"`);
  });

  it("la leçon des chiffres clés dit le calcul que l'écran affiche", () => {
    // 110,7 + 10,3 − 45,0 = 76,0 ; × 1,04 = 79,04 → 79,1 avec les montants exacts de la démonstration.
    const l = LECONS.find((x) => x.id === "lire-les-chiffres")!;
    expect(l.quiz.choix[l.quiz.bonne]).toBe("79,1 M");
  });
});

describe("l'écran du guide", () => {
  it("s'ouvre sans compte, sur « Ce que fait la plateforme »", async () => {
    simulerApi({});
    ouvrir("/guide", null);
    expect(await screen.findByRole("heading", { level: 1, name: "Ce que fait la plateforme" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Se déconnecter" })).not.toBeInTheDocument();
  });

  it("la recherche trouve la définition, accents ignorés", async () => {
    simulerApi({});
    ouvrir("/guide", null);
    await userEvent.type(await screen.findByRole("searchbox", { name: "Chercher dans le guide" }), "cotisation a verser");
    expect(screen.getByText(/Le montant à verser à l'assureur, frais compris/)).toBeInTheDocument();
  });

  it("une leçon : les écrans, la question, la raison", async () => {
    simulerApi({});
    ouvrir("/guide/lecons/lire-les-chiffres", null);
    for (let i = 0; i < 3; i++) await userEvent.click(await screen.findByRole("button", { name: "Suivant" }));
    await userEvent.click(screen.getByRole("button", { name: "La question" }));
    await userEvent.click(screen.getByRole("radio", { name: "79,1 M" }));
    expect(screen.getByText("Exact.")).toBeInTheDocument();
    expect(screen.getByText(/Les 3 M d'écart sont les frais/)).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem("courtage:lecons-faites")!)).toEqual(["lire-les-chiffres"]);
  });

  it("les conventions préremplies se consultent, barème et sources", async () => {
    simulerApi({ "/referentiel/conventions": { version: "2026-09-26", conventions: [{
      pays: "CM", pays_libelle: "Cameroun", code: "CM_COMMERCE", libelle: "Convention du commerce (révisée)", statut: "valide",
      en_vigueur_du: "2024-01-16", en_vigueur_au: null, en_vigueur_aujourd_hui: true,
      sources: [{ titre: "Droit social en pratique", url: "https://exemple.cm", consulte_le: "2026-09-26" }],
      verification: "Quatre sources concordantes.", notes: [],
      bareme: { forme: "tranches_cumulatives", tranches: [{ jusqu_a: 5, mois_par_annee: 0.45 }, { jusqu_a: null, mois_par_annee: 0.5 }] },
      illustration: [{ anciennete: 10, mois: 4.75 }] }] } });
    ouvrir("/guide/conventions-preremplies", null);
    const carte = within(await screen.findByText("Convention du commerce (révisée)").then((e) => e.closest("details") as HTMLElement));
    expect(carte.getByText("De 1 à 5 ans")).toBeInTheDocument();
    expect(carte.getByText("45 % d'un mois par année")).toBeInTheDocument();
    expect(carte.getByText("4,75")).toBeInTheDocument();
    expect(carte.getByRole("link", { name: "Droit social en pratique" })).toHaveAttribute("href", "https://exemple.cm");
  });
});

describe("dans le dossier", () => {
  const avecEtude = () => simulerApi({ ...dossier("admin_client"), [`/organisations/${ORG}/etudes/e1`]: etude({ possible: true, motifs: [] }) });

  it("un chiffre clé donne sa définition en infobulle", async () => {
    avecEtude();
    ouvrir(`/dossier/${ORG}`);
    await userEvent.click(await screen.findByRole("button", { name: "Définition : Dette actuarielle" }));
    expect(screen.getByRole("tooltip")).toHaveTextContent(/déjà acquise par les années passées/);
  });

  it("« Le saviez-vous ? » se referme jusqu'à demain", async () => {
    avecEtude();
    ouvrir(`/dossier/${ORG}`);
    await userEvent.click(await screen.findByRole("button", { name: "Fermer l'astuce" }));
    expect(screen.queryByLabelText("Le saviez-vous ?")).not.toBeInTheDocument();
    expect(localStorage.getItem("courtage:astuce-fermee")).toBe(new Date().toISOString().slice(0, 10));
  });

  it("la visite se lance seule la première fois, et se passe", async () => {
    avecEtude();
    ouvrir(`/dossier/${ORG}`, "u-drh", { premiereVisite: true });
    const bulle = await screen.findByRole("dialog", { name: /Visite guidée : Votre parcours/ }, { timeout: 2000 });
    expect(within(bulle).getByText(`1 / ${VISITE_DOSSIER.length}`)).toBeInTheDocument();
    await userEvent.click(within(bulle).getByRole("button", { name: "Suivant" }));
    expect(await screen.findByRole("dialog", { name: /La prochaine étape/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Passer la visite" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(localStorage.getItem("courtage:visite-faite")).toBe("1");
  });

  it("puis se relance sur demande, jusqu'au bout", async () => {
    avecEtude();
    ouvrir(`/dossier/${ORG}`);
    await screen.findByText("Où en est votre dossier");
    await act(async () => { await new Promise((r) => setTimeout(r, 450)); });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Visite guidée" }));
    for (let i = 1; i < VISITE_DOSSIER.length; i++) await userEvent.click(await screen.findByRole("button", { name: "Suivant" }));
    await userEvent.click(screen.getByRole("button", { name: "Terminer" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
