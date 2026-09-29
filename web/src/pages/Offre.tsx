import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { dateFr, pct } from "../format";
import { t } from "../i18n";
import { DepotFichier } from "../composants/DepotFichier";

interface Consultation {
  cabinet: string; client: string; pays: string; assureur: string; cahier: string; date_limite: string;
  conditions: { cle: string; libelle: string; valeur: number | boolean; sens: "min" | "max" | "oui" }[];
  etat: "envoyee" | "ouverte" | "repondue" | "close" | "annulee"; repondue_le: string | null;
}

/** La page d'un assureur consulté, ouverte par son lien personnel, sans compte : lire le cahier, déposer l'offre. */
export default function Offre() {
  const { jeton } = useParams();
  const { donnee: c, erreur, recharger } = useCharge(() => api.get<Consultation>(`/offre/${jeton}`), [jeton]);
  if (erreur) return <div className="legal"><h1>{t("Consultation", "Consultation")}</h1><Erreur erreur={erreur} /></div>;
  if (!c) return <p className="discret">{t("Chargement…", "Loading…")}</p>;
  return (
    <div className="legal offre-assureur">
      <h1>{t("Consultation d'assureurs", "Insurer consultation")}</h1>
      <p>{t(`${c.cabinet}, courtier en assurance, consulte ${c.assureur} pour le compte de son client ${c.client} sur la couverture de ses indemnités de fin de carrière.`,
        `${c.cabinet}, insurance broker, is consulting ${c.assureur} on behalf of its client ${c.client} about covering its end-of-service benefits.`)}</p>
      <div className="lignes-offre carte">
        <div><span>{t("Cahier des charges", "Tender specifications")}</span><strong>N° {c.cahier}</strong></div>
        <div><span>{t("Réponse attendue au plus tard le", "Response due by")}</span><strong>{dateFr(c.date_limite)}</strong></div>
      </div>
      <p><button type="button" className="principal" onClick={() => api.telecharger(`/offre/${jeton}/cahier`, `cahier-des-charges-${c.cahier}.pdf`)}>
        {t("Télécharger le cahier des charges (PDF scellé)", "Download the specifications (sealed PDF)")}</button></p>

      <h2>{t("Les conditions du cahier", "The specifications' terms")}</h2>
      <ul className="liste-simple">
        {c.conditions.map((x) => (
          <li key={x.cle}>{x.libelle}{x.sens === "oui" ? t(" : exigé", ": required")
            : `${x.sens === "min" ? " ≥ " : " ≤ "}${typeof x.valeur === "number" && x.valeur < 1 && !/jours|mois/.test(x.cle) ? pct(x.valeur, 2) : String(x.valeur)}`}</li>
        ))}
      </ul>

      {c.etat === "repondue" && <p className="constat informe">{t(`Votre réponse est reçue (le ${dateFr(c.repondue_le)}). Le courtier la relit et vous contactera s'il faut la préciser.`,
        `Your response has been received (on ${dateFr(c.repondue_le)}). The broker is reviewing it and will contact you if it needs clarifying.`)}</p>}
      {(c.etat === "close" || c.etat === "annulee") && <p className="constat bloquant">{t("Cette consultation est close : elle ne reçoit plus de réponse.",
        "This consultation is closed: it no longer accepts responses.")}</p>}
      {(c.etat === "envoyee" || c.etat === "ouverte") && <Depot jeton={jeton!} onFait={recharger} />}
      <p className="discret">{t("Ce lien vous est personnel : ne le transférez pas. Les données que vous déposez servent à cette consultation seulement.",
        "This link is personal to you: do not forward it. The data you upload are used for this consultation only.")}</p>
    </div>
  );
}

