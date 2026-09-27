import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { Constats, Erreur, useCharge, Volet } from "../composants/communs";
import { dateFr, montant } from "../format";
import { t } from "../i18n";
import type { Beneficiaire, DossierPEC, EtapeDossier, Prestation } from "../types";
import { useDossier } from "./Dossier";

// Les libellés se lisent au rendu (la langue peut changer) : des fonctions, pas des constantes figées à l'import.
export const etapes = (): Record<EtapeDossier, string> => ({
  declare: t("Déclaré", "Reported"), a_completer: t("À compléter", "Incomplete"), resoumis: t("Resoumis", "Resubmitted"),
  verifie: t("Vérifié", "Checked"), transmis: t("Transmis", "Sent to insurer"),
  paye: t("Payé", "Paid"), refuse: t("Refusé", "Refused"), identite_effacee: t("Identité effacée", "Identity erased"),
});
const CLASSE: Record<string, string> = { paye: "bien", refuse: "grave", a_completer: "attention", transmis: "neutre" };
const natures = (): Record<string, string> => ({
  certificat_travail: t("Certificat de travail", "Certificate of employment"), attestation_depart: t("Attestation de départ", "Certificate of departure"),
  calcul_signe: t("Calcul de l'indemnité signé", "Signed benefit calculation"), piece_identite: t("Pièce d'identité", "Identity document"),
  rib: t("Relevé d'identité bancaire", "Bank account details"),
  autre: t("Autre pièce", "Other document"), dossier_scelle: t("Dossier scellé transmis", "Sealed claim file sent"),
});
const piecesDIdentite = () => ({ cni: t("Carte nationale d'identité", "National identity card"), passeport: t("Passeport", "Passport"),
  carte_sejour: t("Carte de séjour", "Residence permit"), autre: t("Autre", "Other") });
const paiements = () => ({ virement: t("Virement", "Bank transfer"), mobile_money: t("Mobile money", "Mobile money"), cheque: t("Chèque", "Cheque") });

export function EtatDossier({ statut }: { statut: string }) {
  return <span className={`etat ${CLASSE[statut] ?? "neutre"}`}>{etapes()[statut as EtapeDossier] ?? statut}</span>;
}

/** Courtage : le dossier de prise en charge d'un départ, de la déclaration au paiement. */
export default function DossierPriseEnCharge() {
  const d = useDossier();
  const { id } = useParams();
  const url = `/organisations/${d.org.id}/dossiers/${id}`;
  const { donnee: x, erreur, recharger } = useCharge(() => api.get<DossierPEC>(url), [id]);
  const [erreurAction, setErreurAction] = useState<unknown>(null);
  if (erreur) return <Erreur erreur={erreur} />;
  if (!x) return <p className="discret">{t("Chargement…", "Loading…")}</p>;
  const ETAPES = etapes(), NATURES = natures();

  async function agir(action: string, corps: object = {}) {
    setErreurAction(null);
    try { await api.post(`${url}/${action}`, corps); recharger(); } catch (e) { setErreurAction(e); }
  }
  const conseiller = d.role === "conseiller", entreprise = d.role === "admin_client";
  const ouvert = x.statut !== "paye" && !x.identite_effacee;

  return (
    <>
      <p><Link to="../departs">{t("← Départs", "← Departures")}</Link></p>
      <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>{t(`Prise en charge · matricule ${x.matricule}`, `Benefit payment · staff number ${x.matricule}`)}</h1>
        <EtatDossier statut={x.statut} />
      </div>
      <p className="discret">{t(`Départ du ${dateFr(x.date_depart)} · ${montant(x.montant_demande)} demandés à ${x.assureur}`,
        `Departure on ${dateFr(x.date_depart)} · ${montant(x.montant_demande)} requested from ${x.assureur}`)}
        {x.numero_police && t(` (police ${x.numero_police})`, ` (policy ${x.numero_police})`)} · {t("mandat :", "mandate:")} {x.mandat_reference}</p>
      <Constats constats={x.constats} vide="" />

      <div className="grille g2 section">
        <div className="carte">
          <h2>{t("Étapes", "Steps")}</h2>
          <ol className="etapes-dossier">
            {x.evenements.map((e, i) => (
              <li key={i}><strong>{ETAPES[e.etape]}</strong> <span className="discret">{t(`le ${dateFr(e.le)}`, `on ${dateFr(e.le)}`)}</span>
                {e.montant !== null && <> · {montant(e.montant)}</>}
                {e.numero && <> · <Link to={`/verifier/${e.numero}`}>{e.numero}</Link></>}
                {e.motif && <div className="discret">{t(`« ${e.motif} »`, `“${e.motif}”`)}</div>}</li>
            ))}
          </ol>
          {x.efface_le && <p className="discret">{t(`L'identité du bénéficiaire et les pièces seront effacées le ${dateFr(x.efface_le)}.`,
            `The beneficiary's identity and the documents will be erased on ${dateFr(x.efface_le)}.`)}</p>}
          {x.identite_effacee && <p className="discret">{t("Identité et pièces effacées, comme prévu douze mois après le paiement. Le numéro du dossier se vérifie toujours.",
            "Identity and documents erased, as planned twelve months after payment. The claim file number can still be verified.")}</p>}
        </div>
        <div className="carte">
          <h2>{t("Bénéficiaire", "Beneficiary")}</h2>
          {x.beneficiaire ? <FicheBeneficiaire b={x.beneficiaire} /> :
            <p className="discret">{x.identite_effacee ? t("Effacée.", "Erased.") : t("Visible par l'entreprise et son conseiller seulement.", "Visible to the company and its adviser only.")}</p>}
        </div>
      </div>

      {(entreprise || conseiller) && (
        <div className="carte section">
          <h2>{t("Pièces", "Documents")}</h2>
          {x.pieces.length === 0 ? <p className="discret">{t("Aucune pièce.", "No documents.")}</p> : (
            <table><tbody>{x.pieces.map((p) => (
              <tr key={p.id}><td>{NATURES[p.nature] ?? p.nature}</td><td>{p.nom_fichier}</td>
                <td className="n discret">{t(`${Math.ceil(p.taille / 1024)} Ko`, `${Math.ceil(p.taille / 1024)} KB`)}</td>
                <td className="n"><button className="lien" onClick={() => api.ouvrir(p.nature === "dossier_scelle"
                  ? `${url}/document` : `${url}/pieces/${p.id}`)}>{t("Ouvrir", "Open")}</button></td></tr>
            ))}</tbody></table>
          )}
          {ouvert && <AjoutPiece url={url} onFait={recharger} />}
        </div>
      )}

      <div className="section">
        {conseiller && (x.statut === "declare" || x.statut === "resoumis") && <Verifier agir={agir} />}
        {entreprise && x.statut === "a_completer" && (
          <div className="carte"><p>{t("Votre conseiller attend un complément (voir les étapes). Ajoutez les pièces, puis :", "Your adviser is waiting for more information (see the steps). Add the documents, then:")}</p>
            <button className="principal" onClick={() => agir("resoumission")}>{t("Resoumettre le dossier", "Resubmit the claim file")}</button></div>
        )}
        {conseiller && (x.statut === "verifie" || x.statut === "refuse") && <Transmettre agir={agir} refuse={x.statut === "refuse"} />}
        {conseiller && x.statut === "transmis" && <Repondre agir={agir} montantDemande={x.montant_demande} />}
        {!conseiller && ["declare", "resoumis", "verifie", "transmis"].includes(x.statut) && (
          <p className="discret">{x.statut === "transmis" ? t("L'assureur a le dossier : votre conseiller suit le paiement.", "The insurer has the claim file: your adviser is following the payment.")
            : t("Votre conseiller vérifie le dossier puis le transmet à l'assureur.", "Your adviser checks the claim file, then sends it to the insurer.")}</p>
        )}
        <Erreur erreur={erreurAction} />
      </div>
    </>
  );
}

