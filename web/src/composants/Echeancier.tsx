import { useEffect, useRef, useState } from "react";

import { construire, epuisement, graduations, HORIZON_MAX, MESURES, reperesAnnees, type Decoupage, type Horizon, type Lecture,
  type Mesure } from "../echeancier";
import { montant, pct } from "../format";
import type { Annee } from "../types";

const HAUTEUR = 180;           // px : la zone des barres
const LARGEUR_BULLE = 270;

function compact(v: number, enMontant: boolean): string {
  if (!enMontant) return v.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
  if (v >= 1e9) return `${(v / 1e9).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} Md`;
  if (v >= 1e6) return `${(v / 1e6).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} M`;
  if (v >= 1e3) return `${(v / 1e3).toLocaleString("fr-FR", { maximumFractionDigits: 0 })} k`;
  return String(Math.round(v));
}

function Segments<T extends string | number>({ nom, valeur, options, onChange, desactive }: {
  nom: string; valeur: T; options: [T, string][]; onChange: (v: T) => void; desactive?: (v: T) => string | null;
}) {
  return (
    <div className="segments" role="radiogroup" aria-label={nom}>
      <span className="segments-nom">{nom}</span>
      {options.map(([v, l]) => {
        const raison = desactive?.(v) ?? null;
        return (
          <button key={String(v)} type="button" role="radio" aria-checked={v === valeur} disabled={Boolean(raison)}
                  title={raison ?? undefined} className={v === valeur ? "actif" : ""} onClick={() => onChange(v)}>{l}</button>
        );
      })}
    </div>
  );
}

/** L'échéancier des départs, modulable : la mesure, la lecture (annuelle ou cumulée), le découpage par
 *  catégorie et l'horizon ; en cumulé, le fonds constitué en repère. Une bulle par barre, un tableau. */
