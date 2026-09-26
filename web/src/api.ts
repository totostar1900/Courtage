// Le client de l'API. L'identité passe par l'en-tête X-Utilisateur tant que
// l'authentification (tâche 8) n'existe pas : c'est un outil de développement.

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

export function utilisateurCourant(): string | null {
  try {
    return localStorage.getItem(CLE);
  } catch {
    return null;
  }
}

export function seConnecter(id: string | null) {
  try {
    if (id) localStorage.setItem(CLE, id);
    else localStorage.removeItem(CLE);
  } catch {
    /* navigation privée : l'identité ne survivra pas au rechargement */
  }
}

async function appel<T>(chemin: string, init: RequestInit = {}): Promise<T> {
  const entetes = new Headers(init.headers);
  const moi = utilisateurCourant();
  if (moi) entetes.set("X-Utilisateur", moi);
  if (init.body && !(init.body instanceof FormData)) entetes.set("Content-Type", "application/json");
  const r = await fetch(`/api/v1${chemin}`, { ...init, headers: entetes });
  if (r.status === 204) return undefined as T;
  const type = r.headers.get("content-type") ?? "";
  const corps = type.includes("application/json") ? await r.json() : null;
  if (!r.ok) {
    if (corps && typeof corps.code === "string") throw new ErreurApi(r.status, corps.code, corps.message, corps.details);
    const detail = corps?.detail?.[0]?.msg ?? r.statusText;
    throw new ErreurApi(r.status, "requete_invalide", `Requête refusée : ${detail}`);
  }
  return corps as T;
}

export const api = {
  get: <T>(chemin: string) => appel<T>(chemin),
  post: <T>(chemin: string, corps?: unknown) =>
    appel<T>(chemin, { method: "POST", body: corps instanceof FormData ? corps : JSON.stringify(corps ?? {}) }),
  put: <T>(chemin: string, corps: unknown) => appel<T>(chemin, { method: "PUT", body: JSON.stringify(corps) }),
  del: (chemin: string) => appel<void>(chemin, { method: "DELETE" }),
  /** Un PDF : ouvert dans un nouvel onglet. */
  async ouvrir(chemin: string) {
    const moi = utilisateurCourant();
    const r = await fetch(`/api/v1${chemin}`, { headers: moi ? { "X-Utilisateur": moi } : {} });
    if (!r.ok) throw new ErreurApi(r.status, "document_indisponible", "Document indisponible.");
    const url = URL.createObjectURL(await r.blob());
    window.open(url, "_blank");
  },
};
