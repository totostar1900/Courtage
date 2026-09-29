import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { api } from "../api";
import type { Fil } from "../activation";
import { useCabinet } from "../cabinet";
import { Erreur } from "../composants/communs";
import { lienAppel, lienCourriel, lienWhatsApp } from "../contact";
import { dateFr } from "../format";
import { t } from "../i18n";
import { useDossier } from "./Dossier";

/** L'heure d'un message, à côté de sa date, à l'heure de celui qui lit : « 28/09/2026 · 14:05 ». */
function quand(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return dateFr(iso);
  const deux = (n: number) => String(n).padStart(2, "0");
  return `${deux(d.getDate())}/${deux(d.getMonth() + 1)}/${d.getFullYear()} · ${deux(d.getHours())}:${deux(d.getMinutes())}`;
}

/** Un fil de messages, lu et écrit à `chemin` (GET le fil, POST {texte} rend le fil). Lire le fil marque lu ce que
 *  l'autre côté a écrit : `onLu` est appelé une fois, après la première lecture. */
export function Conversation({ chemin, vide, onLu, lectureSeule }: { chemin: string; vide: string; onLu?: () => void;
                                                                   lectureSeule?: boolean }) {
  const [fil, setFil] = useState<Fil | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [texte, setTexte] = useState("");
  const [enCours, setEnCours] = useState(false);
  const liste = useRef<HTMLOListElement>(null);
  const lu = useRef(onLu);
  useEffect(() => { lu.current = onLu; }, [onLu]);

  useEffect(() => {
    let actif = true;
    api.get<Fil>(chemin)
      .then((f) => { if (actif) { setFil(f); setErreur(null); lu.current?.(); } })
      .catch((e) => { if (actif) setErreur(e); });
    return () => { actif = false; };
  }, [chemin]);

  useEffect(() => {
    const l = liste.current;
    if (l) l.scrollTop = l.scrollHeight;
  }, [fil]);

  async function envoyer(ev?: FormEvent) {
    ev?.preventDefault();
    const propre = texte.trim();
    if (!propre || enCours) return;
    setEnCours(true);
    setErreur(null);
    try {
      setFil(await api.post<Fil>(chemin, { texte: propre }));
      setTexte("");
    } catch (e) {
      setErreur(e);
    } finally {
      setEnCours(false);
    }
  }

  function touche(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); void envoyer(); }
  }

  return (
    <div className="conversation">
      {!fil && !erreur && <p className="discret">{t("Chargement des messages…", "Loading messages…")}</p>}
      {fil && fil.messages.length === 0 && <p className="discret conversation-vide">{vide}</p>}
      {fil && fil.messages.length > 0 && (
        <ol ref={liste} className="fil-messages" aria-label={t("Fil des messages", "Message thread")}>
          {fil.messages.map((m) => {
            const mien = m.cote === fil.cote;
            return (
              <li key={m.id} className={`message ${mien ? "mien" : "autre"}`}>
                <div className="message-tete">
                  <strong>{m.auteur}</strong>
                  <span className="discret">
                    {" · "}{m.cote === "courtier" ? t("courtier", "broker") : t("entreprise", "company")}
                  </span>
                </div>
                <div className="message-texte">{m.texte}</div>
                <div className="message-pied discret">
                  <time dateTime={m.le}>{quand(m.le)}</time>
                  {mien && m.lu_le && <span className="message-lu">{" · "}{t("lu", "read")}</span>}
                </div>
              </li>
            );
          })}
        </ol>
      )}
      {lectureSeule ? <Erreur erreur={erreur} /> : <form className="formulaire conversation-saisie" onSubmit={envoyer}>
        <label>{t("Votre message", "Your message")}
          <textarea value={texte} onChange={(e) => setTexte(e.target.value)} onKeyDown={touche} rows={4} maxLength={4000} />
        </label>
        <div className="actions">
          <button className="principal" disabled={!texte.trim() || enCours}>{t("Envoyer", "Send")}</button>
          <span className="discret">{t("Ctrl+Entrée pour envoyer", "Ctrl+Enter to send")}</span>
        </div>
        <Erreur erreur={erreur} />
      </form>}
    </div>
  );
}

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
 *  défaut, le cabinet) ; le conseiller voit les personnes de l'entreprise. Le fil écrit autrefois sur la plateforme
 *  reste lisible, replié ; on n'y écrit plus. */
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

      <details className="pli section">
        <summary><span>{t("Messages écrits sur la plateforme", "Messages written on the platform")}</span>
          <span className="discret">{t("l'historique, en lecture", "the history, read-only")}</span></summary>
        <div className="pli-corps">
          <Conversation chemin={`/organisations/${d.org.id}/messages`} lectureSeule onLu={d.recharger}
            vide={t("Aucun message écrit ici.", "No message written here.")} />
        </div>
      </details>
    </>
  );
}
