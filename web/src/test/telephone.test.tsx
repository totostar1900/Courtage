import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { ChampTelephone, composer, decomposer } from "../composants/ChampTelephone";

describe("le téléphone et son indicatif", () => {
  it("compose la forme internationale selon le pays", () => {
    expect(composer("CM", "6 99 12 34 56")).toBe("+237699123456");
    expect(composer("CI", "07 01 23 45 67")).toBe("+2250701234567");     // le 0 ivoirien fait partie du numéro
    expect(composer("FR", "06 12 34 56 78")).toBe("+33612345678");       // le 0 français tombe
    expect(composer("CM", "+241 06 12 34 56")).toBe("+24106123456");     // déjà international : l'indicatif ne s'ajoute pas
    expect(composer("CM", "00 33 6 12 34 56 78")).toBe("+33612345678");
    expect(composer("CM", "  ")).toBe("");
  });

  it("retrouve le pays d'un numéro connu", () => {
    expect(decomposer("+237699123456")).toEqual({ pays: "CM", national: "699123456" });
    expect(decomposer("+2250701234567")).toEqual({ pays: "CI", national: "0701234567" });
  });

  function Hote() {
    const [v, setV] = useState("");
    return <><ChampTelephone libelle="Téléphone" valeur={v} onChange={setV} /><output>{v}</output></>;
  }

  it("l'indicatif se tape : « +33 » donne la France, et le 0 français tombe", async () => {
    render(<Hote />);
    const indicatif = screen.getByRole("combobox", { name: "Indicatif du pays" });
    expect(indicatif).toHaveValue("+237");                                      // le Cameroun d'abord
    await userEvent.click(indicatif);
    await userEvent.keyboard("+33{Enter}");
    expect(indicatif).toHaveValue("+33");
    await userEvent.type(screen.getByLabelText("Téléphone"), "06 12 34 56 78");
    expect(document.querySelector("output")).toHaveTextContent("+33612345678");
  });

  it("le pays se choisit aussi par son nom, dans la liste de tous les pays", async () => {
    render(<Hote />);
    const indicatif = screen.getByRole("combobox", { name: "Indicatif du pays" });
    await userEvent.click(indicatif);
    expect(screen.getAllByRole("option").length).toBeGreaterThan(200);          // tous les pays, pas une sélection
    await userEvent.keyboard("Gab");
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual(["🇬🇦Gabon+241"]);
    await userEvent.click(screen.getByRole("option", { name: /Gabon/ }));
    expect(indicatif).toHaveValue("+241");
    await userEvent.type(screen.getByLabelText("Téléphone"), "06 12 34 56");
    expect(document.querySelector("output")).toHaveTextContent("+24106123456");
  });

  it("un indicatif partagé garde le pays choisi ; un indicatif inconnu ne change rien", async () => {
    render(<Hote />);
    const indicatif = screen.getByRole("combobox", { name: "Indicatif du pays" });
    await userEvent.click(indicatif);
    await userEvent.keyboard("Canada{Enter}");
    expect(indicatif).toHaveValue("+1");
    expect(indicatif).toHaveAttribute("title", "Canada");
    await userEvent.click(indicatif);
    await userEvent.keyboard("1{Enter}");                                      // +1 : le Canada reste le Canada
    expect(indicatif).toHaveAttribute("title", "Canada");
    await userEvent.click(indicatif);
    await userEvent.keyboard("999{Enter}");                                    // aucun pays : rien ne change
    expect(indicatif).toHaveValue("+1");
  });
});
