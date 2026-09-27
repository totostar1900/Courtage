import { useState } from "react";

import { api } from "../api";
import { useDossier } from "../pages/Dossier";
import { t } from "../i18n";
import type { ExtractionProposee, ModeExtraction, VersionProposee } from "../types";
import { Constats, Erreur, useCharge } from "./communs";

/** Partir d'un texte existant : la plateforme propose, avec pour chaque valeur le passage d'où elle vient. */
export default function ExtractionTexte({ onReprendre }: { onReprendre: (v: VersionProposee) => void }) {
  const d = useDossier();
  const { donnee: mode } = useCharge(() => api.get<ModeExtraction>("/extraction/mode"), []);
  const [fichier, setFichier] = useState<File | null>(null);
  const [accord, setAccord] = useState(false);
  const [resultat, setResultat] = useState<ExtractionProposee | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  if (!mode) return null;
  if (!(d.org.pays in mode.pays_couverts)) {
    return <p className="discret">{t("La lecture assistée d'un texte existant est réservée pour l'instant aux pays de la CEMAC",
      "Assisted reading of an existing text is currently limited to CEMAC countries")}{" "}
      ({Object.values(mode.pays_couverts).join(", ")}).</p>;
  }

  async function lire() {
    if (!fichier) return;
    const f = new FormData();
    f.append("fichier", fichier);
    f.append("consentement", String(accord));
    setErreur(null); setEnCours(true); setResultat(null);
    try { setResultat(await api.post<ExtractionProposee>(`/organisations/${d.org.id}/regimes/extraction`, f)); }
    catch (e) { setErreur(e); } finally { setEnCours(false); }
  }
  const version = resultat && "categories" in resultat.version ? resultat.version as VersionProposee : null;

  return (
    <div className="carte extraction" style={{ background: "var(--fond)", marginBottom: 14 }}>
      <h3>{t("Partir d'un texte existant", "Start from an existing text")}</h3>
      <p className="discret">{t("Votre accord d'entreprise, une note de la direction, une convention : la plateforme en lit le "
        + "barème de départ à la retraite et vous le propose. Rien n'est enregistré sans votre relecture.",
        "Your company agreement, a management memo, a collective agreement: the platform reads its retirement scale and "
        + "proposes it to you. Nothing is saved without your review.")}</p>
      <div className="actions" style={{ alignItems: "end" }}>
        <label>{t("Le texte (PDF ou texte brut)", "The text (PDF or plain text)")}<input type="file" accept=".pdf,.txt"
          onChange={(e) => { setFichier(e.target.files?.[0] ?? null); setResultat(null); }} /></label>
        <button type="button" disabled={!fichier || (mode.envoie_a_un_tiers && !accord) || enCours} onClick={lire}>
          {enCours ? t("Lecture…", "Reading…") : t("Lire le texte", "Read the text")}</button>
      </div>
      {mode.envoie_a_un_tiers && (
        <label style={{ display: "flex", gap: 8, fontWeight: 400, marginTop: 8 }}>
          <input type="checkbox" checked={accord} onChange={(e) => setAccord(e.target.checked)} />
          <span>{t(`J'accepte que ce texte soit envoyé à Anthropic (Claude${mode.modele ? `, ${mode.modele}` : ""}) pour être lu. `
            + "La plateforme n'en conserve que l'empreinte. N'envoyez pas de document contenant des données personnelles "
            + "de salariés.",
            `I agree that this text be sent to Anthropic (Claude${mode.modele ? `, ${mode.modele}` : ""}) to be read. `
            + "The platform keeps only its fingerprint. Do not send any document containing employees' personal data.")}</span>
        </label>
      )}
      {!mode.envoie_a_un_tiers && <p className="discret">{t("Lecture sur la plateforme, sans envoi à un tiers : seules les "
        + "formulations courantes sont reconnues.",
        "Read on the platform, with nothing sent to a third party: only common wordings are recognised.")}</p>}
      <Erreur erreur={erreur} />

      {resultat && (
        <div className="section">
          <Constats constats={resultat.constats} vide="" />
          {resultat.verifications.length > 0 && (
            <div className="defile"><table>
              <thead><tr><th>{t("Valeur", "Value")}</th><th>{t("Passage du texte", "Passage in the text")}</th><th>{t("Retrouvé", "Found")}</th></tr></thead>
              <tbody>{resultat.verifications.map((v, i) => (
                <tr key={i}><td><strong>{v.champ}</strong><div className="discret">{resume(v.valeur)}</div></td>
                  <td className="discret">{v.citation ? t(`« ${v.citation} »`, `“${v.citation}”`) : "—"}</td>
                  <td>{v.retrouvee === true ? <span className="etat bien">✓</span> : v.retrouvee === false
                    ? <span className="etat grave">{t("introuvable", "not found")}</span> : <span className="etat attention">{t("non vérifiable", "cannot be checked")}</span>}</td></tr>
              ))}</tbody>
            </table></div>
          )}
          {version && version.categories.length > 0 && (
            <div className="actions">
              <button type="button" className="principal" onClick={() => onReprendre(version)}>{t("Reprendre dans le formulaire", "Use in the form")}</button>
              <span className="discret">{t("Vous relisez, corrigez, puis enregistrez : l'analyse habituelle suit.",
                "You review, correct, then save: the usual review follows.")}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function resume(v: unknown): string {
  if (Array.isArray(v)) {
    return v.map((tr: { jusqu_a: number | null; mois_par_annee: number }) =>
      `${Math.round(tr.mois_par_annee * 1000) / 10} % ${tr.jusqu_a ? t(`jusqu'à ${tr.jusqu_a} ans`, `up to ${tr.jusqu_a} years`) : t("au-delà", "beyond")}`).join(" ; ");
  }
  return v === null || v === undefined ? "—" : String(v);
}