export function Echeancier({ annees, fonds }: { annees: Annee[]; fonds?: number | null }) {
  const [mesure, setMesure] = useState<Mesure>("prestations_probables");
  const [lecture, setLecture] = useState<Lecture>("annuelle");
  const [decoupage, setDecoupage] = useState<Decoupage>("ensemble");
  const [horizonChoisi, setHorizon] = useState<Horizon | null>(null);   // null : jusqu'à 30 ans, ou tout s'il est plus court
  const [tableau, setTableau] = useState(false);
  const [actif, setActif] = useState<number | null>(null);
  const graphique = useRef<HTMLDivElement>(null);
  const [largeur, setLargeur] = useState(0);
  useEffect(() => { if (actif !== null && graphique.current) setLargeur(graphique.current.clientWidth); }, [actif]);
  if (!annees.length) return null;

  const enMontant = MESURES[mesure].montant;
  const nbAnnees = annees.length ? annees[annees.length - 1].annee - annees[0].annee + 1 : 0;
  const plafond = Math.min(HORIZON_MAX, nbAnnees);
  const horizon: number = Math.min(typeof horizonChoisi === "number" ? horizonChoisi : plafond, plafond);
  const vue = construire(annees, mesure, lecture, decoupage, horizon);
  const repere = lecture === "cumulee" && enMontant && fonds ? fonds : null;
  const echelle = graduations(Math.max(vue.max, repere ?? 0));
  const haut = echelle[2];
  const epuise = repere ? epuisement(vue.colonnes, repere) : null;
  const totalGeneral = construire(annees, mesure, "annuelle", "ensemble", "tout").colonnes.reduce((t, c) => t + c.total, 0) || 1;
  const cumuls = construire(annees, mesure, "cumulee", "ensemble", "tout").colonnes;
  const plusieurs = vue.series.length > 1;
  const valeur = (v: number) => (enMontant ? montant(v) : `${v}`);
  const departs = (n: number) => `${n} départ${n > 1 ? "s" : ""}${lecture === "cumulee" ? " cumulés" : " à la retraite"}`;

  const c = actif === null ? null : vue.colonnes[actif];
  const centre = actif === null ? 0 : ((actif + 0.5) / vue.colonnes.length) * largeur;
  const gauche = Math.min(Math.max(centre - LARGEUR_BULLE / 2, 0), Math.max(largeur - LARGEUR_BULLE, 0));
  const ensembleOriginal = c ? annees.find((a) => a.annee === c.annee) : undefined;

  return (
    <div className="echeancier">
      <div className="reglages">
        <Segments nom="Mesure" valeur={mesure} onChange={setMesure}
                  options={(Object.keys(MESURES) as Mesure[]).map((m) => [m, MESURES[m].court])} />
        <Segments nom="Lecture" valeur={lecture} onChange={setLecture} options={[["annuelle", "Par année"], ["cumulee", "Cumulée"]]} />
        <Segments nom="Découpage" valeur={decoupage} onChange={setDecoupage}
                  options={[["ensemble", "Ensemble"], ["categorie", "Par catégorie"]]}
                  desactive={(v) => (v === "categorie" && !vue.decoupageDisponible
                    ? "Cette étude a été calculée avant le découpage par catégorie." : null)} />
        <label className="segments curseur-horizon">
          <span className="segments-nom">Horizon</span>
          <input type="range" min={1} max={plafond} value={horizon} aria-label="Horizon en années"
                 onChange={(e) => setHorizon(Number(e.target.value))} />
          <output>{horizon} an{horizon > 1 ? "s" : ""}</output>
        </label>
      </div>

      <p className="sous-titre">{MESURES[mesure].libelle}{lecture === "cumulee" ? ", cumulées depuis " + annees[0].annee : ", par année"}
        {plusieurs ? ", par catégorie" : ""}{horizon < nbAnnees ? ` · les ${horizon} premières années` : ""}</p>
      {plusieurs && (
        <ul className="legende" aria-label="Légende">
          {vue.series.map((s) => <li key={s.cle}><span className="cle" style={{ background: s.couleur }} />{s.libelle}</li>)}
        </ul>
      )}

      {tableau ? (
        <div className="defile">
          <table>
            <thead><tr><th>Année</th>{vue.series.map((s) => <th key={s.cle} className="n">{s.libelle}</th>)}
              {plusieurs && <th className="n">Total</th>}</tr></thead>
            <tbody>{vue.colonnes.filter((col) => col.total > 0).map((col) => (
              <tr key={col.annee}><td>{col.annee}</td>
                {vue.series.map((s) => <td key={s.cle} className="n">{valeur(col.valeurs[s.cle])}</td>)}
                {plusieurs && <td className="n">{valeur(col.total)}</td>}</tr>
            ))}</tbody>
          </table>
        </div>
      ) : (
        <div className="trace" onMouseLeave={() => setActif(null)}>
          <div className="axe-y" aria-hidden="true">
            {echelle.map((g) => (
              <div key={g} className="graduation" style={{ bottom: (g / haut) * HAUTEUR }}>
                <span>{compact(g, enMontant)}</span>
              </div>
            ))}
            {repere && (
              <div className="repere" style={{ bottom: (repere / haut) * HAUTEUR }}>
                <span>Fonds constitué {compact(repere, true)}</span>
              </div>
            )}
          </div>
          <div className="barres" ref={graphique} style={{ height: HAUTEUR }}
               aria-label={`${MESURES[mesure].libelle} ${lecture === "cumulee" ? "cumulées" : "par année"}`}>
            {vue.colonnes.map((col, i) => (
              <button key={col.annee} type="button" className={`barre${i === actif ? " active" : ""}`}
                      style={{ height: `${(col.total / haut) * 100}%` }}
                      aria-label={`${col.annee} : ${col.effectif ? departs(col.effectif).replace(/ à la retraite| cumulés/, "") : "aucun départ"}, ${valeur(col.total)}`}
                      aria-describedby={i === actif ? "echeancier-bulle" : undefined}
                      onMouseEnter={() => setActif(i)} onFocus={() => setActif(i)} onBlur={() => setActif(null)}
                      onClick={() => setActif(i)} onKeyDown={(e) => e.key === "Escape" && setActif(null)}>
                {vue.series.map((s) => col.valeurs[s.cle] > 0 && (
                  <span key={s.cle} className="segment" style={{ flexGrow: col.valeurs[s.cle], background: s.couleur }} />
                ))}
              </button>
            ))}
          </div>
          {c && actif !== null && (
            <div role="tooltip" id="echeancier-bulle" className="bulle-barre"
                 style={{ left: gauche + 44, bottom: (c.total / haut) * HAUTEUR + 30,
                          ["--fleche" as string]: `${Math.min(Math.max(centre - gauche, 14), LARGEUR_BULLE - 14)}px` }}>
              <strong>{c.annee}</strong>
              {c.effectif === 0 && c.total === 0 ? <div>Aucun départ à la retraite prévu</div> : (
                <>
                  <div>{departs(c.effectif)}</div>
                  {plusieurs && (
                    <ul className="parts">
                      {vue.series.map((s) => (
                        <li key={s.cle}><span className="trait" style={{ background: s.couleur }} />
                          <span>{s.libelle}</span><b>{valeur(c.valeurs[s.cle])}</b></li>
                      ))}
                    </ul>
                  )}
                  {lecture === "annuelle" && ensembleOriginal ? (
                    <dl>
                      <dt>Prestations probables</dt><dd>{montant(ensembleOriginal.prestations_probables ?? ensembleOriginal.ifc)}</dd>
                      <dt>Si tous partent</dt><dd>{montant(ensembleOriginal.ifc)}</dd>
                      <dt>Valeur actuelle</dt><dd>{montant(ensembleOriginal.vapf)}</dd>
                      <dt>Part du total</dt><dd>{pct((mesure === "effectif" ? ensembleOriginal.effectif : c.total) / totalGeneral)}</dd>
                      <dt>Cumul depuis {annees[0].annee}</dt>
                      <dd>{valeur(cumuls.find((x) => x.annee === c.annee)?.total ?? 0)}</dd>
                    </dl>
                  ) : (
                    <dl>
                      <dt>{MESURES[mesure].libelle}{lecture === "cumulee" ? ", cumul" : ""}</dt><dd>{valeur(c.total)}</dd>
                      {repere && <><dt>Fonds constitué</dt><dd>{montant(repere)}</dd>
                        <dt>{c.total > repere ? "Au-delà du fonds" : "Reste du fonds"}</dt><dd>{montant(Math.abs(repere - c.total))}</dd></>}
                    </dl>
                  )}
                  <p className="discret">Probables : l'indemnité pondérée par la chance d'être en vie et encore dans
                    l'entreprise ce jour-là. Valeur actuelle : ce que ce versement futur vaut aujourd'hui.</p>
                </>
              )}
            </div>
          )}
          <div className="axe-annees" aria-hidden="true">
            {(() => { const reperes = reperesAnnees(vue.colonnes.map((col) => col.annee));
              return vue.colonnes.map((col) => <span key={col.annee}>{reperes.has(col.annee) ? col.annee : ""}</span>); })()}
          </div>
        </div>
      )}

      <div className="actions echeancier-pied">
        {repere && (
          <span className="discret">{epuise === null ? "Le fonds constitué couvre tous les départs affichés."
            : epuise === vue.colonnes[0].annee ? <>Dès <b>{epuise}</b>, les versements dépassent le fonds constitué.</>
            : <>Le fonds constitué couvre les départs jusqu'en <b>{epuise - 1}</b> ; au-delà, les versements le dépassent.</>}</span>
        )}
        <button type="button" className="lien" onClick={() => { setTableau(!tableau); setActif(null); }}>
          {tableau ? "Voir le graphique" : "Voir le tableau"}</button>
      </div>
    </div>
  );
}
