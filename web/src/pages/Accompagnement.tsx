import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { useConfirmation } from "../composants/Confirmer";
import { dateFr } from "../format";
import { t } from "../i18n";
import type { Mandat, Mandats } from "../types";
import { useDossier } from "./Dossier";

// Lu au rendu : la langue peut changer.
const statuts = (): Record<Mandat["statut"], [string, string]> => ({
  demande: [t("Demandé", "Requested"), "attention"], propose: [t("À signer", "To sign"), "attention"], signe: [t("Signé", "Signed"), "bien"],
  refuse: [t("Décliné", "Declined"), "neutre"], retire: [t("Retiré", "Withdrawn"), "neutre"],
});
// Ce que chaque besoin appelle, pour cocher d'avance le périmètre de la proposition.
const MISSIONS: Record<string, string[]> = {
  placement: ["analyse", "consultation", "placement"], mise_en_concurrence: ["consultation", "placement", "renouvellement"],
  prestations: ["gestion"], regime: ["analyse"],
};

/** Demander un accompagnement en courtage ; le conseiller propose le mandat ; l'entreprise le lit et le signe. */
export default function Accompagnement() {
  const d = useDossier();
  const { donnee, erreur, recharger } = useCharge(() => api.get<Mandats>(`/organisations/${d.org.id}/mandats`), []);
  const [demander, fenetre] = useConfirmation();
  if (erreur) return <Erreur erreur={erreur} />;
  if (!donnee) return <p className="discret">{t("Chargement…", "Loading…")}</p>;
  const STATUTS = statuts();
  const courant = donnee.mandats.find((m) => m.statut === "demande" || m.statut === "propose");
  const signe = donnee.mandats.find((m) => m.statut === "signe");
  const passes = donnee.mandats.filter((m) => m !== courant);
  const client = d.role === "admin_client" || d.role === "contributeur_client";
  const fait = () => { recharger(); d.recharger(); };

  function clore(m: Mandat, quoi: "refus" | "retrait") {
    demander({
      titre: quoi === "refus" ? t("Décliner le mandat proposé", "Decline the proposed mandate")
        : m.statut === "demande" ? t("Retirer la demande", "Withdraw the request") : t("Retirer la proposition", "Withdraw the proposal"),
      message: <p>{quoi === "refus" ? t("Votre conseiller en est informé. Vous pourrez demander un accompagnement plus tard.",
          "Your adviser is informed. You can request brokerage support later.")
        : t("La demande est close ; le journal en garde la trace.", "The request is closed; the log keeps a record of it.")}</p>,
      bouton: quoi === "refus" ? t("Décliner", "Decline") : t("Retirer", "Withdraw"),
      action: async () => { await api.post(`/organisations/${d.org.id}/mandats/${m.id}/${quoi}`, {}); fait(); },
    });
  }

  return (
    <>
      {fenetre}
      <h1>{t("Accompagnement en courtage", "Brokerage support")}</h1>
      <p>{t("Un courtier vous représente auprès des assureurs : il analyse votre engagement, consulte le marché, compare les offres, vous recommande la meilleure et suit ensuite le contrat et les départs en retraite. Vous restez seuls à choisir l'assureur. Tout commence par un mandat, que vous lisez et signez ici.",
        "A broker represents you with insurers: they analyse your obligation, consult the market, compare the offers, recommend the best one, and then follow the contract and the retirements. The choice of insurer remains yours alone. It all starts with a mandate, which you read and sign here.")}</p>

      {!courant && donnee.service !== "courtage" && (client
        ? <Demande orgId={d.org.id} besoins={donnee.besoins} onFait={fait} />
        : <p className="carte section discret">{t("Aucune demande d'accompagnement pour l'instant : l'entreprise la fait depuis cette page.", "No request for brokerage support yet: the company makes it from this page.")}</p>)}
      {!courant && donnee.service === "courtage" && signe?.signature && (
        <div className="constat informe section"><div className="titre">{t("Mandat en vigueur", "Mandate in force")}</div>
          {t(`Signé le ${dateFr(signe.signature.le)} par ${signe.signature.nom} · N° ${signe.signature.numero}. Le contrat « courtage » court depuis le ${dateFr(signe.signature.contrat_du)}.`,
            `Signed on ${dateFr(signe.signature.le)} by ${signe.signature.nom} · No. ${signe.signature.numero}. The brokerage contract has run since ${dateFr(signe.signature.contrat_du)}.`)}</div>
      )}
      {!courant && donnee.service === "courtage" && !signe?.signature && (
        <div className="constat informe section"><div className="titre">{t("Vous êtes en courtage", "You are under brokerage")}</div>
          {t("Votre mandat de courtage a été enregistré par votre conseiller : ", "Your brokerage mandate was recorded by your adviser: ")}
          <Link to="../contrat">{t("voir le contrat", "see the contract")}</Link>.</div>
      )}

      {courant && (
        <section className="carte section" aria-labelledby="mandat-courant">
          <div className="actions" style={{ justifyContent: "space-between", marginTop: 0 }}>
            <h2 id="mandat-courant" style={{ margin: 0 }}>{courant.statut === "demande" ? t("Votre demande", "Your request") : t("Le mandat proposé", "The proposed mandate")}</h2>
            <span className={`etat ${STATUTS[courant.statut][1]}`}>{STATUTS[courant.statut][0]}</span>
          </div>
          <p className="discret">{t(`Demandé le ${dateFr(courant.demande_le)} par ${courant.demande_par} :`, `Requested on ${dateFr(courant.demande_le)} by ${courant.demande_par}:`)}{" "}
            {courant.besoins.map((b) => b.libelle.toLowerCase()).join(" ; ")}.</p>
          {courant.message && <blockquote className="citation">{courant.message}</blockquote>}

          {courant.statut === "demande" && d.role !== "conseiller" && (
            <p>{t("Votre conseiller prépare le mandat. Vous le lirez ici avant de le signer.", "Your adviser is preparing the mandate. You will read it here before signing it.")}</p>
          )}
          {d.role === "conseiller" && <Proposer orgId={d.org.id} m={courant} perimetre={donnee.perimetre} onFait={fait} />}
          {courant.proposition && <TexteMandat m={courant} />}
          {courant.statut === "propose" && d.role === "admin_client" && (
            <Signer orgId={d.org.id} m={courant} nom={d.equipe.find((x) => x.moi)?.nom ?? ""} onFait={fait} />
          )}
          {courant.statut === "propose" && d.role === "contributeur_client" && (
            <p className="discret">{t("L'administrateur de l'entreprise signe le mandat.", "The company administrator signs the mandate.")}</p>
          )}
          <div className="actions">
            {courant.statut === "propose" && d.role === "admin_client" &&
              <button type="button" onClick={() => clore(courant, "refus")}>{t("Décliner", "Decline")}</button>}
            {(d.role === "conseiller" || client) &&
              <button type="button" onClick={() => clore(courant, "retrait")}>
                {courant.statut === "demande" ? t("Retirer la demande", "Withdraw the request") : t("Retirer la proposition", "Withdraw the proposal")}</button>}
          </div>
        </section>
      )}

      {passes.length > 0 && (
        <div className="section">
          <h2>{t("Historique", "History")}</h2>
          <div className="defile"><table>
            <thead><tr><th>{t("Demandé le", "Requested on")}</th><th>{t("État", "Status")}</th><th>{t("Détail", "Details")}</th><th aria-label={t("Document", "Document")} /></tr></thead>
            <tbody>{passes.map((m) => (
              <tr key={m.id}><td>{dateFr(m.demande_le)}</td>
                <td><span className={`etat ${STATUTS[m.statut][1]}`}>{STATUTS[m.statut][0]}</span></td>
                <td>{m.signature ? t(`Signé le ${dateFr(m.signature.le)} par ${m.signature.nom} · N° ${m.signature.numero}`, `Signed on ${dateFr(m.signature.le)} by ${m.signature.nom} · No. ${m.signature.numero}`)
                  : m.motif ?? "—"}</td>
                <td className="n">{m.signature?.numero && (
                  <button className="lien" onClick={() => api.ouvrir(`/organisations/${d.org.id}/mandats/${m.id}/pdf`)}>
                    {t("Mandat signé (PDF)", "Signed mandate (PDF)")}</button>)}</td></tr>
            ))}</tbody>
          </table></div>
        </div>
      )}
    </>
  );
}

