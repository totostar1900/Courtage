import { useEffect } from "react";

import { api, DEMO } from "./api";

export type Evenement = "vitrine" | "contenu_ifc" | "contenu_cameroun" | "essai_ouvert" | "essai_calcule" | "inscription_ouverte";

/** Le navigateur demande-t-il à ne pas être suivi ? Alors rien ne part. */
function refuse(): boolean {
  const n = navigator as Navigator & { globalPrivacyControl?: boolean; doNotTrack?: string | null };
  return n.globalPrivacyControl === true || n.doNotTrack === "1" || (window as { doNotTrack?: string }).doNotTrack === "1";
}

/** Compte un événement public, une fois par session de navigation : ni témoin, ni identifiant (spec 2026-09-29 §2).
 *  Le référent part pour sa catégorie seulement ; le serveur ne garde pas l'adresse. */
export function mesurer(evenement: Evenement): void {
  if (DEMO || refuse()) return;
  const cle = `courtage:mesure:${evenement}`;
  try {
    if (sessionStorage.getItem(cle)) return;
    sessionStorage.setItem(cle, "1");
  } catch { /* stockage refusé : on compte quand même, une fois par page */ }
  api.post("/public/mesure", { evenement, referent: document.referrer || null }).catch(() => undefined);
}

export function useMesure(evenement: Evenement): void {
  useEffect(() => { mesurer(evenement); }, [evenement]);
}
