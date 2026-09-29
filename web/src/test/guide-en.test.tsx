import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { CHAPITRES } from "../guide/chapitres";
import { CHAPITRES_EN } from "../guide/chapitres-en";
import { LECONS } from "../guide/lecons";
import { changerLangue, relireLangue } from "../i18n";
import { ouvrir, simulerApi } from "./outils";

// `ouvrir` vide le stockage puis relit la langue : la langue gardée se pose par `stockage`, puis se relit — l'application
// se remonte dans la langue choisie, comme au clic sur « English ».
function ouvrirEnAnglais(chemin: string) {
  ouvrir(chemin, null, { stockage: { "courtage:langue": "en" } });
  act(() => relireLangue());
}

afterEach(() => changerLangue("fr"));

describe("the guide in English", () => {
  it("every chapter has its English, section for section and paragraph for paragraph", () => {
    changerLangue("fr");
    const francais = CHAPITRES.map((c) => ({ id: c.id, sections: c.sections.map((s) => s.texte.length) }));
    for (const { id, sections } of francais) {
      const en = CHAPITRES_EN[id];
      expect(en, id).toBeDefined();
      expect(en.sections.map((s) => s.texte.length), id).toEqual(sections);
    }
    expect(Object.keys(CHAPITRES_EN).sort()).toEqual(francais.map((c) => c.id).sort());
  });

  it("opens on the first chapter, its group and its sections in English", async () => {
    simulerApi({});
    ouvrirEnAnglais("/guide");
    expect(await screen.findByRole("heading", { level: 1, name: "What the platform does" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Three principles" })).toBeInTheDocument();
    expect(screen.getAllByText("Getting started").length).toBeGreaterThan(0);
    expect(screen.queryByText(/chapters are in French/)).not.toBeInTheDocument();
    // The previous / next links read from the same list, in the same language.
    expect(screen.getByRole("link", { name: "Try, sign up, get confirmed →" })).toBeInTheDocument();
  });

  it("a lesson: its screens, its question and its reason in English", async () => {
    simulerApi({});
    ouvrirEnAnglais("/guide/lecons/lire-les-chiffres");
    expect(await screen.findByRole("heading", { level: 1, name: "Reading the four key figures" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "The actuarial liability" })).toBeInTheDocument();
    for (let i = 0; i < 3; i++) await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(screen.getByRole("button", { name: "The question" }));
    await userEvent.click(screen.getByRole("radio", { name: "79.1 M" }));
    expect(screen.getByText("Correct.")).toBeInTheDocument();
    expect(screen.getByText(/The 3 M difference is the insurer's fees/)).toBeInTheDocument();
    // The next lesson is found in the same list: identity holds from one read to the next.
    expect(screen.getByRole("button", { name: "Next lesson" })).toBeInTheDocument();
  });

  it("the search reads the English text", async () => {
    simulerApi({});
    ouvrirEnAnglais("/guide");
    await userEvent.type(await screen.findByRole("searchbox", { name: "Search the guide" }), "tender specifications");
    const resultats = within(document.querySelector(".guide-texte") as HTMLElement);
    expect(resultats.getByRole("heading", { level: 2, name: "Chapters" })).toBeInTheDocument();
    expect(resultats.getByRole("link", { name: "5. The tender specifications" })).toBeInTheDocument();
  });

  it("the lists follow the language without being re-imported", () => {
    changerLangue("fr");
    expect(LECONS[0].titre).toBe("L'IFC en deux minutes");
    changerLangue("en");
    expect(LECONS[0].titre).toBe("End-of-service benefits in two minutes");
    expect(CHAPITRES.indexOf(CHAPITRES.find((c) => c.id === "regime")!)).toBeGreaterThan(0);
  });
});
