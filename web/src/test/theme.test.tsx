import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { lireTheme } from "../theme";
import { ouvrir, simulerApi } from "./outils";

describe("le thème clair ou sombre", () => {
  afterEach(() => { localStorage.removeItem("courtage:theme"); document.documentElement.removeAttribute("data-theme"); });

  it("suit l'appareil par défaut, s'impose au choix, et se garde", async () => {
    simulerApi({});
    ouvrir("/ifc", null);
    const auto = await screen.findByRole("button", { name: "Thème de l'appareil" });
    expect(auto).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement).not.toHaveAttribute("data-theme");
    await userEvent.click(screen.getByRole("button", { name: "Thème sombre" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(lireTheme()).toBe("sombre");
    await userEvent.click(screen.getByRole("button", { name: "Thème clair" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    await userEvent.click(auto);
    expect(document.documentElement).not.toHaveAttribute("data-theme");
    expect(localStorage.getItem("courtage:theme")).toBeNull();
  });
});
