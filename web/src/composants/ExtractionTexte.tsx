import { useState } from "react";

import { api } from "../api";
import { useDossier } from "../pages/Dossier";
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
    return <p className="discret">La lecture assistée d'un texte existant est réservée pour l'instant aux pays de la CEMAC
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
      <h3>Partir d'un texte existant</h3>
      <p className="discret">Votre accord d'entreprise, une note de la direction, une convention : la plateforme en lit le
        barème de départ à la retraite et vous le propose. Rien n'est enregistré sans votre relecture.</p>
      <div className="actions" style={{ alignItems: "end" }}>
        <label>Le texte (PDF ou texte brut)<input type="file" accept=".pdf,.txt"
          onChange={(e) => { setFichier(e.target.files?.[0] ?? null); setResultat(null); }} /></label>
        <button type="button" disabled={!fichier || (mode.envoie_a_un_tiers && !accord) || enCours} onClick={lire}>
          {enCours ? "Lecture…" : "Lire le texte"}</button>
      </div>
      {mode.envoie_a_un_tiers && (
        <label style={{ display: "flex", gap: 8, fontWeight: 400, marginTop: 8 }}>
          <input type="checkbox" checked={accord} onChange={(e) => setAccord(e.target.checked)} />
          <span>J'accepte que ce texte soit envoyé à Anthropic (Claude{mode.modele ? `, ${mode.modele}` : ""}) pour être lu.
            La plateforme n'en conserve que l'empreinte. N'envoyez pas de document contenant des données personnelles
            de salariés.</span>
        </label>
      )}
      {!mode.envoie_a_un_tiers && <p className="discret">Lecture sur la plateforme, sans envoi à un tiers : seules les
        formulations courantes sont reconnues.</p>}
      <Erreur erreur={erreur} />

      {resultat && (
        <div className="section">
          <Constats constats={resultat.constats} vide="" />
          {resultat.verifications.length > 0 && (
            <div className="defile"><table>
              <thead><tr><th>Valeur</th><th>Passage du texte</th><th>Retrouvé</th></tr></thead>
              <tbody>{resultat.verifications.map((v, i) => (
                <tr key={i}><td><strong>{v.champ}</strong><div className="discret">{resume(v.valeur)}</div></td>
                  <td className="discret">{v.citation ? `« ${v.citation} »` : "—"}</td>
                  <td>{v.retrouvee === true ? <span className="etat bien">✓</span> : v.retrouvee === false
                    ? <span className="etat grave">introuvable</span> : <span className="etat attention">non vérifiable</span>}</td></tr>
              ))}</tbody>
            </table></div>
          )}
          {version && version.categories.length > 0 && (
            <div className="actions">
              <button type="button" className="principal" onClick={() => onReprendre(version)}>Reprendre dans le formulaire</button>
              <span className="discret">Vous relisez, corrigez, puis enregistrez : l'analyse habituelle suit.</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function resume(v: unknown): string {
  if (Array.isArray(v)) {
    return v.map((t: { jusqu_a: number | null; mois_par_annee: number }) =>
      `${Math.round(t.mois_par_annee * 1000) / 10} % ${t.jusqu_a ? `jusqu'à ${t.jusqu_a} ans` : "au-delà"}`).join(" ; ");
  }
  return v === null || v === undefined ? "—" : String(v);
}
