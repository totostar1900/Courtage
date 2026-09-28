import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { api } from "../api";
import type { Fil } from "../activation";
import { Erreur } from "../composants/communs";
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
export function Conversation({ chemin, vide, onLu }: { chemin: string; vide: string; onLu?: () => void }) {
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
      <form className="formulaire conversation-saisie" onSubmit={envoyer}>
        <label>{t("Votre message", "Your message")}
          <textarea value={texte} onChange={(e) => setTexte(e.target.value)} onKeyDown={touche} rows={4} maxLength={4000} />
        </label>
        <div className="actions">
          <button className="principal" disabled={!texte.trim() || enCours}>{t("Envoyer", "Send")}</button>
          <span className="discret">{t("Ctrl+Entrée pour envoyer", "Ctrl+Enter to send")}</span>
        </div>
        <Erreur erreur={erreur} />
      </form>
    </div>
  );
}

/** Le fil entre l'entreprise et son conseiller. Tous les membres du dossier le lisent et y écrivent, y compris en
 *  lecture seule. Après la lecture, le dossier se relit : le compteur du rail tombe à zéro. */
export default function Messages() {
  const d = useDossier();
  return (
    <>
      <h1>{t("Messages", "Messages")}</h1>
      <p className="discret">{t("Un fil par dossier, entre l'entreprise et son conseiller.",
        "One thread per file, between the company and its adviser.")}</p>
      <section className="carte">
        <Conversation chemin={`/organisations/${d.org.id}/messages`}
          vide={t("Votre conseiller vous répond ici ; tant que votre inscription attend, c'est le courtier qui lit.",
                  "Your adviser answers here; while your sign-up is pending, the broker reads it.")}
          onLu={d.recharger} />
      </section>
    </>
  );
}
