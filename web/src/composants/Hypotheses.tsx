import { useState, type ReactNode } from "react";

import { t as tr } from "../i18n";
import type { CatalogueHypotheses, HypotheseLue, Tranche } from "../types";

/** Les hypothèses telles qu'on les saisit : des pourcentages et des âges en texte, pour taper sans être corrigé. */
export interface SaisieHypotheses {
  taux: Record<string, string>;            // champ → valeur affichée (% ou ans)
  table: string;
  rotation: "uniforme" | "tranches";
  tranches: { des: string; taux: string }[];
}

const TAUX = ["taux_actualisation", "croissance_salaires", "inflation", "taux_turnover", "frais_sur_cotisation"];
const ORDRE = ["taux_actualisation", "croissance_salaires", "inflation", "age_retraite", "taux_turnover",
               "frais_sur_cotisation", "table"];

const enPct = (v: number) => String(Math.round(v * 10000) / 100).replace(".", ",");
const lirePct = (t: string) => Math.round(Number(t.replace(",", ".")) * 10000) / 1000000;
const lireAge = (t: string) => Number(t);

/** La saisie par défaut, ou pré-remplie (par exemple par une rotation proposée par l'expérience réelle). */
export function saisieParDefaut(c: CatalogueHypotheses, depart: Partial<Record<string, number>> = {}): SaisieHypotheses {
  const taux: Record<string, string> = {};
  for (const champ of TAUX) taux[champ] = enPct(depart[champ] ?? Number(c.defauts[champ]));
  taux.age_retraite = String(depart.age_retraite ?? c.defauts.age_retraite);
  const a = c.age_premier_emploi;
  return { taux, table: c.defauts.table, rotation: "uniforme",
           tranches: [{ des: String(a), taux: "6" }, { des: "30", taux: "3" }, { des: "45", taux: "1" }] };
}

/** Ce que l'API reçoit : seulement ce qui s'écarte du référentiel. */
export function aEnvoyer(c: CatalogueHypotheses, s: SaisieHypotheses): Record<string, unknown> {
  const envoi: Record<string, unknown> = {};
  for (const champ of TAUX) {
    if (champ === "taux_turnover" && s.rotation === "tranches") continue;
    const v = lirePct(s.taux[champ]);
    if (v !== Number(c.defauts[champ])) envoi[champ] = v;
  }
  const age = lireAge(s.taux.age_retraite);
  if (age !== c.defauts.age_retraite) envoi.age_retraite = age;
  if (s.table !== c.defauts.table) envoi.table = s.table;
  if (s.rotation === "tranches")
    envoi.rotation_par_age = s.tranches.map((t): Tranche => ({ des: Number(t.des), taux: lirePct(t.taux) }));
  return envoi;
}

/** Les hypothèses de l'étude, repliées : les valeurs du référentiel conviennent à la plupart des études ; qui veut
 *  les régler les trouve toutes ici, avec leur rôle, leur effet et un retour aux valeurs par défaut. */