function Demande({ orgId, besoins, onFait }: { orgId: string; besoins: Mandats["besoins"]; onFait: () => void }) {
  const [erreur, setErreur] = useState<unknown>(null);
  async function envoyer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await api.post(`/organisations/${orgId}/mandats`, {
        besoins: f.getAll("besoins").map(String), message: String(f.get("message") ?? "").trim() || null });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <form className="carte section formulaire" onSubmit={envoyer} aria-labelledby="demande-titre">
      <h2 id="demande-titre" style={{ marginTop: 0 }}>{t("Demander un accompagnement", "Request brokerage support")}</h2>
      <fieldset><legend>{t("Ce que vous attendez", "What you expect")}</legend>
        {besoins.map((b) => (
          <label key={b.code} className="case"><input type="checkbox" name="besoins" value={b.code} /> {b.libelle}</label>
        ))}
      </fieldset>
      <label>{t("Précisions (facultatif)", "Details (optional)")}
        <textarea name="message" rows={3} maxLength={2000} placeholder={t("Échéance de votre contrat actuel, contraintes, questions…", "End date of your current contract, constraints, questions…")} /></label>
      <p className="discret">{t("Votre conseiller vous propose ensuite un mandat de courtage, à lire et signer sur cette page. Rien ne vous engage avant la signature, et l'accompagnement ne vous coûte rien : le courtier est rémunéré par l'assureur retenu.",
        "Your adviser then proposes a brokerage mandate, to read and sign on this page. Nothing binds you before you sign, and the support costs you nothing: the broker is paid by the chosen insurer.")}</p>
      <div className="actions"><button className="principal">{t("Envoyer la demande", "Send the request")}</button></div>
      <Erreur erreur={erreur} />
    </form>
  );
}

