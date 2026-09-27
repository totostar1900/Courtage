// Le client de l'API. L'identité passe par l'en-tête X-Utilisateur tant que
// l'authentification (tâche 8) n'existe pas : c'est un outil de développement.

import { t } from "./i18n";

export class ErreurApi extends Error {
  constructor(
    public statut: number,
    public code: string,
    message: string,
    public details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

const CLE = "courtage:utilisateur";
/** La démonstration statique : l'API est rejouée dans le navigateur (src/demo). */
export const DEMO = import.meta.env.VITE_DEMO === "1";
let enMemoire: string | null = null;   // quand le navigateur refuse le stockage local

export function utilisateurCourant(): string | null {
  try {
    return localStorage.getItem(CLE) ?? enMemoire;
  } catch {
    return enMemoire;
  }
}

export function seConnecter(id: string | null) {
  enMemoire = id;
  try {
    if (id) localStorage.setItem(CLE, id);
    else localStorage.removeItem(CLE);
  } catch {
    /* navigation privée : l'identité ne survivra pas au rechargement */
  }
}

async function appel<T>(chemin: string, init: RequestInit = {}): Promise<T> {
  if (DEMO) {
    const { repondre } = await import("./demo/serveur");
    const corps = typeof init.body === "string" ? JSON.parse(init.body) : init.body;
    return (await repondre(init.method ?? "GET", chemin, corps, utilisateurCourant())) as T;
  }
  const entetes = new Headers(init.headers);
  entetes.set("X-Courtage", "1");   // anti-CSRF : un autre site ne peut pas poser cet en-tête
  const moi = utilisateurCourant();
  if (moi) entetes.set("X-Utilisateur", moi);   // mode développement seulement ; ignoré par un serveur en production
  if (init.body && !(init.body instanceof FormData)) entetes.set("Content-Type", "application/json");
  const r = await fetch(`/api/v1${chemin}`, { ...init, headers: entetes });
  if (r.status === 204) return undefined as T;
  const type = r.headers.get("content-type") ?? "";
  const corps = type.includes("application/json") ? await r.json() : null;
  if (!r.ok) {
    if (corps && typeof corps.code === "string") throw new ErreurApi(r.status, corps.code, corps.message, corps.details);
    const detail = corps?.detail?.[0]?.msg ?? r.statusText;
    throw new ErreurApi(r.status, "requete_invalide", t(`Requête refusée : ${detail}`, `Request refused: ${detail}`));
  }
  return corps as T;
}

export const api = {
  get: <T>(chemin: string) => appel<T>(chemin),
  post: <T>(chemin: string, corps?: unknown) =>
    appel<T>(chemin, { method: "POST", body: corps instanceof FormData ? corps : JSON.stringify(corps ?? {}) }),
  put: <T>(chemin: string, corps: unknown) => appel<T>(chemin, { method: "PUT", body: JSON.stringify(corps) }),
  patch: <T>(chemin: string, corps: unknown) => appel<T>(chemin, { method: "PATCH", body: JSON.stringify(corps) }),
  del: (chemin: string) => appel<void>(chemin, { method: "DELETE" }),
  /** Un fichier (xlsx) à enregistrer sous `nom` : le navigateur le télécharge. */
  async telecharger(chemin: string, nom: string) {
    if (DEMO) {
      throw new ErreurApi(0, "demonstration",
        t("La démonstration ne télécharge pas de fichier : sur le site, ce bouton enregistre le classeur.",
          "The demo does not download files: on the live site, this button saves the workbook."));
    }
    const entetes = new Headers({ "X-Courtage": "1" });
    const moi = utilisateurCourant();
    if (moi) entetes.set("X-Utilisateur", moi);
    const r = await fetch(`/api/v1${chemin}`, { headers: entetes });
    if (!r.ok) throw new ErreurApi(r.status, "telechargement_impossible", t("Le fichier n'a pas pu être téléchargé.", "The file could not be downloaded."));
    const url = URL.createObjectURL(await r.blob());
    const lien = document.createElement("a");
    lien.href = url;
    lien.download = nom;
    document.body.appendChild(lien);
    lien.click();
    lien.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
  /** Un PDF : ouvert dans un nouvel onglet (dans la démonstration, ses pages s'affichent sur place). */
  async ouvrir(chemin: string) {
    if (DEMO) {
      const { DOCUMENTS } = await import("./demo/serveur");
      window.dispatchEvent(new CustomEvent("courtage:document", { detail: DOCUMENTS[chemin] ?? [] }));
      return;
    }
    const moi = utilisateurCourant();
    const r = await fetch(`/api/v1${chemin}`, { headers: moi ? { "X-Utilisateur": moi } : {} });
    if (!r.ok) throw new ErreurApi(r.status, "document_indisponible", t("Document indisponible.", "Document unavailable."));
    const url = URL.createObjectURL(await r.blob());
    window.open(url, "_blank");
  },
};
