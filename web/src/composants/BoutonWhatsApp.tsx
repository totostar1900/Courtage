import { useState } from "react";

import { DEMO } from "../api";
import { useCabinet } from "../cabinet";
import { lienWhatsApp } from "../contact";
import { t } from "../i18n";

/** Le bouton WhatsApp, en bas à droite : écrire tout de suite, hors de la plateforme. Dans un dossier, au conseiller
 *  (à défaut, au cabinet) ; sur les pages publiques, au cabinet. Sans numéro utilisable, pas de bouton. Le message
 *  prérempli ne dit que le sujet : ni montant ni coordonnées bancaires. En démonstration, les personnes n'ont pas de
 *  numéro (aucun vrai numéro ne doit être appelé) : le bouton s'affiche et dit ce qu'il ferait. */
export default function BoutonWhatsApp({ telephone, message, libelle }: {
  telephone: string | null | undefined; message: string; libelle: string;
}) {
  const [note, setNote] = useState(false);
  const lien = lienWhatsApp(telephone, message);
  if (!lien && !DEMO) return null;
  const demo = !lien;
  return (
    <>
    {demo && note && (
      <div className="bulle-whatsapp" role="status">{t("Démonstration : dans la version réelle, WhatsApp s'ouvre ici, avec un message qui cite le dossier.",
        "Demo: in the real version, WhatsApp opens here, with a message naming the file.")}</div>
    )}
    <a className="bouton-whatsapp" href={lien ?? "#"} target={demo ? undefined : "_blank"} rel="noopener noreferrer"
       aria-label={libelle} onClick={demo ? (e) => { e.preventDefault(); setNote((x) => !x); } : undefined}>
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"
           strokeLinejoin="round" aria-hidden="true">
        <path d="M3.5 20.5l1.3-3.9A8.6 8.6 0 1 1 8 19.3z" />
        <path d="M9.2 8.6c.2-.4.5-.5.8-.5h.5l.8 1.9-.6.8c.5 1 1.3 1.8 2.4 2.4l.8-.6 1.9.8v.5c0 .3-.1.6-.5.8-.9.5-2.2.3-3.6-.7a8.2 8.2 0 0 1-2.2-2.3c-.8-1.3-.9-2.4-.3-3.1z" />
      </svg>
      <span>WhatsApp</span>
    </a>
    </>
  );
}

/** Sur les pages publiques (et la vitrine d'un visiteur) : le cabinet. */
export function WhatsAppCabinet() {
  const cabinet = useCabinet();
  return <BoutonWhatsApp telephone={cabinet?.telephone} libelle={t("Écrire au cabinet sur WhatsApp", "Write to the firm on WhatsApp")}
                         message={t("Bonjour, je souhaite en savoir plus sur Nitch.", "Hello, I would like to know more about Nitch.")} />;
}
