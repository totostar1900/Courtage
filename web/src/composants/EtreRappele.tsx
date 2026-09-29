import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { t } from "../i18n";
import { Erreur } from "./communs";
import { ChampTelephone } from "./ChampTelephone";

/** « Être rappelé » : pour qui préfère parler à quelqu'un avant d'essayer. Le champ « site web » est un piège à
 *  robots, caché à l'œil et aux lecteurs d'écran. */
export default function EtreRappele() {
  const [accord, setAccord] = useState(false);
  const [merci, setMerci] = useState<string | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [envoi, setEnvoi] = useState(false);
  async function envoyer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const x = (k: string) => String(f.get(k) ?? "").trim();
    setErreur(null);
    setEnvoi(true);
    try {
      const r = await api.post<{ message: string }>("/public/rappel", { nom: x("nom"), entreprise: x("entreprise"),
        telephone: x("telephone"), courriel: x("courriel") || null, creneau: x("creneau"), message: x("message") || null,
        accord, site_web: x("site_web") || null });
      setMerci(r.message);
    } catch (e) { setErreur(e); setEnvoi(false); }
  }
  if (merci) return <p className="constat informe" role="status">{merci}</p>;
  return (
    <form className="formulaire" onSubmit={envoyer} aria-label={t("Être rappelé", "Be called back")}>
      <div className="grille-2">
        <label>{t("Votre nom", "Your name")}<input name="nom" required minLength={2} autoComplete="name" /></label>
        <label>{t("Entreprise", "Company")}<input name="entreprise" required minLength={2} autoComplete="organization" /></label>
        <ChampTelephone libelle={t("Téléphone", "Phone")} name="telephone" required />
        <label>{t("Courriel (facultatif)", "Email (optional)")}<input name="courriel" type="email" autoComplete="email" /></label>
        <label>{t("Quand vous appeler ?", "When should we call?")}
          <select name="creneau" defaultValue="indifferent">
            <option value="matin">{t("Le matin", "In the morning")}</option>
            <option value="apres_midi">{t("L'après-midi", "In the afternoon")}</option>
            <option value="indifferent">{t("Indifférent", "Any time")}</option>
          </select></label>
      </div>
      <label>{t("Votre question (facultatif)", "Your question (optional)")}<textarea name="message" maxLength={1000} rows={3} /></label>
      <div className="piege" aria-hidden="true"><label>Site web<input name="site_web" tabIndex={-1} autoComplete="off" /></label></div>
      <label className="case"><input type="checkbox" checked={accord} onChange={(e) => setAccord(e.target.checked)} />{" "}
        <span>{t("J'accepte d'être rappelé au sujet de cette demande. ", "I agree to be called back about this request. ")}
          <Link to="/confidentialite">{t("Confidentialité", "Privacy")}</Link></span></label>
      <div className="actions"><button className="principal" disabled={!accord || envoi}>{t("Être rappelé", "Be called back")}</button></div>
      <Erreur erreur={erreur} />
    </form>
  );
}
