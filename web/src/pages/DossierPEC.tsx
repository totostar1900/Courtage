import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { Constats, Erreur, useCharge, Volet } from "../composants/communs";
import { dateFr, montant } from "../format";
import type { Beneficiaire, DossierPEC, EtapeDossier, Prestation } from "../types";
import { useDossier } from "./Dossier";

export const ETAPES: Record<EtapeDossier, string> = {
  declare: "Déclaré", a_completer: "À compléter", resoumis: "Resoumis", verifie: "Vérifié", transmis: "Transmis",
  paye: "Payé", refuse: "Refusé", identite_effacee: "Identité effacée",
};
const CLASSE: Record<string, string> = { paye: "bien", refuse: "grave", a_completer: "attention", transmis: "neutre" };
const NATURES: Record<string, string> = {
  certificat_travail: "Certificat de travail", attestation_depart: "Attestation de départ",
  calcul_signe: "Calcul de l'indemnité signé", piece_identite: "Pièce d'identité", rib: "Relevé d'identité bancaire",
  autre: "Autre pièce", dossier_scelle: "Dossier scellé transmis",
};
const PIECES_D_IDENTITE = { cni: "Carte nationale d'identité", passeport: "Passeport", carte_sejour: "Carte de séjour", autre: "Autre" };
const PAIEMENTS = { virement: "Virement", mobile_money: "Mobile money", cheque: "Chèque" };

export function EtatDossier({ statut }: { statut: string }) {
  return <span className={`etat ${CLASSE[statut] ?? "neutre"}`}>{ETAPES[statut as EtapeDossier] ?? statut}</span>;
}

