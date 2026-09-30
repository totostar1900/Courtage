import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { useCabinet } from "../cabinet";
import { Cle, Erreur, useCharge } from "../composants/communs";
import { DepotFichier } from "../composants/DepotFichier";
import { lienWhatsApp } from "../contact";
import { Echeancier } from "../composants/Echeancier";
import { dateFr, millions, montant } from "../format";
import { mesurer, useMesure } from "../mesure";
import { t } from "../i18n";
import type { Annee, Totaux } from "../types";

/** Ce que l'essai garde, dans ce navigateur seulement : l'inscription le reprend. Trente minutes, pas plus : un
 *  visiteur qui revient plus tard repart d'une page vide. */
export const CLE_ESSAI = "courtage:essai";
export const DUREE_ESSAI_MS = 30 * 60 * 1000;

export interface EssaiGarde {
  pays: string; convention_code: string; date_evaluation: string; fonds_disponible: number;
  modele: { code: string; titre: string; version: Record<string, unknown> } | null;
  fichier: { nom: string; type: string; base64: string } | null;
  garde_le?: number;
}

interface Convention { code: string; libelle: string; pays: string; pays_libelle: string; en_vigueur_aujourd_hui: boolean }
interface Modele { code: string; titre: string; description: string; convention: { code: string };
                  version: { categories: unknown[] } & Record<string, unknown> }
interface Resultat {
  effectif: number; convention: { code: string; libelle: string }; date_evaluation: string; fonds_disponible: number;
  totaux: Totaux; echeancier: Annee[]; sensibilite: { libelle: string; dette: number } | null; nombre_anomalies: number;
}

const finAnneeDerniere = () => `${new Date().getFullYear() - 1}-12-31`;

export function lireEssai(maintenant = Date.now()): EssaiGarde | null {
  try {
    const x = sessionStorage.getItem(CLE_ESSAI);
    if (!x) return null;
    const e = JSON.parse(x) as EssaiGarde;
    if (!e.garde_le || maintenant - e.garde_le > DUREE_ESSAI_MS) { oublierEssai(); return null; }
    return e;
  } catch { return null; }
}

export function oublierEssai() {
  try { sessionStorage.removeItem(CLE_ESSAI); } catch { /* rien à oublier */ }
}

function garder(e: EssaiGarde) {
  try { sessionStorage.setItem(CLE_ESSAI, JSON.stringify({ ...e, garde_le: Date.now() })); }
  catch { /* trop lourd pour le navigateur : l'essai reste à l'écran */ }
}

function enBase64(f: File): Promise<string> {
  return new Promise((resoudre, rejeter) => {
    const lecteur = new FileReader();
    lecteur.onload = () => resoudre(String(lecteur.result).split(",", 2)[1] ?? "");
    lecteur.onerror = () => rejeter(lecteur.error);
    lecteur.readAsDataURL(f);
  });
}

export function fichierDeLEssai(g: NonNullable<EssaiGarde["fichier"]>): File {
  const binaire = atob(g.base64);
  const octets = new Uint8Array(binaire.length);
  for (let i = 0; i < binaire.length; i++) octets[i] = binaire.charCodeAt(i);
  return new File([octets], g.nom, { type: g.type });
}

/** À l'inscription : le fichier de l'essai devient le premier fichier du personnel, son modèle type une version du
 *  régime en analyse. Ce qui échoue n'empêche rien (l'entreprise le refera dans son dossier) ; l'essai est ensuite
 *  oublié du navigateur. Rend ce qui a été repris. */
export async function reprendreEssai(orgId: string): Promise<{ fichier: boolean; regime: boolean }> {
  const e = lireEssai();
  const repris = { fichier: false, regime: false };
  if (!e) return repris;
  if (e.fichier) {
    try {
      const envoi = new FormData();
      envoi.append("fichier", fichierDeLEssai(e.fichier));
      envoi.append("date_donnees", e.date_evaluation);
      await api.post(`/organisations/${orgId}/fichiers`, envoi);
      repris.fichier = true;
    } catch { /* le fichier se déposera depuis « Personnel » */ }
  }
  if (e.modele) {
    try {
      const r = await api.post<{ id: string }>(`/organisations/${orgId}/regimes`, { nom: e.modele.titre });
      await api.post(`/organisations/${orgId}/regimes/${r.id}/versions`, { ...e.modele.version, en_vigueur_du: e.date_evaluation });
      repris.regime = true;
    } catch { /* le régime se décrira depuis « Régime » */ }
  }
  oublierEssai();
  return repris;
}

