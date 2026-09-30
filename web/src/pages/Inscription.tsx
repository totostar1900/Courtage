import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, seConnecter } from "../api";
import { useCabinet } from "../cabinet";
import { useMesure } from "../mesure";
import { Erreur, useCharge } from "../composants/communs";
import { t } from "../i18n";
import { reprendreEssai } from "./Essai";
import { ChampTelephone } from "../composants/ChampTelephone";

type Nature = "telephone" | "courriel";
interface Canal { cible: string; codeDemande: boolean; message: string | null; preuve: string | null }
const CANAL_VIDE: Canal = { cible: "", codeDemande: false, message: null, preuve: null };

// Lus au rendu : la langue peut changer.
const pays = (): [string, string][] => [
  ["CM", t("Cameroun", "Cameroon")], ["GA", t("Gabon", "Gabon")], ["CG", t("Congo", "Congo")],
  ["TD", t("Tchad", "Chad")], ["CF", t("Centrafrique", "Central African Republic")],
  ["GQ", t("Guinée équatoriale", "Equatorial Guinea")],
];
const tailles = (): [string, string][] => [
  ["moins_de_50", t("moins de 50 salariés", "fewer than 50 employees")],
  ["50_a_250", t("50 à 250 salariés", "50 to 250 employees")],
  ["plus_de_250", t("plus de 250 salariés", "more than 250 employees")],
];
const secteurs = () => [t("Commerce et distribution", "Retail and distribution"), t("BTP", "Construction"),
  t("Industrie", "Manufacturing"), t("Banque et assurance", "Banking and insurance"), t("Services", "Services"),
  t("Transport et logistique", "Transport and logistics"), t("Énergie et mines", "Energy and mining"),
  t("Agriculture", "Agriculture"), t("Télécommunications", "Telecommunications")];

/** L'essai en cours (tenu par la page d'essai) : il est repris dans le dossier juste après l'inscription. */
function essaiEnCours(): boolean {
  try { return Boolean(sessionStorage.getItem("courtage:essai")); } catch { return false; }
}

/** L'inscription en libre-service : les coordonnées vérifiées, la personne, l'entreprise. Le dossier s'ouvre aussitôt,
 *  en attente de confirmation par le courtier. */