function Proposer({ orgId, m, perimetre, onFait }: { orgId: string; m: Mandat; perimetre: Mandats["perimetre"]; onFait: () => void }) {
  const [ouvert, setOuvert] = useState(m.statut === "demande");
  const [erreur, setErreur] = useState<unknown>(null);
  const p = m.proposition;
  const coches = new Set(p?.perimetre ?? m.besoins.flatMap((b) => MISSIONS[b.code] ?? []));
  const dansUnMois = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);
  if (!ouvert) return <div className="actions"><button onClick={() => setOuvert(true)}>{t("Modifier la proposition", "Edit the proposal")}</button></div>;
  async function proposer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await api.put(`/organisations/${orgId}/mandats/${m.id}/proposition`, {
        perimetre: f.getAll("perimetre").map(String), date_effet: f.get("date_effet"),
        duree_mois: Number(f.get("duree_mois")), preavis_mois: Number(f.get("preavis_mois")),
        exclusif: f.get("exclusif") === "oui", conditions: String(f.get("conditions") ?? "").trim() || null });
      setOuvert(false);
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <form className="formulaire section" onSubmit={proposer} aria-label={t("Proposer le mandat", "Propose the mandate")}>
      <h3>{p ? t("Modifier la proposition", "Edit the proposal") : t("Proposer le mandat", "Propose the mandate")}</h3>
      <fieldset><legend>{t("Missions", "Scope of work")}</legend>
        {perimetre.map((x) => (
          <label key={x.code} className="case"><input type="checkbox" name="perimetre" value={x.code} defaultChecked={coches.has(x.code)} />
            {" "}{x.libelle.charAt(0).toUpperCase() + x.libelle.slice(1)}</label>
        ))}
      </fieldset>
      <div className="grille-2">
        <label>{t("Prise d'effet", "Effective date")}<input type="date" name="date_effet" required defaultValue={p?.date_effet ?? dansUnMois} /></label>
        <label>{t("Durée (mois)", "Term (months)")}<input type="number" name="duree_mois" min={1} max={60} required defaultValue={p?.duree_mois ?? 12} /></label>
        <label>{t("Préavis de résiliation (mois)", "Termination notice (months)")}<input type="number" name="preavis_mois" min={1} max={12} required defaultValue={p?.preavis_mois ?? 3} /></label>
        <label>{t("Exclusivité", "Exclusivity")}
          <select name="exclusif" defaultValue={p && !p.exclusif ? "non" : "oui"}>
            <option value="oui">{t("Mandat exclusif", "Exclusive mandate")}</option><option value="non">{t("Non exclusif", "Non-exclusive")}</option>
          </select></label>
      </div>
      <label>{t("Conditions particulières (facultatif)", "Special conditions (optional)")}<textarea name="conditions" rows={2} maxLength={3000} defaultValue={p?.conditions ?? ""} /></label>
      <p className="discret">{t("Le texte du mandat se compose de ces choix ; l'entreprise le lit ici avant de signer.", "The text of the mandate is built from these choices; the company reads it here before signing.")}</p>
      <div className="actions">
        <button className="principal">{p ? t("Mettre à jour la proposition", "Update the proposal") : t("Proposer le mandat", "Propose the mandate")}</button>
        {p && <button type="button" onClick={() => setOuvert(false)}>{t("Annuler", "Cancel")}</button>}
      </div>
      <Erreur erreur={erreur} />
    </form>
  );
}

