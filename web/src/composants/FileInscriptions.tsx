import { useState, type FormEvent } from "react";

import { api } from "../api";
import type { Inscription } from "../activation";
import { dateFr } from "../format";
import { t } from "../i18n";
import { Conversation } from "../pages/Messages";
import { Erreur, Tiroir, useCharge, Volet } from "./communs";

type Piece = { id: string; nom_fichier: string; depose_le: string };
type Ligne = Inscription & { justificatifs?: Piece[] };
interface FileAttente { inscriptions: Ligne[]; delai_jours_ouvres: number }
type Ouvert = { ins: Ligne; acte: "confirmer" | "refuser" | "ecrire" };

const tailles = (): Record<string, string> => ({
  moins_de_50: t("moins de 50 salariés", "fewer than 50 employees"),
  "50_a_250": t("50 à 250 salariés", "50 to 250 employees"),
  plus_de_250: t("plus de 250 salariés", "more than 250 employees"),
});

const aujourdhui = () => new Date().toISOString().slice(0, 10);

/** La file du courtier : les inscriptions à confirmer, la plus ancienne d'abord. Chaque carte dit qui a demandé,
 *  quand, l'échéance (en rouge une fois dépassée) et ce qui a été déposé ; confirmer, refuser et écrire s'ouvrent
 *  dans un tiroir. `onDecision` : une confirmation ajoute le dossier à ceux que le courtier conseille. */
export default function FileInscriptions({ onDecision }: { onDecision?: () => void }) {
  const { donnee, erreur, recharger } = useCharge(() => api.get<FileAttente>("/inscriptions"), []);
  const [ouvert, setOuvert] = useState<Ouvert | null>(null);
  const [erreurPiece, setErreurPiece] = useState<unknown>(null);

  function fermer() {
    const relire = ouvert?.acte === "ecrire";     // les messages de l'entreprise viennent d'être lus
    setOuvert(null);
    if (relire) recharger();
  }
  function decide() {
    setOuvert(null);
    recharger();
    onDecision?.();
  }
  async function voir(org: string, piece: Piece) {
    setErreurPiece(null);
    try { await api.ouvrir(`/inscriptions/${org}/justificatifs/${piece.id}`); } catch (e) { setErreurPiece(e); }
  }

  const TAILLES = tailles();
  return (
    <section className="section file-inscriptions" aria-label={t("Inscriptions à confirmer", "Sign-ups to confirm")}>
      <h2>{t("Inscriptions à confirmer", "Sign-ups to confirm")}
        {!!donnee?.inscriptions.length && <span className="discret"> · {donnee.inscriptions.length}</span>}</h2>
      {donnee && (
        <p className="discret">{t(`Chaque inscription reçoit un appel sous ${donnee.delai_jours_ouvres} jours ouvrés (samedi et dimanche exclus).`,
          `Each sign-up gets a call within ${donnee.delai_jours_ouvres} working days (Saturday and Sunday excluded).`)}</p>
      )}
      <Erreur erreur={erreur} />
      <Erreur erreur={erreurPiece} />
      {donnee && donnee.inscriptions.length === 0 && (
        <p className="discret">{t("Aucune inscription en attente.", "No pending sign-ups.")}</p>
      )}
      <div className="grille g3">
        {donnee?.inscriptions.map((i) => (
          <article key={i.id} className={`carte inscription${i.en_retard ? " en-retard" : ""}`} aria-label={i.nom}>
            <h3 style={{ margin: "0 0 4px" }}>{i.nom}</h3>
            <div className="discret">{[i.secteur, i.ville, i.pays].filter(Boolean).join(" · ")}</div>
            <dl className="inscription-faits">
              <dt>{t("RCCM", "Trade register (RCCM)")}</dt><dd>{i.rccm}</dd>
              <dt>{t("Taille", "Size")}</dt><dd>{TAILLES[i.taille] ?? i.taille}</dd>
              {i.adresse && <><dt>{t("Adresse", "Address")}</dt><dd>{i.adresse}</dd></>}
              <dt>{t("Demandeur", "Applicant")}</dt>
              <dd>
                {i.demandeur ? (
                  <>
                    {i.demandeur.nom ?? "—"}{i.demandeur.fonction && <span className="discret"> · {i.demandeur.fonction}</span>}
                    {i.demandeur.telephone && <div><a href={`tel:${i.demandeur.telephone}`}>{i.demandeur.telephone}</a></div>}
                    {i.demandeur.courriel && <div><a href={`mailto:${i.demandeur.courriel}`}>{i.demandeur.courriel}</a></div>}
                  </>
                ) : "—"}
              </dd>
              <dt>{t("Demandée le", "Requested on")}</dt><dd>{dateFr(i.demandee_le)}</dd>
              <dt>{t("Échéance", "Deadline")}</dt>
              <dd>
                <span className={i.en_retard ? "echeance-retard" : undefined}>{dateFr(i.echeance)}</span>
                {i.en_retard && <> <span className="etat grave">{t("en retard", "overdue")}</span></>}
              </dd>
              <dt>{t("Document RCCM", "RCCM document")}</dt>
              <dd>
                {i.rccm_depose ? t("déposé", "uploaded") : t("non déposé", "not uploaded")}
                {i.justificatifs?.map((p) => (
                  <div key={p.id}>
                    <button type="button" className="lien" onClick={() => voir(i.id, p)}>
                      {t(`Ouvrir ${p.nom_fichier}`, `Open ${p.nom_fichier}`)}</button>
                  </div>
                ))}
              </dd>
              <dt>{t("Messages", "Messages")}</dt>
              <dd>{i.messages_non_lus > 0
                ? <span className="etat attention">{t(`${i.messages_non_lus} non lu(s)`, `${i.messages_non_lus} unread`)}</span>
                : t("aucun non lu", "none unread")}</dd>
            </dl>
            <div className="discret">{t(`Effacée le ${dateFr(i.expire_le)} si elle n'est pas confirmée.`,
              `Deleted on ${dateFr(i.expire_le)} if not confirmed.`)}</div>
            <div className="actions">
              <button type="button" className="principal" onClick={() => setOuvert({ ins: i, acte: "confirmer" })}>
                {t("Confirmer", "Confirm")}</button>
              <button type="button" onClick={() => setOuvert({ ins: i, acte: "refuser" })}>{t("Refuser", "Refuse")}</button>
              <button type="button" onClick={() => setOuvert({ ins: i, acte: "ecrire" })}>{t("Écrire", "Write")}</button>
            </div>
          </article>
        ))}
      </div>
      {ouvert && (
        <Tiroir onFermer={fermer} etiquette={ouvert.ins.nom}>
          {ouvert.acte === "confirmer" && <Confirmer ins={ouvert.ins} onFermer={fermer} onFait={decide} />}
          {ouvert.acte === "refuser" && <Refuser ins={ouvert.ins} onFermer={fermer} onFait={decide} />}
          {ouvert.acte === "ecrire" && (
            <Volet titre={t(`Écrire à ${ouvert.ins.nom}`, `Write to ${ouvert.ins.nom}`)} onFermer={fermer}>
              <Conversation chemin={`/inscriptions/${ouvert.ins.id}/messages`}
                vide={t("Aucun message pour l'instant. L'entreprise lit ce fil dans son dossier, à « Messages ».",
                        "No messages yet. The company reads this thread in its file, under “Messages”.")} />
            </Volet>
          )}
        </Tiroir>
      )}
    </section>
  );
}