export default function Inscription() {
  const naviguer = useNavigate();
  const [etape, setEtape] = useState(1);
  const [telephone, setTelephone] = useState<Canal>(CANAL_VIDE);
  const [courriel, setCourriel] = useState<Canal>(CANAL_VIDE);
  const [nom, setNom] = useState("");
  const [fonction, setFonction] = useState("");
  const [erreur, setErreur] = useState<unknown>(null);
  const [envoi, setEnvoi] = useState(false);
  const [accepte, setAccepte] = useState(false);
  const [entreprise, setEntreprise] = useState<Record<string, string | null> | null>(null);
  const [besoins, setBesoins] = useState<string[]>(["placement"]);
  const [precision, setPrecision] = useState("");
  const { donnee: listeBesoins } = useCharge(
    () => api.get<{ besoins: { code: string; libelle: string }[] }>("/public/besoins").catch(() => ({ besoins: [] })), []);
  const cabinet = useCabinet();
  useMesure("inscription_ouverte");
  const etapes = [t("Vos coordonnées", "Your contact details"), t("Vous", "You"), t("L'entreprise", "The company"),
                  t("Vos besoins", "Your needs")];

  function retenirEntreprise(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const texte = (k: string) => String(f.get(k) ?? "").trim() || null;
    setEntreprise({ nom: texte("entreprise"), pays: String(f.get("pays")), rccm: texte("rccm"), taille: String(f.get("taille")),
                    secteur: texte("secteur"), adresse: texte("adresse"), ville: texte("ville") });
    setEtape(4);
  }

  async function inscrire(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setErreur(null);
    setEnvoi(true);
    try {
      const r = await api.post<{ organisation_id: string }>("/inscription", {
        telephone: telephone.cible, preuve_telephone: telephone.preuve,
        courriel: courriel.cible, preuve_courriel: courriel.preuve,
        nom: nom.trim(), fonction: fonction.trim() || null,
        entreprise,
        conditions: cabinet?.conditions_version,
        ...(besoins.length ? { accompagnement: { besoins, message: precision.trim() || null } } : {}),
      });
      seConnecter(null);     // la session est le cookie posé par la réponse
      await reprendreEssai(r.organisation_id);
      naviguer(`/dossier/${r.organisation_id}`);
    } catch (e) { setErreur(e); setEnvoi(false); }
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <h1>{t("Créer votre compte", "Create your account")}</h1>
      <p className="discret">{t("Quatre étapes. Votre dossier s'ouvre aussitôt ; votre conseiller confirme ensuite votre "
        + "entreprise, sous 2 jours ouvrés.", "Four steps. Your file opens straight away; your adviser then confirms "
        + "your company within 2 working days.")}</p>
      {essaiEnCours() && (
        <p className="constat informe">{t("Votre essai sera repris dans votre dossier.", "Your trial will be carried into your file.")}</p>
      )}
      <ol className="inscription-etapes" aria-label={t("Étapes", "Steps")}>
        {etapes.map((e, i) => <li key={e} aria-current={etape === i + 1 ? "step" : undefined}>{i + 1}. {e}</li>)}
      </ol>

      {etape === 1 && (
        <div className="carte">
          <h2 style={{ marginTop: 0 }}>{t("Vos coordonnées", "Your contact details")}</h2>
          <VerificationCanal nature="telephone" canal={telephone} onChange={setTelephone} />
          <VerificationCanal nature="courriel" canal={courriel} onChange={setCourriel} />
          <div className="actions">
            <button type="button" className="principal" disabled={!telephone.preuve || !courriel.preuve}
                    onClick={() => setEtape(2)}>{t("Continuer", "Continue")}</button>
          </div>
        </div>
      )}

      {etape === 2 && (
        <form className="carte formulaire" onSubmit={(ev) => { ev.preventDefault(); setEtape(3); }}>
          <h2 style={{ marginTop: 0 }}>{t("Vous", "You")}</h2>
          <label>{t("Nom et prénom", "Full name")}
            <input name="nom" required minLength={2} maxLength={120} autoComplete="name" value={nom}
                   onChange={(e) => setNom(e.target.value)} /></label>
          <label>{t("Fonction", "Job title")}
            <input name="fonction" maxLength={80} placeholder={t("DRH, DG, DAF…", "HR director, CEO, CFO…")} value={fonction}
                   onChange={(e) => setFonction(e.target.value)} /></label>
          <div className="actions">
            <button className="principal">{t("Continuer", "Continue")}</button>
            <button type="button" onClick={() => setEtape(1)}>{t("Retour", "Back")}</button>
          </div>
        </form>
      )}

      {etape === 3 && (
        <form className="carte formulaire" onSubmit={retenirEntreprise}>
          <h2 style={{ marginTop: 0 }}>{t("L'entreprise", "The company")}</h2>
          <label>{t("Raison sociale", "Company name")}
            <input name="entreprise" required minLength={2} maxLength={200} autoComplete="organization" defaultValue={entreprise?.nom ?? ""} /></label>
          <div className="grille-2">
            <label>{t("Pays", "Country")}
              <select name="pays" defaultValue={entreprise?.pays ?? "CM"}>
                {pays().map(([code, libelle]) => <option key={code} value={code}>{libelle}</option>)}
              </select></label>
            <label>{t("Numéro RCCM", "Trade register (RCCM) number")}
              <input name="rccm" required minLength={3} maxLength={80} placeholder="RC/DLA/2020/B/1234" defaultValue={entreprise?.rccm ?? ""} /></label>
            <label>{t("Taille", "Size")}
              <select name="taille" defaultValue={entreprise?.taille ?? "50_a_250"}>
                {tailles().map(([code, libelle]) => <option key={code} value={code}>{libelle}</option>)}
              </select></label>
            <label>{t("Secteur", "Sector")}
              <input name="secteur" list="secteurs-inscription" maxLength={120} defaultValue={entreprise?.secteur ?? ""} /></label>
          </div>
          <datalist id="secteurs-inscription">{secteurs().map((s) => <option key={s} value={s} />)}</datalist>
          <label>{t("Adresse", "Address")}<input name="adresse" maxLength={300} autoComplete="street-address" defaultValue={entreprise?.adresse ?? ""} /></label>
          <label>{t("Ville", "City")}<input name="ville" maxLength={120} autoComplete="address-level2" defaultValue={entreprise?.ville ?? ""} /></label>
          <p className="discret">{t("Le document RCCM pourra être envoyé après l'inscription, depuis votre dossier : votre "
            + "conseiller s'en sert pour confirmer l'entreprise.", "The RCCM document can be sent after signing up, from "
            + "your file: your adviser uses it to confirm the company.")}</p>
          <div className="actions">
            <button className="principal">{t("Continuer", "Continue")}</button>
            <button type="button" onClick={() => setEtape(2)}>{t("Retour", "Back")}</button>
          </div>
        </form>
      )}

      {etape === 4 && (
        <form className="carte formulaire" onSubmit={inscrire}>
          <h2 style={{ marginTop: 0 }}>{t("Vos besoins", "Your needs")}</h2>
          <p>{t("Ce que vous attendez de votre courtier. Votre conseiller s'en sert pour préparer votre mandat : rien ne vous engage avant la signature, et l'accompagnement ne vous coûte rien.",
            "What you expect from your broker. Your adviser uses it to prepare your mandate: nothing binds you before you sign, and the support costs you nothing.")}</p>
          <fieldset className="choix-cartes"><legend className="visuellement-cache">{t("Ce que vous attendez", "What you expect")}</legend>
            {(listeBesoins?.besoins ?? []).map((x) => (
              <label key={x.code} className={`choix-carte${besoins.includes(x.code) ? " coche" : ""}`}>
                <input type="checkbox" checked={besoins.includes(x.code)}
                       onChange={(e) => setBesoins(e.target.checked ? [...besoins, x.code] : besoins.filter((c) => c !== x.code))} />
                <span>{x.libelle}</span>
              </label>
            ))}
          </fieldset>
          <label>{t("Précisions (facultatif)", "Details (optional)")}
            <textarea rows={3} maxLength={2000} value={precision} onChange={(e) => setPrecision(e.target.value)}
                      placeholder={t("Échéance de votre contrat actuel, contraintes, questions…", "End date of your current contract, constraints, questions…")} /></label>
          <label className="case">
            <input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)} />{" "}
            <span>{t("J'ai lu et j'accepte les ", "I have read and accept the ")}
              <Link to="/conditions" target="_blank">{t("conditions d'utilisation", "terms of use")}</Link>
              {t(" et la ", " and the ")}
              <Link to="/confidentialite" target="_blank">{t("politique de confidentialité", "privacy policy")}</Link>.</span>
          </label>
          <div className="actions">
            <button className="principal" disabled={envoi || !accepte || !cabinet}>{t("Créer mon compte", "Create my account")}</button>
            <button type="button" onClick={() => setEtape(3)}>{t("Retour", "Back")}</button>
          </div>
          <Erreur erreur={erreur} />
        </form>
      )}

      <p className="section discret">{t("Déjà un compte ? ", "Already have an account? ")}
        <Link to="/connexion">{t("Se connecter", "Sign in")}</Link></p>
    </div>
  );
}

