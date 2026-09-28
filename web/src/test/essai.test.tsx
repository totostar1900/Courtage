import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CLE_ESSAI } from "../pages/Essai";
import { ouvrir, simulerApi } from "./outils";

const conventions = { pays_couverts: { CM: "Cameroun", GA: "Gabon" }, conventions: [
  { code: "CM_COMMERCE", libelle: "Convention du commerce", pays: "CM", pays_libelle: "Cameroun", en_vigueur_aujourd_hui: true }] };
const resultat = { effectif: 23, convention: { code: "CM_COMMERCE", libelle: "Convention du commerce" },
  date_evaluation: "2025-12-31", fonds_disponible: 0, nombre_anomalies: 0,
  totaux: { effectif: 23, vapf: 1, dette: 60_130_415, charge: 4_411_469, cotisation_totale: 3_111_095 },
  echeancier: [], sensibilite: { libelle: "Taux − 1 point", dette: 70_000_000 } };

describe("l'essai sans compte", () => {
  it("calcule à l'écran, filigrané, et garde la saisie dans le navigateur pour l'inscription", async () => {
    const appels = simulerApi({ "/referentiel/conventions": conventions, "/referentiel/modeles": { modeles: [] },
                                "POST /essai/etude": resultat });
    sessionStorage.clear();
    ouvrir("/essai", null);
    const fichier = new File(["matricule;naissance\n"], "personnel.csv", { type: "text/csv" });
    await userEvent.upload(await screen.findByLabelText(/Votre personnel/), fichier);
    await userEvent.click(screen.getByRole("button", { name: "Calculer mon engagement" }));
    expect(await screen.findByText("Estimation — non scellée")).toBeInTheDocument();
    expect(screen.getByText("60,1 M F")).toBeInTheDocument();
    expect(screen.getByText(/la dette passerait à 70 000 000 F/)).toBeInTheDocument();
    const envoi = appels.find((a) => a.chemin === "/essai/etude")!;
    const parametres = JSON.parse(String((envoi.init!.body as FormData).get("parametres")));
    expect(parametres).toMatchObject({ pays: "CM", convention_code: "CM_COMMERCE", fonds_disponible: 0 });
    await waitFor(() => expect(sessionStorage.getItem(CLE_ESSAI)).toContain("personnel.csv"));
    expect(screen.getByRole("link", { name: "Enregistrer mes résultats" })).toHaveAttribute("href", "/inscription");
  });
});