/** L'essai sans compte : son personnel, son fonds, un régime, et l'engagement à l'écran. Rien n'est gardé sur la
 *  plateforme ; rien ne s'imprime ; « Enregistrer mes résultats » mène à l'inscription, qui reprend la saisie. */
export default function Essai() {
  useMesure("essai_ouvert");
  const [precedent] = useState(() => lireEssai());
  const cabinet = useCabinet();
  const { donnee: ref } = useCharge(() => api.get<{ conventions: Convention[]; pays_couverts: Record<string, string> }>("/referentiel/conventions"), []);
  const [pays, setPays] = useState(precedent?.pays ?? "CM");
  const [convention, setConvention] = useState(precedent?.convention_code ?? "");
  const [modele, setModele] = useState<string>(precedent?.modele?.code ?? "");
  const [fichier, setFichier] = useState<File | null>(precedent?.fichier ? fichierDeLEssai(precedent.fichier) : null);
  const [resultat, setResultat] = useState<Resultat | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [calcul, setCalcul] = useState(false);
  const { donnee: modeles } = useCharge(() => api.get<{ modeles: Modele[] }>(`/referentiel/modeles?pays=${pays}`), [pays]);
  const conventions = (ref?.conventions ?? []).filter((c) => c.pays === pays && c.en_vigueur_aujourd_hui);
  const premiere = conventions[0]?.code;
  useEffect(() => {
    if (premiere && !conventions.some((c) => c.code === convention)) setConvention(premiere);
  }, [premiere, conventions, convention]);
  const choisi = modeles?.modeles.find((m) => m.code === modele) ?? null;

  /** Retirer le fichier : il n'est plus envoyé, ni gardé dans ce navigateur. */
  function changerFichier(f: File | null) {
    setFichier(f);
    setResultat(null);
    if (!f) oublierEssai();
  }

  async function calculer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    if (!fichier) return;
    const f = new FormData(ev.currentTarget);
    const parametres = {
      pays, date_evaluation: String(f.get("date_evaluation")), fonds_disponible: Number(f.get("fonds_disponible") || 0),
      convention_code: choisi ? choisi.convention.code : convention,
      ...(choisi ? { categories: choisi.version.categories } : {}),
    };
    const envoi = new FormData();
    envoi.append("fichier", fichier);
    envoi.append("parametres", JSON.stringify(parametres));
    setErreur(null);
    setCalcul(true);
    try {
      setResultat(await api.post<Resultat>("/essai/etude", envoi));
      mesurer("essai_calcule");
    } catch (e) { setErreur(e); setResultat(null); setCalcul(false); return; }
    setCalcul(false);
    try {
      garder({ pays, convention_code: parametres.convention_code, date_evaluation: parametres.date_evaluation,
               fonds_disponible: parametres.fonds_disponible,
               modele: choisi ? { code: choisi.code, titre: choisi.titre, version: choisi.version } : null,
               fichier: { nom: fichier.name, type: fichier.type, base64: await enBase64(fichier) } });
    } catch { /* la saisie n'est pas gardée : l'inscription repartira de zéro, l'essai reste à l'écran */ }
  }

  return (
    <div className="essai">
      <p className="essai-impression">{t("L'essai ne s'imprime pas : inscrivez-vous pour obtenir un rapport scellé.",
        "The trial cannot be printed: sign up to get a sealed report.")}</p>
      <h1>{t("Essayer sans compte", "Try without an account")}</h1>
      <p>{t("Votre personnel, votre fonds, un régime : votre engagement d'indemnités de fin de carrière, calculé par le vrai moteur. Rien n'est gardé sur la plateforme ; l'estimation n'est ni scellée ni imprimable.",
        "Your staff, your fund, a plan: your end-of-service liability, calculated by the real engine. Nothing is kept on the platform; the estimate is neither sealed nor printable.")}</p>

      <form className="carte section formulaire" onSubmit={calculer} aria-label={t("Paramètres de l'essai", "Trial settings")}>
        <div className="grille-2">
          <label>{t("Pays", "Country")}
            <select value={pays} onChange={(e) => { setPays(e.target.value); setModele(""); setConvention(""); }}>
              {Object.entries(ref?.pays_couverts ?? { CM: "Cameroun" }).map(([code, nom]) => <option key={code} value={code}>{nom}</option>)}
            </select></label>
          <label>{t("Convention collective", "Collective agreement")}
            <select value={choisi ? choisi.convention.code : convention} onChange={(e) => setConvention(e.target.value)} disabled={Boolean(choisi)}>
              {conventions.map((c) => <option key={c.code} value={c.code}>{c.libelle}</option>)}
            </select></label>
          <label>{t("Régime", "Plan")}
            <select value={modele} onChange={(e) => setModele(e.target.value)}>
              <option value="">{t("La convention seule", "The collective agreement only")}</option>
              {(modeles?.modeles ?? []).map((m) => <option key={m.code} value={m.code}>{t("Modèle type : ", "Standard template: ")}{m.titre}</option>)}
            </select></label>
          <label>{t("Évaluation au", "Valuation date")}<input type="date" name="date_evaluation" required
                  defaultValue={precedent?.date_evaluation ?? finAnneeDerniere()} /></label>
          <label>{t("Fonds déjà constitué (F)", "Fund already built up (F)")}<input type="number" name="fonds_disponible" min={0}
                  defaultValue={precedent?.fonds_disponible ?? 0} /></label>
        </div>
        {choisi && <p className="discret">{choisi.description}</p>}
        <DepotFichier libelle={t("Votre personnel (Excel ou CSV, 300 salariés au plus)", "Your staff (Excel or CSV, 300 employees at most)")}
          accept=".xlsx,.csv" fichier={fichier} onChange={changerFichier}
          aide={<>{t("Un matricule, jamais un nom. ", "A staff number, never a name. ")}
            <button type="button" className="lien" onClick={() => api.telecharger("/referentiel/canevas-personnel", "canevas-personnel.xlsx")}>
              {t("Télécharger le canevas à remplir", "Download the template to fill in")}</button>
            {precedent?.fichier && fichier?.name === precedent.fichier.nom
              && t(" · Repris de votre essai précédent : retirez-le pour repartir de zéro.", " · Carried over from your previous trial: remove it to start afresh.")}</>} />
        <div className="actions"><button className="principal" disabled={!fichier || calcul}>
          {calcul ? t("Calcul…", "Calculating…") : t("Calculer mon engagement", "Calculate my liability")}</button></div>
        <p className="discret">{t("Rien n'est gardé sur la plateforme. Dans ce navigateur, votre saisie est gardée 30 minutes pour que l'inscription la reprenne ; « Retirer » l'efface aussitôt.",
          "Nothing is kept on the platform. In this browser, what you entered is kept for 30 minutes so that sign-up can carry it over; “Remove” erases it at once.")}</p>
        <Erreur erreur={erreur} />
      </form>

      {resultat && (
        <section className="section resultat-essai" aria-label={t("Résultat de l'essai", "Trial result")}>
          <div className="filigrane" aria-hidden="true">{t("Estimation — non scellée", "Estimate — not sealed")}</div>
          <h2>{t(`Votre engagement au ${dateFr(resultat.date_evaluation)}`, `Your liability as at ${dateFr(resultat.date_evaluation)}`)}</h2>
          <p className="discret">{t(`${resultat.effectif} salariés · ${resultat.convention.libelle}`, `${resultat.effectif} employees · ${resultat.convention.libelle}`)}</p>
          <div className="grille g4">
            <Cle etiquette={t("Dette actuarielle", "Actuarial liability")} valeur={millions(resultat.totaux.dette)} sous={montant(resultat.totaux.dette)} terme="dette" />
            <Cle etiquette={t("Charge annuelle", "Annual cost")} valeur={millions(resultat.totaux.charge)} sous={montant(resultat.totaux.charge)} terme="charge" />
            <Cle etiquette={t("Fonds constitué", "Fund built up")} valeur={millions(resultat.fonds_disponible)} sous={montant(resultat.fonds_disponible)} terme="fonds" />
            {resultat.totaux.cotisation_totale !== undefined && (
              <Cle etiquette={t("Cotisation à verser", "Contribution to pay")} valeur={millions(resultat.totaux.cotisation_totale)} sous={montant(resultat.totaux.cotisation_totale)} />
            )}
          </div>
          {resultat.sensibilite && (
            <p>{t(`Si le taux d'actualisation baissait d'un point, la dette passerait à ${montant(resultat.sensibilite.dette)}.`,
              `If the discount rate fell by one point, the liability would rise to ${montant(resultat.sensibilite.dette)}.`)}</p>
          )}
          {resultat.nombre_anomalies > 0 && (
            <p className="discret">{t(`${resultat.nombre_anomalies} point(s) à regarder dans votre fichier : ils se lisent un par un dans votre dossier.`,
              `${resultat.nombre_anomalies} point(s) to check in your file: they can be read one by one in your file space.`)}</p>
          )}
          <div className="carte section"><h3>{t("Départs prévus", "Expected departures")}</h3>
            <Echeancier annees={resultat.echeancier} fonds={resultat.fonds_disponible} /></div>
          <EtEnsuite whatsapp={lienWhatsApp(cabinet?.telephone, t("Bonjour, je viens de faire l'essai sur la plateforme et j'aimerais en parler.", "Hello, I have just run the trial on the platform and would like to talk about it."))} />
        </section>
      )}
    </div>
  );
}

