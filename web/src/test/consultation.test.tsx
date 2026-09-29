import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { dossier, ORG, ouvrir, simulerApi } from "./outils";

const fiches = { [`/organisations/${ORG}/fiches`]: [{ id: "f1", numero: "CC-AAAA-BBBB", etude_id: "e1", date_limite_reponse: "2026-10-26", emise_le: "2026-09-26" }] };
const reponses = { fiche_id: "f1", date_limite_reponse: "2026-10-26", conditions: {}, reponses: [], recommandee: null,
  comparaison: null, choix: null };
const consultation = (extra: Record<string, unknown> = {}) => ({ id: "c1", assureur: "Assureur Lien", contact_nom: "Mme Tchoua",
  contact_courriel: "offres@lien.cm", envoyee_le: "2026-09-27T10:00:00", envoyee_par: "Conseiller", ouverte_le: "2026-09-28T09:00:00",
  repondue_le: null, relances: 0, relancee_le: null, annulee_le: null, expire_le: "2026-10-26", etat: "ouverte", ...extra });
const vue = (extra: Record<string, unknown> = {}) => ({ cabinet: "Cabinet X", client: "AZITO", pays: "CI", assureur: "Assureur Lien",
  cahier: "CC-AAAA-BBBB", date_limite: "2026-10-26", etat: "ouverte", repondue_le: null,
  conditions: [{ cle: "taux_garanti_minimum", libelle: "Taux garanti", valeur: 0.025, sens: "min" },
               { cle: "reporting_annuel", libelle: "Relevé annuel du fonds", valeur: true, sens: "oui" }], ...extra });

describe("la consultation des assureurs", () => {
  it("le conseiller consulte un assureur ; la liste dit qui a été consulté et où il en est", async () => {
    const appels = simulerApi({ ...dossier("conseiller", fiches), [`/organisations/${ORG}/fiches/f1/reponses`]: reponses,
      [`/organisations/${ORG}/fiches/f1/consultations`]: [consultation()],
      [`POST /organisations/${ORG}/fiches/f1/consultations`]: consultation({ id: "c2", assureur: "Assureur B" }),
      [`POST /organisations/${ORG}/consultations/c1/relance`]: consultation({ relances: 1 }) });
    ouvrir(`/dossier/${ORG}/cahier/f1`);
    const zone = (await screen.findByRole("heading", { name: "Assureurs consultés" })).closest("section")!;
    const ligne = (await within(zone).findByText("Assureur Lien")).closest("tr")!;
    expect(within(ligne).getByText("Ouverte")).toBeInTheDocument();
    await userEvent.click(within(ligne).getByRole("button", { name: "Relancer" }));
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith("/relance"))).toBe(true));
    await userEvent.click(within(zone).getByRole("button", { name: "Consulter un assureur" }));
    await userEvent.type(within(zone).getByLabelText("Assureur"), "Assureur B");
    await userEvent.type(within(zone).getByLabelText("Adresse électronique du contact"), "devis@b.cm");
    await userEvent.click(within(zone).getByRole("button", { name: "Envoyer le cahier" }));
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith("/consultations") && a.init?.method === "POST")).toBe(true));
    expect(JSON.parse(String(appels.find((a) => a.init?.method === "POST" && a.chemin.endsWith("/consultations"))!.init!.body)))
      .toEqual({ assureur: "Assureur B", contact_nom: null, contact_courriel: "devis@b.cm" });
  });

  it("l'entreprise voit la liste, sans pouvoir consulter", async () => {
    simulerApi({ ...dossier("admin_client", fiches), [`/organisations/${ORG}/fiches/f1/reponses`]: reponses,
      [`/organisations/${ORG}/fiches/f1/consultations`]: [consultation({ etat: "repondue", repondue_le: "2026-09-29T10:00:00" })] });
    ouvrir(`/dossier/${ORG}/cahier/f1`);
    expect(await screen.findByText("Répondue")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Consulter un assureur" })).toBeNull();
  });

  it("l'assureur, par son lien et sans compte, lit les conditions et dépose sa grille avec son offre PDF", async () => {
    let depose = false;
    const repondue = vue({ etat: "repondue", repondue_le: "2026-09-29T10:00:00" });
    const appels = simulerApi({ "GET /offre/jeton-x": () => (depose ? repondue : vue()),
                                "POST /offre/jeton-x": () => { depose = true; return repondue; } });
    ouvrir("/offre/jeton-x", null);
    expect(await screen.findByText(/Cabinet X, courtier en assurance, consulte Assureur Lien pour le compte de son client AZITO/)).toBeInTheDocument();
    expect(screen.getByText(/Taux garanti ≥ 2,50/)).toBeInTheDocument();
    for (const [champ, valeur] of [["Taux garanti (%)", "3"], ["Participation aux bénéfices (%)", "90"],
      ["Frais sur cotisations (%)", "2"], ["Frais sur encours (%/an)", "0,4"]] as const) {
      await userEvent.type(screen.getByLabelText(champ), valeur.replace(",", "."));
    }
    await userEvent.selectOptions(screen.getByLabelText("Relevé annuel du fonds"), "oui");
    await userEvent.click(screen.getByRole("button", { name: "Déposer mon offre" }));
    expect(await screen.findByText("Joindre votre offre en PDF.")).toBeInTheDocument();          // l'offre est exigée
    await userEvent.upload(screen.getByLabelText("Votre offre signée (PDF)"), new File(["%PDF"], "offre.pdf", { type: "application/pdf" }));
    await userEvent.click(screen.getByRole("button", { name: "Déposer mon offre" }));
    await waitFor(() => expect(appels.some((a) => a.init?.method === "POST")).toBe(true));
    const corps = appels.find((a) => a.init?.method === "POST")!.init!.body as FormData;
    expect(JSON.parse(String(corps.get("donnees")))).toMatchObject({ taux_garanti: 0.03, participation_benefices: 0.9,
      frais_sur_cotisations: 0.02, reporting_annuel: true, delai_paiement_jours: null });
    expect(await screen.findByText(/Votre réponse est reçue/)).toBeInTheDocument();
  });

  it("un lien clos le dit, sans formulaire", async () => {
    simulerApi({ "/offre/jeton-y": vue({ etat: "close" }) });
    ouvrir("/offre/jeton-y", null);
    expect(await screen.findByText(/Cette consultation est close/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Déposer mon offre" })).toBeNull();
  });
});