function FicheBeneficiaire({ b }: { b: Beneficiaire }) {
  return (
    <div className="lignes-offre">
      <div><span>{t("Qualité", "Capacity")}</span><span>{b.qualite === "salarie" ? t("Le salarié", "The employee") : t("Ayant droit", "Dependant")}</span></div>
      <div><span>{t("Nom et prénoms", "Full name")}</span><strong>{b.nom} {b.prenoms}</strong></div>
      {b.date_naissance && <div><span>{t("Né(e) le", "Born on")}</span><span>{dateFr(b.date_naissance)}</span></div>}
      <div><span>{piecesDIdentite()[b.piece_type]}</span><span>{b.piece_numero}</span></div>
      {b.telephone && <div><span>{t("Téléphone", "Phone")}</span><span>{b.telephone}</span></div>}
      <div><span>{paiements()[b.moyen_paiement]}</span><span>{b.coordonnees_paiement ?? "—"}</span></div>
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
      <label>{t("Nature", "Type")}<select name="nature">{Object.entries(natures()).filter(([k]) => k !== "dossier_scelle")
        .map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
      <label>{t("Fichier (PDF, JPEG, PNG · 5 Mo)", "File (PDF, JPEG, PNG · 5 MB)")}<input name="fichier" type="file" accept=".pdf,.jpg,.jpeg,.png" required /></label>
      <button>{t("Ajouter la pièce", "Add the document")}</button>
      <Erreur erreur={erreur} />
    </form>
  );
}

function Verifier({ agir }: { agir: (a: string, c?: object) => void }) {
  const [motif, setMotif] = useState("");
  return (
    <div className="carte">
      <h3>{t("Vérifier le dossier", "Check the claim file")}</h3>
      <div className="actions">
        <button className="principal" onClick={() => agir("verification", { conforme: true })}>{t("Dossier complet", "Claim file complete")}</button>
        <input aria-label={t("Ce qui manque", "What is missing")} placeholder={t("Ce qui manque…", "What is missing…")} value={motif} onChange={(e) => setMotif(e.target.value)} />
        <button disabled={!motif.trim()} onClick={() => agir("verification", { conforme: false, motif })}>{t("À compléter", "Incomplete")}</button>
      </div>
    </div>
  );
}

function Transmettre({ agir, refuse }: { agir: (a: string, c?: object) => void; refuse: boolean }) {
  const [le, setLe] = useState(new Date().toISOString().slice(0, 10));
  return (
    <div className="carte">
      <h3>{refuse ? t("Contester et transmettre à nouveau", "Challenge and send again") : t("Sceller et transmettre", "Seal and send")}</h3>
      <p className="discret">{t("La plateforme scelle le dossier (numéro PC-…) ; vous l'envoyez à l'assureur et notez la date d'envoi. Le sceau public ne porte aucune donnée personnelle.",
        "The platform seals the claim file (number PC-…); you send it to the insurer and note the date it was sent. The public seal carries no personal data.")}</p>
      <div className="actions">
        <label>{t("Envoyé le", "Sent on")}<input type="date" value={le} onChange={(e) => setLe(e.target.value)} /></label>
        <button className="principal" onClick={() => agir("transmission", { le })}>{t("Sceller et noter l'envoi", "Seal and record the sending")}</button>
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
      <h3>{t("Réponse de l'assureur", "Insurer's response")}</h3>
      <div className="actions">
        <label><input type="radio" checked={paye} onChange={() => setPaye(true)} /> {t("Payé", "Paid")}</label>
        <label><input type="radio" checked={!paye} onChange={() => setPaye(false)} /> {t("Refusé", "Refused")}</label>
      </div>
      <div className="grille g3">
        <label>{t("Le", "On")}<input type="date" value={le} onChange={(e) => setLe(e.target.value)} /></label>
        {paye ? <label>{t("Montant payé (F)", "Amount paid (F)")}<input type="number" min={1} value={montantPaye} onChange={(e) => setMontant(e.target.value)} /></label>
          : <label>{t("Motif du refus", "Reason for refusal")}<input value={motif} onChange={(e) => setMotif(e.target.value)} /></label>}
      </div>
      <div className="actions">
        <button className="principal" onClick={() => agir("reponse", paye ? { paye, montant: Number(montantPaye), le } : { paye, motif, le })}>
          {t("Enregistrer la réponse", "Save the response")}</button>
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
    const s = (k: string) => String(f.get(k) ?? "").trim() || null;
    setErreur(null);
    try {
      const x = await api.post<DossierPEC>(`/organisations/${d.org.id}/dossiers`, {
        prestation_id: p.id, montant_demande: Number(f.get("montant_demande")),
        beneficiaire: { qualite: f.get("qualite"), nom: s("nom"), prenoms: s("prenoms"), date_naissance: s("date_naissance"),
          piece_type: f.get("piece_type"), piece_numero: s("piece_numero"), telephone: s("telephone"),
          moyen_paiement: f.get("moyen_paiement"), coordonnees_paiement: s("coordonnees_paiement") } });
      naviguer(`../dossiers/${x.id}`);
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre={t(`Demander la prise en charge · matricule ${p.matricule}`, `Request the benefit payment · staff number ${p.matricule}`)} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={ouvrir}>
        <p className="discret">{t("Vous êtes en courtage : nous portons la demande auprès de l'assureur. L'identité du bénéficiaire sert à ce seul paiement ; elle reste dans ce dossier, n'entre dans aucun rapport, et est effacée douze mois après le paiement.",
          "You are under brokerage: we take the request to the insurer. The beneficiary's identity is used for this payment only; it stays in this claim file, appears in no report, and is erased twelve months after payment.")}</p>
        <div className="grille g3">
          <label>{t("Montant demandé au fonds (F)", "Amount requested from the fund (F)")}<input name="montant_demande" type="number" min={1} required
                 defaultValue={p.verse ?? p.du} /></label>
          <label>{t("Le bénéficiaire est", "The beneficiary is")}<select name="qualite"><option value="salarie">{t("le salarié", "the employee")}</option>
            <option value="ayant_droit">{t("un ayant droit", "a dependant")}</option></select></label>
          <span />
          <label>{t("Nom", "Surname")}<input name="nom" required autoComplete="off" /></label>
          <label>{t("Prénoms", "First names")}<input name="prenoms" autoComplete="off" /></label>
          <label>{t("Date de naissance", "Date of birth")}<input name="date_naissance" type="date" /></label>
          <label>{t("Pièce d'identité", "Identity document")}<select name="piece_type">{Object.entries(piecesDIdentite()).map(([k, l]) =>
            <option key={k} value={k}>{l}</option>)}</select></label>
          <label>{t("Numéro de la pièce", "Document number")}<input name="piece_numero" required autoComplete="off" /></label>
          <label>{t("Téléphone", "Phone")}<input name="telephone" type="tel" autoComplete="off" /></label>
          <label>{t("Paiement par", "Payment by")}<select name="moyen_paiement">{Object.entries(paiements()).map(([k, l]) =>
            <option key={k} value={k}>{l}</option>)}</select></label>
          <label>{t("IBAN ou numéro mobile money", "IBAN or mobile money number")}<input name="coordonnees_paiement" autoComplete="off" /></label>
        </div>
        <div className="actions"><button className="principal">{t("Ouvrir le dossier", "Open the claim file")}</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