function TexteMandat({ m }: { m: Mandat }) {
  const p = m.proposition!;
  return (
    <article className="texte-mandat section" aria-label={t("Texte du mandat", "Text of the mandate")}>
      <p className="discret">{t(`Proposé le ${dateFr(p.propose_le)} par ${p.propose_par} · prise d'effet le ${dateFr(p.date_effet)} · ${p.duree_mois} mois · préavis ${p.preavis_mois} mois · ${p.exclusif ? "exclusif" : "non exclusif"}`,
        `Proposed on ${dateFr(p.propose_le)} by ${p.propose_par} · effective ${dateFr(p.date_effet)} · ${p.duree_mois} months · ${p.preavis_mois} months' notice · ${p.exclusif ? "exclusive" : "non-exclusive"}`)}</p>
      {p.texte.articles.map((a) => (
        <section key={a.numero}>
          <h3>{t("Article", "Article")} {a.numero} — {a.titre}</h3>
          {a.paragraphes.map((x, i) => <p key={i}>{x}</p>)}
        </section>
      ))}
    </article>
  );
}

function Signer({ orgId, m, nom, onFait }: { orgId: string; m: Mandat; nom: string; onFait: () => void }) {
  const [accepte, setAccepte] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  async function signer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await api.post(`/organisations/${orgId}/mandats/${m.id}/signature`, {
        nom: String(f.get("nom") ?? ""), fonction: String(f.get("fonction") ?? "").trim() || null,
        empreinte: m.proposition!.empreinte, accepte });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <form className="formulaire signature section" onSubmit={signer} aria-label={t("Signer le mandat", "Sign the mandate")}>
      <h3>{t("Signer", "Sign")}</h3>
      <div className="grille-2">
        <label>{t("Nom et prénom", "Full name")}<input name="nom" required minLength={3} defaultValue={nom} autoComplete="name" /></label>
        <label>{t("Fonction", "Job title")}<input name="fonction" placeholder={t("DG, DRH, DAF…", "CEO, HR director, CFO…")} /></label>
      </div>
      <label className="case"><input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)} />
        {" "}{t("J'ai lu ce mandat et je l'accepte au nom de l'entreprise.", "I have read this mandate and accept it on behalf of the company.")}</label>
      <p className="discret">{t("La signature porte sur le texte ci-dessus, tel qu'il est affiché. Le mandat signé est scellé, vérifiable par son numéro, et le contrat « courtage » prend effet à sa date.",
        "The signature covers the text above, exactly as displayed. The signed mandate is sealed, verifiable by its number, and the brokerage contract takes effect on its date.")}</p>
      <div className="actions"><button className="principal" disabled={!accepte}>{t("Signer le mandat", "Sign the mandate")}</button></div>
      <Erreur erreur={erreur} />
    </form>
  );
}