/** Un canal (téléphone ou courriel) : la cible, « Recevoir un code », le code, puis ✓. */
function VerificationCanal({ nature, canal, onChange }: { nature: Nature; canal: Canal; onChange: (c: Canal) => void }) {
  const [erreur, setErreur] = useState<unknown>(null);
  const [code, setCode] = useState("");
  const tel = nature === "telephone";
  const libelle = tel ? t("Téléphone", "Phone") : t("Courriel", "Email");

  async function demander(ev: FormEvent) {
    ev.preventDefault();
    setErreur(null);
    try {
      const r = await api.post<{ message: string }>("/inscription/code", { nature, cible: canal.cible });
      onChange({ ...canal, codeDemande: true, message: r.message, preuve: null });
      setCode("");
    } catch (e) { setErreur(e); }
  }
  async function verifier(ev: FormEvent) {
    ev.preventDefault();
    setErreur(null);
    try {
      const r = await api.post<{ preuve: string }>("/inscription/verification", { nature, cible: canal.cible, code });
      onChange({ ...canal, preuve: r.preuve });
    } catch (e) { setErreur(e); }
  }

  if (canal.preuve)
    return (
      <p className="section" data-canal={nature}>
        <span className="verifie" aria-hidden="true">✓ </span>{libelle}{t(" : ", ": ")}<strong>{canal.cible}</strong>{" "}
        <span className="discret">{t("vérifié", "verified")}</span>{" "}
        <button type="button" className="lien" onClick={() => onChange(CANAL_VIDE)}>{t("Changer", "Change")}</button>
      </p>
    );
  return (
    <div className="section" data-canal={nature}>
      {!canal.codeDemande ? (
        <form key="cible" className="formulaire" onSubmit={demander}>
          {tel ? <ChampTelephone libelle={libelle} valeur={canal.cible} required
                                 onChange={(v) => onChange({ ...CANAL_VIDE, cible: v })} /> : (
          <label>{libelle}
            <input type="email" inputMode="email" autoComplete="email"
                   required value={canal.cible} onChange={(e) => onChange({ ...CANAL_VIDE, cible: e.target.value })}
                   placeholder="prenom.nom@entreprise.cm" /></label>)}
          <div className="actions"><button>{t("Recevoir un code", "Get a code")}</button></div>
        </form>
      ) : (
        // Une clé propre : sans elle, React réutiliserait le champ de la cible pour le code.
        <form key="code" className="formulaire" onSubmit={verifier}>
          <p>{canal.message}</p>
          <label>{tel ? t("Code reçu par message", "Code received by message") : t("Code reçu par courriel", "Code received by email")}
            <input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required
                   value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" /></label>
          <div className="actions">
            <button className="principal">{t("Vérifier", "Verify")}</button>
            <button type="button" onClick={() => { onChange({ ...canal, codeDemande: false }); setErreur(null); }}>
              {tel ? t("Changer de numéro", "Change number") : t("Changer d'adresse", "Change address")}</button>
          </div>
        </form>
      )}
      <Erreur erreur={erreur} />
    </div>
  );
}
