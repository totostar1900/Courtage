import { useCabinet } from "../cabinet";
import { lienWhatsApp } from "../contact";
import { t } from "../i18n";

/** Le bouton WhatsApp, en bas à droite : écrire tout de suite, hors de la plateforme. Dans un dossier, au conseiller
 *  (à défaut, au cabinet) ; sur les pages publiques, au cabinet. Sans numéro utilisable, pas de bouton. Le message
 *  prérempli ne dit que le sujet : ni montant ni coordonnées bancaires. */
export default function BoutonWhatsApp({ telephone, message, libelle }: {
  telephone: string | null | undefined; message: string; libelle: string;
}) {
  const lien = lienWhatsApp(telephone, message);
  if (!lien) return null;
  return (
    <a className="bouton-whatsapp" href={lien} target="_blank" rel="noopener noreferrer"
       aria-label={libelle}>
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"
           strokeLinejoin="round" aria-hidden="true">
        <path d="M3.5 20.5l1.3-3.9A8.6 8.6 0 1 1 8 19.3z" />
        <path d="M9.2 8.6c.2-.4.5-.5.8-.5h.5l.8 1.9-.6.8c.5 1 1.3 1.8 2.4 2.4l.8-.6 1.9.8v.5c0 .3-.1.6-.5.8-.9.5-2.2.3-3.6-.7a8.2 8.2 0 0 1-2.2-2.3c-.8-1.3-.9-2.4-.3-3.1z" />
      </svg>
      <span>WhatsApp</span>
    </a>
  );
}

/** Sur les pages publiques (et la vitrine d'un visiteur) : le cabinet. */
export function WhatsAppCabinet() {
  const cabinet = useCabinet();
  return <BoutonWhatsApp telephone={cabinet?.telephone} libelle={t("Écrire au cabinet sur WhatsApp", "Write to the firm on WhatsApp")}
                         message={t("Bonjour, je souhaite en savoir plus sur Nitch.", "Hello, I would like to know more about Nitch.")} />;
}