interface Acte { ins: Ligne; onFermer: () => void; onFait: () => void }

function Confirmer({ ins, onFermer, onFait }: Acte) {
  const [erreur, setErreur] = useState<unknown>(null);
  const [enCours, setEnCours] = useState(false);
  async function envoyer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const texte = (cle: string) => String(f.get(cle) ?? "").trim() || null;
    const verification = {
      rccm_recu: f.get("rccm_recu") === "on",
      ...(texte("appel_le") ? { appel_le: texte("appel_le") } : {}),
      habilitation: texte("habilitation"),
      note: texte("note"),
    };
    setErreur(null);
    setEnCours(true);
    try {
      await api.post(`/inscriptions/${ins.id}/decision`, { decision: "confirmer", verification });
      onFait();
    } catch (e) {
      setErreur(e);
      setEnCours(false);
    }
  }
  return (
    <Volet titre={t(`Confirmer ${ins.nom}`, `Confirm ${ins.nom}`)} onFermer={onFermer}>
      <form className="formulaire" onSubmit={envoyer}>
        <p className="discret">{t("Ce qui a été vérifié est tracé avec la décision. En confirmant, vous devenez le conseiller du dossier.",
          "What was checked is recorded with the decision. By confirming, you become the file's adviser.")}</p>
        <label className="case">
          <input type="checkbox" name="rccm_recu" defaultChecked={ins.rccm_depose} />
          {t(`RCCM reçu et conforme (${ins.rccm})`, `RCCM received and matching (${ins.rccm})`)}
        </label>
        <label>{t("Date de l'appel", "Date of the call")}
          <input type="date" name="appel_le" defaultValue={aujourdhui()} />
        </label>
        <label>{t("Personne jointe, et à quel titre", "Person reached, and in what capacity")}
          <input name="habilitation" maxLength={300}
            placeholder={t("ex. Mme Ngo, DRH, habilitée par le DG", "e.g. Ms Ngo, HR director, authorised by the CEO")} />
        </label>
        <label>{t("Note", "Note")}
          <textarea name="note" rows={3} maxLength={2000} />
        </label>
        <div className="actions">
          <button className="principal" disabled={enCours}>{t("Confirmer l'inscription", "Confirm the sign-up")}</button>
          <button type="button" onClick={onFermer}>{t("Annuler", "Cancel")}</button>
        </div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}

function Refuser({ ins, onFermer, onFait }: Acte) {
  const [motif, setMotif] = useState("");
  const [erreur, setErreur] = useState<unknown>(null);
  const [enCours, setEnCours] = useState(false);
  async function envoyer(ev: FormEvent) {
    ev.preventDefault();
    if (!motif.trim()) return;
    setErreur(null);
    setEnCours(true);
    try {
      await api.post(`/inscriptions/${ins.id}/decision`, { decision: "refuser", motif: motif.trim() });
      onFait();
    } catch (e) {
      setErreur(e);
      setEnCours(false);
    }
  }
  return (
    <Volet titre={t(`Refuser ${ins.nom}`, `Refuse ${ins.nom}`)} onFermer={onFermer}>
      <form className="formulaire" onSubmit={envoyer}>
        <label>{t("Motif du refus (lu par l'entreprise)", "Reason for refusal (shown to the company)")}
          <textarea value={motif} onChange={(e) => setMotif(e.target.value)} rows={4} maxLength={1000} required />
        </label>
        <div className="actions">
          <button className="danger" disabled={!motif.trim() || enCours}>{t("Refuser l'inscription", "Refuse the sign-up")}</button>
          <button type="button" onClick={onFermer}>{t("Annuler", "Cancel")}</button>
        </div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