function Depot({ jeton, onFait }: { jeton: string; onFait: () => void }) {
  const [offre, setOffre] = useState<File | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [envoi, setEnvoi] = useState(false);
  async function deposer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const taux = (k: string) => { const v = String(f.get(k) ?? "").trim(); return v === "" ? null : Number(v.replace(",", ".")) / 100; };
    const entier = (k: string) => { const v = String(f.get(k) ?? "").trim(); return v === "" ? null : Number(v); };
    const oui = (k: string) => { const v = f.get(k); return v === "oui" ? true : v === "non" ? false : null; };
    const texte = (k: string) => String(f.get(k) ?? "").trim() || null;
    if (!offre) { setErreur(new Error(t("Joindre votre offre en PDF.", "Attach your offer as a PDF."))); return; }
    const envoiFormulaire = new FormData();
    envoiFormulaire.set("donnees", JSON.stringify({
      taux_garanti: taux("taux_garanti"), participation_benefices: taux("participation_benefices"),
      frais_sur_cotisations: taux("frais_sur_cotisations"), frais_sur_encours: taux("frais_sur_encours"),
      delai_paiement_jours: entier("delai_paiement_jours"), transfert_preavis_mois: entier("transfert_preavis_mois"),
      transfert_penalite: taux("transfert_penalite"), accepte_etude_plateforme: oui("accepte_etude_plateforme"),
      reporting_annuel: oui("reporting_annuel"), historique_participation: texte("historique_participation"),
      commentaire: texte("commentaire") }));
    envoiFormulaire.set("offre", offre);
    setErreur(null);
    setEnvoi(true);
    try { await api.post(`/offre/${jeton}`, envoiFormulaire); onFait(); } catch (e) { setErreur(e); setEnvoi(false); }
  }
  const choixOui = (nom: string) => (
    <select name={nom} defaultValue=""><option value="">—</option><option value="oui">{t("Oui", "Yes")}</option><option value="non">{t("Non", "No")}</option></select>
  );
  return (
    <form className="formulaire carte" onSubmit={deposer} aria-label={t("Déposer votre offre", "Upload your offer")}>
      <h2 style={{ marginTop: 0 }}>{t("Votre offre", "Your offer")}</h2>
      <div className="grille-2">
        <label>{t("Taux garanti (%)", "Guaranteed rate (%)")}<input name="taux_garanti" type="number" step={0.01} required /></label>
        <label>{t("Participation aux bénéfices (%)", "Profit sharing (%)")}<input name="participation_benefices" type="number" step={0.1} required /></label>
        <label>{t("Frais sur cotisations (%)", "Charges on contributions (%)")}<input name="frais_sur_cotisations" type="number" step={0.01} required /></label>
        <label>{t("Frais sur encours (%/an)", "Charges on assets (%/year)")}<input name="frais_sur_encours" type="number" step={0.01} required /></label>
        <label>{t("Délai de paiement d'une prestation (jours)", "Benefit payment period (days)")}<input name="delai_paiement_jours" type="number" min={1} /></label>
        <label>{t("Préavis de transfert (mois)", "Transfer notice (months)")}<input name="transfert_preavis_mois" type="number" min={0} /></label>
        <label>{t("Pénalité de transfert (%)", "Transfer penalty (%)")}<input name="transfert_penalite" type="number" step={0.1} min={0} /></label>
        <label>{t("L'étude du courtier sert de base", "The broker's study is used as the basis")}{choixOui("accepte_etude_plateforme")}</label>
        <label>{t("Relevé annuel du fonds", "Annual fund statement")}{choixOui("reporting_annuel")}</label>
        <label>{t("Participation servie (5 dernières années)", "Profit sharing paid (last 5 years)")}<input name="historique_participation" placeholder="3,1 % ; 3,4 % ; …" /></label>
      </div>
      <label>{t("Commentaire", "Comment")}<input name="commentaire" /></label>
      <DepotFichier libelle={t("Votre offre signée (PDF)", "Your signed offer (PDF)")} accept="application/pdf" fichier={offre} onChange={setOffre} />
      <div className="actions"><button className="principal" disabled={envoi}>{t("Déposer mon offre", "Upload my offer")}</button></div>
      <p className="discret">{t("Une seule réponse par lien. Pour la modifier ensuite, écrivez au courtier.", "One response per link. To change it afterwards, write to the broker.")}</p>
      <Erreur erreur={erreur} />
    </form>
  );
}
