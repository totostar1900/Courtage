import { useCabinet } from "../cabinet";
import { lienAppel, lienCourriel, lienWhatsApp } from "../contact";
import { t } from "../i18n";
import { useDossier } from "./Dossier";

/** WhatsApp, courriel, appel : les trois façons d'écrire ou de parler, hors de la plateforme. Un canal sans numéro ou
 *  sans adresse n'a pas de bouton. */
export function BoutonsContact({ telephone, courriel, message, sujet }: {
  telephone: string | null | undefined; courriel: string | null | undefined; message: string; sujet: string;
}) {
  const whatsapp = lienWhatsApp(telephone, message);
  const mail = lienCourriel(courriel, sujet);
  const appel = lienAppel(telephone);
  if (!whatsapp && !mail && !appel) return <p className="discret">{t("Aucun numéro ni adresse connus.", "No number or address known.")}</p>;
  return (
    <div className="actions boutons-contact">
      {whatsapp && <a className="bouton whatsapp" href={whatsapp} target="_blank" rel="noopener noreferrer">{t("Écrire sur WhatsApp", "Write on WhatsApp")}</a>}
      {mail && <a className="bouton" href={mail}>{t("Écrire un courriel", "Write an email")}</a>}
      {appel && <a className="bouton" href={appel}>{t("Appeler", "Call")}</a>}
    </div>
  );
}

function Personne({ nom, detail, telephone, courriel, message, sujet }: {
  nom: string; detail: string | null; telephone: string | null; courriel: string | null; message: string; sujet: string;
}) {
  return (
    <div className="carte contact-personne">
      <div className="conseiller">
        <div className="avatar">{nom.slice(0, 1)}</div>
        <div><strong>{nom}</strong>{detail && <div className="discret">{detail}</div>}
          <div className="discret">{[telephone, courriel].filter(Boolean).join(" · ")}</div></div>
      </div>
      <BoutonsContact telephone={telephone} courriel={courriel} message={message} sujet={sujet} />
    </div>
  );
}

/** Nous contacter : écrire se fait sur WhatsApp ou par courriel, directement. L'entreprise voit son conseiller (à
 *  défaut, le cabinet) ; le conseiller voit les personnes de l'entreprise. La plateforme ne porte aucun fil écrit. */
export default function Contact() {
  const d = useDossier();
  const cabinet = useCabinet();
  const sujet = t(`Dossier ${d.org.nom}`, `File ${d.org.nom}`);
  const courtier = d.role === "conseiller";
  const conseillers = d.equipe.filter((m) => m.role === "conseiller");
  const entreprise = d.equipe.filter((m) => m.role !== "conseiller" && !m.moi);
  const message = courtier
    ? t(`Bonjour, je vous écris au sujet de votre dossier ${d.org.nom} sur la plateforme de courtage.`,
        `Hello, I am writing about your file ${d.org.nom} on the brokerage platform.`)
    : t(`Bonjour, je vous écris au sujet du dossier ${d.org.nom} sur la plateforme de courtage.`,
        `Hello, I am writing about the file ${d.org.nom} on the brokerage platform.`);
  return (
    <>
      <h1>{courtier ? t("Contacter l'entreprise", "Contact the company") : t("Nous contacter", "Contact us")}</h1>
      <p>{courtier
        ? t("Les personnes du dossier, sur WhatsApp, par courriel ou au téléphone.", "The people on the file, on WhatsApp, by email or by phone.")
        : t("Votre conseiller vous répond sur WhatsApp, par courriel ou au téléphone. Ni coordonnées bancaires ni montants par message : ils restent sur la plateforme.",
            "Your adviser answers on WhatsApp, by email or by phone. No bank details or amounts by message: they stay on the platform.")}</p>

      <section className="section grille g2" aria-label={t("Contacts", "Contacts")}>
        {courtier
          ? (entreprise.length ? entreprise.map((m) => (
              <Personne key={m.id} nom={m.nom} detail={m.fonction} telephone={m.telephone} courriel={m.email} message={message} sujet={sujet} />))
            : <p className="discret">{t("Personne d'autre sur ce dossier.", "Nobody else on this file.")}</p>)
          : conseillers.length ? conseillers.map((m) => (
              <Personne key={m.id} nom={m.nom} detail={m.fonction ?? t("Votre conseiller", "Your adviser")} telephone={m.telephone}
                        courriel={m.email} message={message} sujet={sujet} />))
            : cabinet && <Personne nom={cabinet.nom} detail={t("Le cabinet de courtage", "The brokerage firm")} telephone={cabinet.telephone}
                                   courriel={cabinet.courriel} message={message} sujet={sujet} />}
      </section>

    </>
  );
}
