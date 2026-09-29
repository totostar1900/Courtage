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

  it("change d'indicatif au menu, et rend le numéro complet", async () => {
    function Hote() {
      const [v, setV] = useState("");
      return <><ChampTelephone libelle="Téléphone" valeur={v} onChange={setV} /><output>{v}</output></>;
    }
    render(<Hote />);
    await userEvent.selectOptions(screen.getByLabelText("Indicatif du pays"), "GA");
    await userEvent.type(screen.getByLabelText("Téléphone"), "06 12 34 56");
    expect(document.querySelector("output")).toHaveTextContent("+24106123456");
  });
});