export function Hypotheses({ catalogue: c, saisie: s, onChange, lues, ouvert }: {
  catalogue: CatalogueHypotheses; saisie: SaisieHypotheses; onChange: (s: SaisieHypotheses) => void;
  /** Les hypothèses lues de la dernière étude : leur effet est mesuré sur l'entreprise. */
  lues?: HypotheseLue[]; ouvert?: boolean;
}) {
  const [explique, setExplique] = useState<string | null>(null);
  const ecarts = Object.keys(aEnvoyer(c, s));
  const champ = (nom: string) => c.champs.find((x) => x.champ === nom)!;
  const taux = (nom: string, v: string) => onChange({ ...s, taux: { ...s.taux, [nom]: v } });
  const tranche = (i: number, cle: "des" | "taux", v: string) =>
    onChange({ ...s, tranches: s.tranches.map((t, j) => (j === i ? { ...t, [cle]: v } : t)) });

  function effet(nom: string): string {
    const mesure = lues?.find((l) => l.champ === nom)?.effet;
    if (mesure && /sur cette étude/.test(mesure)) return mesure.replace("sur cette étude", "sur votre dernière étude");
    if (mesure && /on this study/.test(mesure)) return mesure.replace("on this study", "on your latest study");
    return champ(nom).effet.replace("{effet}", "");
  }

  function explication(nom: string) {
    const x = champ(nom === "taux_turnover" && s.rotation === "tranches" ? "rotation_par_age" : nom);
    return (
      <div className="explication" id={`explication-${nom}`}>
        <p><b>{tr("À quoi elle sert.", "What it is for.")}</b> {x.role}</p>
        <p><b>{tr("Son effet.", "Its effect.")}</b> {nom === x.champ ? effet(nom) : x.effet.replace("{effet}", "")}</p>
        <p><b>{tr("Comment la fixer.", "How to set it.")}</b> {x.fixer}</p>
        <p><b>{tr("À regarder avec elle.", "Look at it alongside.")}</b> {x.avec}</p>
      </div>
    );
  }

  function ligne(nom: string, saisie: ReactNode, defaut: string) {
    const ecarte = ecarts.includes(nom) || (nom === "taux_turnover" && ecarts.includes("rotation_par_age"));
    return (
      <div key={nom} className={`hypothese-ligne${ecarte ? " ecartee" : ""}`}>
        <div className="hypothese-tete">
          <span className="hypothese-nom">{champ(nom).libelle}</span>
          <span className="hypothese-saisie">{saisie}</span>
          <span className="discret hypothese-defaut">{tr("par défaut", "default")} {defaut}</span>
          <button type="button" className="lien hypothese-lien" aria-expanded={explique === nom} aria-controls={`explication-${nom}`}
                  onClick={() => setExplique(explique === nom ? null : nom)}>
            {explique === nom ? tr("Refermer", "Close") : tr("Comprendre", "Explain")}</button>
        </div>
        {explique === nom && explication(nom)}
      </div>
    );
  }

  return (
    <details className="hypotheses section" open={ouvert}>
      <summary>
        <span className="chevron" aria-hidden="true" />
        <span>{tr("Hypothèses", "Assumptions")}</span>
        <span className={`etat ${ecarts.length ? "attention" : "bien"}`}>
          {ecarts.length ? tr(`${ecarts.length} ajustée${ecarts.length > 1 ? "s" : ""}`, `${ecarts.length} adjusted`)
            : tr("valeurs par défaut", "default values")}</span>
      </summary>
      <div className="hypotheses-corps">
        <div className="hypotheses-intro">
          <p className="discret">{tr("Les valeurs par défaut conviennent à la plupart des études. S'en écarter demande une "
            + "justification, qui figure au rapport.", "The default values suit most studies. Departing from them requires a "
            + "justification, which appears in the report.")}</p>
          <button type="button" className="secondaire" disabled={!ecarts.length}
                  onClick={() => onChange(saisieParDefaut(c))}>{tr("Revenir aux valeurs par défaut", "Reset to default values")}</button>
        </div>
        {ORDRE.map((nom) => {
          const x = champ(nom);
          if (nom === "table") return ligne(nom, (
            <select aria-label={x.libelle} value={s.table} onChange={(e) => onChange({ ...s, table: e.target.value })}>
              {c.tables.map((t) => <option key={t.code} value={t.code} disabled={!t.disponible}>
                {t.libelle}{t.disponible ? "" : ` — ${t.raison ?? tr("indisponible", "unavailable")}`}</option>)}
            </select>), c.tables.find((t) => t.code === c.defauts.table)?.libelle ?? c.defauts.table);
          if (nom === "age_retraite") return ligne(nom, (
            <span className="unite"><input aria-label={x.libelle} type="number" min={x.min ?? undefined} max={x.max ?? undefined}
              step={1} value={s.taux.age_retraite} onChange={(e) => taux(nom, e.target.value)} /> {tr("ans", "years")}</span>),
            tr(`${c.defauts.age_retraite} ans`, `${c.defauts.age_retraite} years`));
          const pct = (
            <span className="unite"><input aria-label={x.libelle} type="text" inputMode="decimal" value={s.taux[nom]}
              onChange={(e) => taux(nom, e.target.value)} /> %</span>);
          if (nom !== "taux_turnover") return ligne(nom, pct, `${enPct(Number(c.defauts[nom]))} %`);
          return (
            <div key={nom}>
              {ligne(nom, (
                <span className="rotation">
                  <span className="segments" role="radiogroup" aria-label={tr("Rotation", "Staff turnover")}>
                    {(["uniforme", "tranches"] as const).map((m) => (
                      <button key={m} type="button" role="radio" aria-checked={s.rotation === m}
                              className={s.rotation === m ? "actif" : ""} onClick={() => onChange({ ...s, rotation: m })}>
                        {m === "uniforme" ? tr("Uniforme", "Uniform") : tr("Par tranche d'âge", "By age band")}</button>))}
                  </span>
                  {s.rotation === "uniforme" && pct}
                </span>), tr(`${enPct(c.defauts.taux_turnover)} % à tout âge`, `${enPct(c.defauts.taux_turnover)}% at all ages`))}
              {s.rotation === "tranches" && (
                <div className="tranches">
                  {s.tranches.map((t, i) => (
                    <div key={i} className="tranche">
                      <span>{i === 0 ? tr("De", "From") : tr("Dès", "From")}</span>
                      <input aria-label={tr(`Tranche ${i + 1} : âge de début`, `Band ${i + 1}: starting age`)} type="number" value={t.des} disabled={i === 0}
                             min={c.age_premier_emploi} onChange={(e) => tranche(i, "des", e.target.value)} />
                      <span>{tr("ans :", "years:")}</span>
                      <input aria-label={tr(`Tranche ${i + 1} : taux`, `Band ${i + 1}: rate`)} type="text" inputMode="decimal" value={t.taux}
                             onChange={(e) => tranche(i, "taux", e.target.value)} />
                      <span>{tr("% l'an", "% a year")}{i === s.tranches.length - 1
                        ? <span className="discret">{tr(" jusqu'à la retraite", " until retirement")}</span> : ""}</span>
                      {i === 0 ? <span /> : <button type="button" className="lien" aria-label={tr(`Retirer la tranche ${i + 1}`, `Remove band ${i + 1}`)}
                        onClick={() => onChange({ ...s, tranches: s.tranches.filter((_, j) => j !== i) })}>{tr("Retirer", "Remove")}</button>}
                    </div>
                  ))}
                  {s.tranches.length < 6 && (
                    <button type="button" className="lien" onClick={() => {
                      const dernier = Number(s.tranches[s.tranches.length - 1].des);
                      onChange({ ...s, tranches: [...s.tranches, { des: String(dernier + 10), taux: "0" }] });
                    }}>{tr("+ Ajouter une tranche", "+ Add a band")}</button>)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </details>
  );
}