/** Courtage : le dossier de prise en charge d'un départ, de la déclaration au paiement. */
export default function DossierPriseEnCharge() {
  const d = useDossier();
  const { id } = useParams();
  const url = `/organisations/${d.org.id}/dossiers/${id}`;
  const { donnee: x, erreur, recharger } = useCharge(() => api.get<DossierPEC>(url), [id]);
  const [erreurAction, setErreurAction] = useState<unknown>(null);
  if (erreur) return <Erreur erreur={erreur} />;
  if (!x) return <p className="discret">Chargement…</p>;

  async function agir(action: string, corps: object = {}) {
    setErreurAction(null);
    try { await api.post(`${url}/${action}`, corps); recharger(); } catch (e) { setErreurAction(e); }
  }
  const conseiller = d.role === "conseiller", entreprise = d.role === "admin_client";
  const ouvert = x.statut !== "paye" && !x.identite_effacee;

  return (
    <>
      <p><Link to="../departs">← Départs</Link></p>
      <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>Prise en charge · matricule {x.matricule}</h1>
        <EtatDossier statut={x.statut} />
      </div>
      <p className="discret">Départ du {dateFr(x.date_depart)} · {montant(x.montant_demande)} demandés à {x.assureur}
        {x.numero_police && ` (police ${x.numero_police})`} · mandat : {x.mandat_reference}</p>
      <Constats constats={x.constats} vide="" />

      <div className="grille g2 section">
        <div className="carte">
          <h2>Étapes</h2>
          <ol className="etapes-dossier">
            {x.evenements.map((e, i) => (
              <li key={i}><strong>{ETAPES[e.etape]}</strong> <span className="discret">le {dateFr(e.le)}</span>
                {e.montant !== null && <> · {montant(e.montant)}</>}
                {e.numero && <> · <Link to={`/verifier/${e.numero}`}>{e.numero}</Link></>}
                {e.motif && <div className="discret">« {e.motif} »</div>}</li>
            ))}
          </ol>
          {x.efface_le && <p className="discret">L'identité du bénéficiaire et les pièces seront effacées le {dateFr(x.efface_le)}.</p>}
          {x.identite_effacee && <p className="discret">Identité et pièces effacées, comme prévu douze mois après le paiement.
            Le numéro du dossier se vérifie toujours.</p>}
        </div>
        <div className="carte">
          <h2>Bénéficiaire</h2>
          {x.beneficiaire ? <FicheBeneficiaire b={x.beneficiaire} /> :
            <p className="discret">{x.identite_effacee ? "Effacée." : "Visible par l'entreprise et son conseiller seulement."}</p>}
        </div>
      </div>

      {(entreprise || conseiller) && (
        <div className="carte section">
          <h2>Pièces</h2>
          {x.pieces.length === 0 ? <p className="discret">Aucune pièce.</p> : (
            <table><tbody>{x.pieces.map((p) => (
              <tr key={p.id}><td>{NATURES[p.nature] ?? p.nature}</td><td>{p.nom_fichier}</td>
                <td className="n discret">{Math.ceil(p.taille / 1024)} Ko</td>
                <td className="n"><button className="lien" onClick={() => api.ouvrir(p.nature === "dossier_scelle"
                  ? `${url}/document` : `${url}/pieces/${p.id}`)}>Ouvrir</button></td></tr>
            ))}</tbody></table>
          )}
          {ouvert && <AjoutPiece url={url} onFait={recharger} />}
        </div>
      )}

      <div className="section">
        {conseiller && (x.statut === "declare" || x.statut === "resoumis") && <Verifier agir={agir} />}
        {entreprise && x.statut === "a_completer" && (
          <div className="carte"><p>Votre conseiller attend un complément (voir les étapes). Ajoutez les pièces, puis :</p>
            <button className="principal" onClick={() => agir("resoumission")}>Resoumettre le dossier</button></div>
        )}
        {conseiller && (x.statut === "verifie" || x.statut === "refuse") && <Transmettre agir={agir} refuse={x.statut === "refuse"} />}
        {conseiller && x.statut === "transmis" && <Repondre agir={agir} montantDemande={x.montant_demande} />}
        {!conseiller && ["declare", "resoumis", "verifie", "transmis"].includes(x.statut) && (
          <p className="discret">{x.statut === "transmis" ? "L'assureur a le dossier : votre conseiller suit le paiement."
            : "Votre conseiller vérifie le dossier puis le transmet à l'assureur."}</p>
        )}
        <Erreur erreur={erreurAction} />
      </div>
    </>
  );
}

function FicheBeneficiaire({ b }: { b: Beneficiaire }) {
  return (
    <div className="lignes-offre">
      <div><span>Qualité</span><span>{b.qualite === "salarie" ? "Le salarié" : "Ayant droit"}</span></div>
      <div><span>Nom et prénoms</span><strong>{b.nom} {b.prenoms}</strong></div>
      {b.date_naissance && <div><span>Né(e) le</span><span>{dateFr(b.date_naissance)}</span></div>}
      <div><span>{PIECES_D_IDENTITE[b.piece_type]}</span><span>{b.piece_numero}</span></div>
      {b.telephone && <div><span>Téléphone</span><span>{b.telephone}</span></div>}
      <div><span>{PAIEMENTS[b.moyen_paiement]}</span><span>{b.coordonnees_paiement ?? "—"}</span></div>
    </div>
  );
}

function AjoutPiece({ url, onFait }: { url: string; onFait: () => void }) {
  const [erreur, setErreur] = useState<unknown>(null);
  async function envoyer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try { await api.post(`${url}/pieces`, f); ev.currentTarget?.reset(); onFait(); } catch (e) { setErreur(e); }
  }
  return (
    <form className="actions" onSubmit={envoyer} style={{ alignItems: "end" }}>
      <label>Nature<select name="nature">{Object.entries(NATURES).filter(([k]) => k !== "dossier_scelle")
        .map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
      <label>Fichier (PDF, JPEG, PNG · 5 Mo)<input name="fichier" type="file" accept=".pdf,.jpg,.jpeg,.png" required /></label>
      <button>Ajouter la pièce</button>
      <Erreur erreur={erreur} />
    </form>
  );
}

function Verifier({ agir }: { agir: (a: string, c?: object) => void }) {
  const [motif, setMotif] = useState("");
  return (
    <div className="carte">
      <h3>Vérifier le dossier</h3>
      <div className="actions">
        <button className="principal" onClick={() => agir("verification", { conforme: true })}>Dossier complet</button>
        <input aria-label="Ce qui manque" placeholder="Ce qui manque…" value={motif} onChange={(e) => setMotif(e.target.value)} />
        <button disabled={!motif.trim()} onClick={() => agir("verification", { conforme: false, motif })}>À compléter</button>
      </div>
    </div>
  );
}

function Transmettre({ agir, refuse }: { agir: (a: string, c?: object) => void; refuse: boolean }) {
  const [le, setLe] = useState(new Date().toISOString().slice(0, 10));
  return (
    <div className="carte">
      <h3>{refuse ? "Contester et transmettre à nouveau" : "Sceller et transmettre"}</h3>
      <p className="discret">La plateforme scelle le dossier (numéro PC-…) ; vous l'envoyez à l'assureur et notez la date d'envoi.
        Le sceau public ne porte aucune donnée personnelle.</p>
      <div className="actions">
        <label>Envoyé le<input type="date" value={le} onChange={(e) => setLe(e.target.value)} /></label>
        <button className="principal" onClick={() => agir("transmission", { le })}>Sceller et noter l'envoi</button>
      </div>
    </div>
  );
}

function Repondre({ agir, montantDemande }: { agir: (a: string, c?: object) => void; montantDemande: number }) {
  const [paye, setPaye] = useState(true);
  const [montantPaye, setMontant] = useState(String(montantDemande));
  const [le, setLe] = useState(new Date().toISOString().slice(0, 10));
  const [motif, setMotif] = useState("");
  return (
    <div className="carte">
      <h3>Réponse de l'assureur</h3>
      <div className="actions">
        <label><input type="radio" checked={paye} onChange={() => setPaye(true)} /> Payé</label>
        <label><input type="radio" checked={!paye} onChange={() => setPaye(false)} /> Refusé</label>
      </div>
      <div className="grille g3">
        <label>Le<input type="date" value={le} onChange={(e) => setLe(e.target.value)} /></label>
        {paye ? <label>Montant payé (F)<input type="number" min={1} value={montantPaye} onChange={(e) => setMontant(e.target.value)} /></label>
          : <label>Motif du refus<input value={motif} onChange={(e) => setMotif(e.target.value)} /></label>}
      </div>
      <div className="actions">
        <button className="principal" onClick={() => agir("reponse", paye ? { paye, montant: Number(montantPaye), le } : { paye, motif, le })}>
          Enregistrer la réponse</button>
      </div>
    </div>
  );
}

// --- Ouvrir un dossier depuis un départ -----------------------------------------------

export function DemandePriseEnCharge({ p, onFermer }: { p: Prestation; onFermer: () => void }) {
  const d = useDossier();
  const naviguer = useNavigate();
  const [erreur, setErreur] = useState<unknown>(null);
  async function ouvrir(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const t = (k: string) => String(f.get(k) ?? "").trim() || null;
    setErreur(null);
    try {
      const x = await api.post<DossierPEC>(`/organisations/${d.org.id}/dossiers`, {
        prestation_id: p.id, montant_demande: Number(f.get("montant_demande")),
        beneficiaire: { qualite: f.get("qualite"), nom: t("nom"), prenoms: t("prenoms"), date_naissance: t("date_naissance"),
          piece_type: f.get("piece_type"), piece_numero: t("piece_numero"), telephone: t("telephone"),
          moyen_paiement: f.get("moyen_paiement"), coordonnees_paiement: t("coordonnees_paiement") } });
      naviguer(`../dossiers/${x.id}`);
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre={`Demander la prise en charge · matricule ${p.matricule}`} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={ouvrir}>
        <p className="discret">Vous êtes en courtage : nous portons la demande auprès de l'assureur. L'identité du bénéficiaire
          sert à ce seul paiement ; elle reste dans ce dossier, n'entre dans aucun rapport, et est effacée douze mois après
          le paiement.</p>
        <div className="grille g3">
          <label>Montant demandé au fonds (F)<input name="montant_demande" type="number" min={1} required
                 defaultValue={p.verse ?? p.du} /></label>
          <label>Le bénéficiaire est<select name="qualite"><option value="salarie">le salarié</option>
            <option value="ayant_droit">un ayant droit</option></select></label>
          <span />
          <label>Nom<input name="nom" required autoComplete="off" /></label>
          <label>Prénoms<input name="prenoms" autoComplete="off" /></label>
          <label>Date de naissance<input name="date_naissance" type="date" /></label>
          <label>Pièce d'identité<select name="piece_type">{Object.entries(PIECES_D_IDENTITE).map(([k, l]) =>
            <option key={k} value={k}>{l}</option>)}</select></label>
          <label>Numéro de la pièce<input name="piece_numero" required autoComplete="off" /></label>
          <label>Téléphone<input name="telephone" type="tel" autoComplete="off" /></label>
          <label>Paiement par<select name="moyen_paiement">{Object.entries(PAIEMENTS).map(([k, l]) =>
            <option key={k} value={k}>{l}</option>)}</select></label>
          <label>IBAN ou numéro mobile money<input name="coordonnees_paiement" autoComplete="off" /></label>
        </div>
        <div className="actions"><button className="principal">Ouvrir le dossier</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
