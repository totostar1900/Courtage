import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { useConfirmation } from "../composants/Confirmer";
import { dateFr } from "../format";
import type { Mandat, Mandats } from "../types";
import { useDossier } from "./Dossier";

const STATUTS: Record<Mandat["statut"], [string, string]> = {
  demande: ["Demandé", "attention"], propose: ["À signer", "attention"], signe: ["Signé", "bien"],
  refuse: ["Décliné", "neutre"], retire: ["Retiré", "neutre"],
};
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
  if (!donnee) return <p className="discret">Chargement…</p>;
  const courant = donnee.mandats.find((m) => m.statut === "demande" || m.statut === "propose");
  const signe = donnee.mandats.find((m) => m.statut === "signe");
  const passes = donnee.mandats.filter((m) => m !== courant);
  const client = d.role === "admin_client" || d.role === "contributeur_client";
  const fait = () => { recharger(); d.recharger(); };

  function clore(m: Mandat, quoi: "refus" | "retrait") {
    demander({
      titre: quoi === "refus" ? "Décliner le mandat proposé" : m.statut === "demande" ? "Retirer la demande" : "Retirer la proposition",
      message: <p>{quoi === "refus" ? "Votre conseiller en est informé. Vous pourrez demander un accompagnement plus tard."
        : "La demande est close ; le journal en garde la trace."}</p>,
      bouton: quoi === "refus" ? "Décliner" : "Retirer",
      action: async () => { await api.post(`/organisations/${d.org.id}/mandats/${m.id}/${quoi}`, {}); fait(); },
    });
  }

  return (
    <>
      {fenetre}
      <h1>Accompagnement en courtage</h1>
      <p>Un courtier vous représente auprès des assureurs : il analyse votre engagement, consulte le marché, compare les
        offres, vous recommande la meilleure et suit ensuite le contrat et les départs en retraite. Vous restez seuls
        à choisir l'assureur. Tout commence par un mandat, que vous lisez et signez ici.</p>

      {!courant && donnee.service !== "courtage" && (client
        ? <Demande orgId={d.org.id} besoins={donnee.besoins} onFait={fait} />
        : <p className="carte section discret">Aucune demande d'accompagnement pour l'instant : l'entreprise la fait depuis cette page.</p>)}
      {!courant && donnee.service === "courtage" && signe?.signature && (
        <div className="constat informe section"><div className="titre">Mandat en vigueur</div>
          Signé le {dateFr(signe.signature.le)} par {signe.signature.nom} · N° {signe.signature.numero}. Le contrat
          « courtage » court depuis le {dateFr(signe.signature.contrat_du)}.</div>
      )}

      {courant && (
        <section className="carte section" aria-labelledby="mandat-courant">
          <div className="actions" style={{ justifyContent: "space-between", marginTop: 0 }}>
            <h2 id="mandat-courant" style={{ margin: 0 }}>{courant.statut === "demande" ? "Votre demande" : "Le mandat proposé"}</h2>
            <span className={`etat ${STATUTS[courant.statut][1]}`}>{STATUTS[courant.statut][0]}</span>
          </div>
          <p className="discret">Demandé le {dateFr(courant.demande_le)} par {courant.demande_par} :{" "}
            {courant.besoins.map((b) => b.libelle.toLowerCase()).join(" ; ")}.</p>
          {courant.message && <blockquote className="citation">{courant.message}</blockquote>}

          {courant.statut === "demande" && d.role !== "conseiller" && (
            <p>Votre conseiller prépare le mandat. Vous le lirez ici avant de le signer.</p>
          )}
          {d.role === "conseiller" && <Proposer orgId={d.org.id} m={courant} perimetre={donnee.perimetre} onFait={fait} />}
          {courant.proposition && <TexteMandat m={courant} />}
          {courant.statut === "propose" && d.role === "admin_client" && (
            <Signer orgId={d.org.id} m={courant} nom={d.equipe.find((x) => x.moi)?.nom ?? ""} onFait={fait} />
          )}
          {courant.statut === "propose" && d.role === "contributeur_client" && (
            <p className="discret">L'administrateur de l'entreprise signe le mandat.</p>
          )}
          <div className="actions">
            {courant.statut === "propose" && d.role === "admin_client" &&
              <button type="button" onClick={() => clore(courant, "refus")}>Décliner</button>}
            {(d.role === "conseiller" || client) &&
              <button type="button" onClick={() => clore(courant, "retrait")}>
                {courant.statut === "demande" ? "Retirer la demande" : "Retirer la proposition"}</button>}
          </div>
        </section>
      )}

      {passes.length > 0 && (
        <div className="section">
          <h2>Historique</h2>
          <div className="defile"><table>
            <thead><tr><th>Demandé le</th><th>État</th><th>Détail</th><th aria-label="Document" /></tr></thead>
            <tbody>{passes.map((m) => (
              <tr key={m.id}><td>{dateFr(m.demande_le)}</td>
                <td><span className={`etat ${STATUTS[m.statut][1]}`}>{STATUTS[m.statut][0]}</span></td>
                <td>{m.signature ? `Signé le ${dateFr(m.signature.le)} par ${m.signature.nom} · N° ${m.signature.numero}`
                  : m.motif ?? "—"}</td>
                <td className="n">{m.signature?.numero && (
                  <button className="lien" onClick={() => api.ouvrir(`/organisations/${d.org.id}/mandats/${m.id}/pdf`)}>
                    Mandat signé (PDF)</button>)}</td></tr>
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
      <h2 id="demande-titre" style={{ marginTop: 0 }}>Demander un accompagnement</h2>
      <fieldset><legend>Ce que vous attendez</legend>
        {besoins.map((b) => (
          <label key={b.code} className="case"><input type="checkbox" name="besoins" value={b.code} /> {b.libelle}</label>
        ))}
      </fieldset>
      <label>Précisions (facultatif)
        <textarea name="message" rows={3} maxLength={2000} placeholder="Échéance de votre contrat actuel, contraintes, questions…" /></label>
      <p className="discret">Votre conseiller vous propose ensuite un mandat de courtage, à lire et signer sur cette page.
        Rien ne vous engage avant la signature.</p>
      <div className="actions"><button className="principal">Envoyer la demande</button></div>
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
  if (!ouvert) return <div className="actions"><button onClick={() => setOuvert(true)}>Modifier la proposition</button></div>;
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
    <form className="formulaire section" onSubmit={proposer} aria-label="Proposer le mandat">
      <h3>{p ? "Modifier la proposition" : "Proposer le mandat"}</h3>
      <fieldset><legend>Missions</legend>
        {perimetre.map((x) => (
          <label key={x.code} className="case"><input type="checkbox" name="perimetre" value={x.code} defaultChecked={coches.has(x.code)} />
            {" "}{x.libelle.charAt(0).toUpperCase() + x.libelle.slice(1)}</label>
        ))}
      </fieldset>
      <div className="grille-2">
        <label>Prise d'effet<input type="date" name="date_effet" required defaultValue={p?.date_effet ?? dansUnMois} /></label>
        <label>Durée (mois)<input type="number" name="duree_mois" min={1} max={60} required defaultValue={p?.duree_mois ?? 12} /></label>
        <label>Préavis de résiliation (mois)<input type="number" name="preavis_mois" min={1} max={12} required defaultValue={p?.preavis_mois ?? 3} /></label>
        <label>Exclusivité
          <select name="exclusif" defaultValue={p && !p.exclusif ? "non" : "oui"}>
            <option value="oui">Mandat exclusif</option><option value="non">Non exclusif</option>
          </select></label>
      </div>
      <label>Conditions particulières (facultatif)<textarea name="conditions" rows={2} maxLength={3000} defaultValue={p?.conditions ?? ""} /></label>
      <p className="discret">Le texte du mandat se compose de ces choix ; l'entreprise le lit ici avant de signer.</p>
      <div className="actions">
        <button className="principal">{p ? "Mettre à jour la proposition" : "Proposer le mandat"}</button>
        {p && <button type="button" onClick={() => setOuvert(false)}>Annuler</button>}
      </div>
      <Erreur erreur={erreur} />
    </form>
  );
}

function TexteMandat({ m }: { m: Mandat }) {
  const p = m.proposition!;
  return (
    <article className="texte-mandat section" aria-label="Texte du mandat">
      <p className="discret">Proposé le {dateFr(p.propose_le)} par {p.propose_par} · prise d'effet le {dateFr(p.date_effet)} ·{" "}
        {p.duree_mois} mois · préavis {p.preavis_mois} mois · {p.exclusif ? "exclusif" : "non exclusif"}</p>
      {p.texte.articles.map((a) => (
        <section key={a.numero}>
          <h3>Article {a.numero} — {a.titre}</h3>
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
    <form className="formulaire signature section" onSubmit={signer} aria-label="Signer le mandat">
      <h3>Signer</h3>
      <div className="grille-2">
        <label>Nom et prénom<input name="nom" required minLength={3} defaultValue={nom} autoComplete="name" /></label>
        <label>Fonction<input name="fonction" placeholder="DG, DRH, DAF…" /></label>
      </div>
      <label className="case"><input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)} />
        {" "}J'ai lu ce mandat et je l'accepte au nom de l'entreprise.</label>
      <p className="discret">La signature porte sur le texte ci-dessus, tel qu'il est affiché. Le mandat signé est scellé,
        vérifiable par son numéro, et le contrat « courtage » prend effet à sa date.</p>
      <div className="actions"><button className="principal" disabled={!accepte}>Signer le mandat</button></div>
      <Erreur erreur={erreur} />
    </form>
  );
}
