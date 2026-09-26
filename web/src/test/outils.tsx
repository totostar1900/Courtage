import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { seConnecter } from "../api";
import App from "../App";

/** Une API simulée : chemin (sans /api/v1) → réponse JSON. Une fonction reçoit la requête. */
export function simulerApi(reponses: Record<string, unknown | ((init?: RequestInit) => unknown)>) {
  const appels: { chemin: string; init?: RequestInit }[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    const chemin = url.replace("/api/v1", "").split("?")[0];
    appels.push({ chemin, init });
    const methode = (init?.method ?? "GET").toUpperCase();
    const cle = reponses[`${methode} ${chemin}`] !== undefined ? `${methode} ${chemin}` : chemin;
    let corps = reponses[cle];
    if (typeof corps === "function") corps = (corps as (i?: RequestInit) => unknown)(init);
    if (corps === undefined) return new Response(JSON.stringify({ code: "introuvable", message: `${chemin} ?` }), { status: 404, headers: { "content-type": "application/json" } });
    if (corps instanceof Response) return corps;
    return new Response(JSON.stringify(corps), { status: 200, headers: { "content-type": "application/json" } });
  }));
  return appels;
}

/** `premiereVisite` : la visite guidée n'a jamais été faite (sinon, elle est tenue pour faite : elle se
 *  lancerait seule sur chaque dossier et masquerait l'écran testé). */
export function ouvrir(chemin: string, utilisateur: string | null = "u-drh", { premiereVisite = false } = {}) {
  localStorage.clear();
  if (!premiereVisite) localStorage.setItem("courtage:visite-faite", "1");
  seConnecter(utilisateur);
  return render(<MemoryRouter initialEntries={[chemin]}><App /></MemoryRouter>);
}

export const ORG = "o1";

/** Un dossier minimal, pour un rôle donné. */
export function dossier(role: "admin_client" | "conseiller" | "lecteur_client", extra: Record<string, unknown> = {}) {
  return {
    "/moi": { id: "u", email: null, admin_plateforme: false, organisations: [{ id: ORG, nom: "AZITO", pays: "CI", role }] },
    [`/organisations/${ORG}/fichiers`]: [{ id: "f1", nom_fichier: "p.xlsx", depose_le: "2026-09-26T10:00:00", date_donnees: "2019-12-31", periodicite: "annuel", effectif: 23, anomalies: [] }],
    [`/organisations/${ORG}/regimes`]: [],
    [`/organisations/${ORG}/etudes`]: [{ id: "e1", statut: "brouillon", date_evaluation: "2019-12-31", convention_code: "CI_CCI", dette: 60130415, emise_le: null }],
    [`/organisations/${ORG}/fiches`]: [],
    [`/organisations/${ORG}/equipe`]: [{ id: "c", nom: "Awa Nkoulou", email: "awa@x.cm", telephone: null, role: "conseiller" }],
    ...extra,
  };
}

export function etude(emission: { possible: boolean; motifs: string[] }, statut = "brouillon") {
  return {
    id: "e1", statut, fichier_id: "f1", date_evaluation: "2019-12-31",
    convention: { code: "CI_CCI", libelle: "CCI de Côte d'Ivoire", en_vigueur_du: "1977-07-20", statut: "valide", verification: "" },
    regime: null, hypotheses: { valeurs: {}, ecarts: [], justification: null }, fonds_disponible: 61550447,
    totaux: { effectif: 23, vapf: 118516875, dette: 60130415, charge: 4411469, cotisation_nette: 2991437, cotisation_totale: 3111095 },
    totaux_convention: null, par_categorie: null,
    echeancier: [{ annee: 2021, effectif: 1, ifc: 3000000, prestations_probables: 2900000, vapf: 2800000 }],
    sensibilites: { taux_actualisation_moins_1pt: { dette: 66000000, charge: 1 } },
    anomalies: [], emission, empreinte: null, honoraires_ht: null, emise_le: null,
    rapport: statut === "emise" ? { numero: "RL-AAAA-BBBB" } : null,
  };
}
