import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { lireTheme } from "../theme";
import { ouvrir, simulerApi } from "./outils";

describe("le thème clair ou sombre", () => {
  afterEach(() => { localStorage.removeItem("courtage:theme"); document.documentElement.removeAttribute("data-theme"); });

  it("suit l'appareil par défaut, s'impose au choix, et se garde", async () => {
    const barres = ["light", "dark"].map((m) => {
      const b = document.createElement("meta");
      b.name = "theme-color"; b.media = `(prefers-color-scheme: ${m})`; b.content = m === "dark" ? "#070b10" : "#f5f7f9";
      return document.head.appendChild(b);
    });
    const couleurs = () => barres.map((b) => b.content);
    simulerApi({});
    ouvrir("/ifc", null);
    const auto = await screen.findByRole("button", { name: "Thème de l'appareil" });
    expect(auto).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement).not.toHaveAttribute("data-theme");
    await userEvent.click(screen.getByRole("button", { name: "Thème sombre" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(lireTheme()).toBe("sombre");
    expect(couleurs()).toEqual(["#070b10", "#070b10"]);   // la barre du navigateur suit le thème imposé
    await userEvent.click(screen.getByRole("button", { name: "Thème clair" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    await userEvent.click(auto);
    expect(document.documentElement).not.toHaveAttribute("data-theme");
    expect(localStorage.getItem("courtage:theme")).toBeNull();
    expect(couleurs()).toEqual(["#f5f7f9", "#070b10"]);   // puis rend la main à l'appareil
    barres.forEach((b) => b.remove());
  });
});