/** Ce qui vient après l'essai : les étapes, et trois façons de continuer la conversation. */
function EtEnsuite({ whatsapp }: { whatsapp: string | null }) {
  const etapes: [string, string][] = [
    [t("Créez votre compte", "Create your account"), t("Deux minutes. Votre saisie est reprise.", "Two minutes. What you entered is carried over.")],
    [t("Un conseiller vous appelle", "An adviser calls you"), t("Sous deux jours ouvrés : il confirme l'entreprise et vos besoins.", "Within two working days: they confirm the company and your needs.")],
    [t("Le rapport scellé", "The sealed report"), t("L'évaluation relue, émise, vérifiable par son numéro.", "The valuation reviewed, issued, verifiable by its number.")],
    [t("Les assureurs consultés", "Insurers consulted"), t("Votre conseiller vous apporte leurs offres, classées par rendement net.", "Your adviser brings you their offers, ranked by net return.")],
    [t("Vous choisissez", "You choose"), t("Sur des chiffres, sans frais pour l'entreprise.", "On figures, at no cost to the company.")],
  ];
  return (
    <div className="carte section et-ensuite" aria-labelledby="et-ensuite">
      <p className="surtitre">{t("Et ensuite ?", "What comes next?")}</p>
      <h3 id="et-ensuite">{t("Ce chiffre est un début. Voici la suite.", "This figure is a start. Here is what follows.")}</h3>
      <ol className="frise">
        {etapes.map(([titre, texte], i) => (
          <li key={titre}><span className="frise-num">{i + 1}</span><strong>{titre}</strong><span>{texte}</span></li>
        ))}
      </ol>
      <div className="actions">
        <Link to="/inscription" className="bouton principal">{t("Créer mon compte et garder mes résultats", "Create my account and keep my results")}</Link>
        {whatsapp && <a className="bouton whatsapp" href={whatsapp} target="_blank" rel="noopener noreferrer">{t("En parler sur WhatsApp", "Talk on WhatsApp")}</a>}
        <Link to="/#vitrine-rappel" className="bouton">{t("Être rappelé", "Get a call back")}</Link>
        <Link to="/connexion" className="lien-discret">{t("J'ai déjà un compte", "I already have an account")}</Link>
      </div>
    </div>
  );
}
