import { useEffect, useRef, useState, type PointerEvent } from "react";

import { bilan, categorieParlante, categories, confondues, couleur, courbe, ecartRelatif, EGAL, GAIN, MESURES,
  nomsCourts, PERTE, type Mesure, type Variante } from "../comparatif";
import { millions, montant, pct } from "../format";
import { langue, t } from "../i18n";
import { Segments } from "./Echeancier";

const LIBELLE_CATEGORIE = (c: string, n: number) =>
  (c === "*" ? (n === 1 ? t("Tout le personnel", "All staff") : t("Autres salariés", "Other employees")) : c);
const nombre = (x: number, chiffres: number) =>
  x.toLocaleString(langue() === "en" ? "en-GB" : "fr-FR", { maximumFractionDigits: chiffres });
const signe = (v: number, f: (x: number) => string) => (v > 0 ? `+${f(v)}` : v < 0 ? `−${f(-v)}` : f(0));

/** Les régimes simulés, comparés : les chiffres côte à côte, la courbe des mois versés, qui gagne et qui perd.
 *  `variantes[0]` est la convention seule, la référence par défaut. */
export function Comparatif({ variantes }: { variantes: Variante[] }) {
  const [tableau, setTableau] = useState(false);
  if (variantes.length < 2) return null;
  return (
    <div className="comparatif">
      <div className="actions" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ margin: 0 }}>{t("Comparer les régimes", "Compare plans")}</h2>
        <button type="button" className="lien" onClick={() => setTableau(!tableau)}>
          {tableau ? t("Voir les graphiques", "View the charts") : t("Voir le tableau", "View the table")}</button>
      </div>
      <ul className="legende" aria-label={t("Légende", "Legend")}>
        {variantes.map((v, i) => (
          <li key={v.nom}><span className={`cle${i === 0 ? " reference" : ""}`} style={{ background: couleur(i) }} />{v.nom}</li>
        ))}
      </ul>
      {tableau ? <Tableau variantes={variantes} /> : (
        <>
          <Chiffres variantes={variantes} />
          <Courbes variantes={variantes} />
          <GagnantsPerdants variantes={variantes} />
        </>
      )}
    </div>
  );
}

function Chiffres({ variantes }: { variantes: Variante[] }) {
  const [actif, setActif] = useState<string | null>(null);
  const mesures: Mesure[] = ["dette", "charge", "cotisation", "dette_par_salarie"];
  const courts = nomsCourts(variantes.map((v) => v.nom));
  return (
    <div className="carte section">
      <h3>{t("Les chiffres côte à côte", "The figures side by side")}</h3>
      <p className="discret">{t("L'écart se lit contre la convention seule.", "The difference is read against the collective agreement alone.")}</p>
      <div className="petits-multiples">
        {mesures.map((m) => {
          const valeurs = variantes.map(MESURES[m].lire);
          const max = Math.max(...valeurs, 1);
          return (
            <div key={m} className="multiple" aria-label={MESURES[m].libelle}>
              <div className="multiple-titre">{MESURES[m].libelle}</div>
              {variantes.map((v, i) => {
                const cle = `${m}:${i}`;
                const e = ecartRelatif(valeurs[i], valeurs[0]);
                return (
                  <div key={v.nom} className={`rangee${actif === cle ? " active" : ""}`} tabIndex={0}
                       aria-label={t(`${v.nom} : ${montant(valeurs[i])}`, `${v.nom}: ${montant(valeurs[i])}`)}
                       onMouseEnter={() => setActif(cle)} onMouseLeave={() => setActif(null)}
                       onFocus={() => setActif(cle)} onBlur={() => setActif(null)}>
                    <span className="rangee-nom" title={v.nom}>{courts[i]}</span>
                    <span className="rangee-piste">
                      <span className="rangee-barre" style={{ width: `${(valeurs[i] / max) * 100}%`, background: couleur(i) }} />
                    </span>
                    <span className="rangee-valeur">{millions(valeurs[i])}
                      {i > 0 && e !== null && <small>{signe(e, (x) => pct(x, 0))}</small>}</span>
                    {actif === cle && (
                      <div role="tooltip" className="bulle-barre bulle-rangee">
                        <strong>{montant(valeurs[i])}</strong>
                        <div>{v.nom} · {MESURES[m].libelle.toLowerCase()}</div>
                        {i > 0 && (
                          <dl>
                            <dt>{t("Écart", "Difference")}</dt><dd>{signe(valeurs[i] - valeurs[0], montant)}{e !== null ? ` (${signe(e, (x) => pct(x))})` : ""}</dd>
                            <dt>{t("Convention seule", "Collective agreement alone")}</dt><dd>{montant(valeurs[0])}</dd>
                          </dl>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const H = 260, G = 40, HAUT = 16, BAS = 30;

function Courbes({ variantes }: { variantes: Variante[] }) {
  const cats = categories(variantes[0]);
  const [categorie, setCategorie] = useState(() => categorieParlante(variantes));
  const courts = nomsCourts(variantes.map((v) => v.nom));
  const memes = confondues(variantes, categorie);
  const [n, setN] = useState<number | null>(null);
  const zone = useRef<SVGSVGElement>(null);
  const cadre = useRef<HTMLDivElement>(null);
  // Le tracé prend la largeur de sa carte, en pixels : le texte garde sa taille, sur téléphone comme sur écran large.
  const [L, setL] = useState(640);
  useEffect(() => {
    const el = cadre.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const o = new ResizeObserver(([x]) => setL(Math.max(300, Math.round(x.contentRect.width))));
    o.observe(el);
    return () => o.disconnect();
  }, []);
  const D = L < 480 ? 96 : 150;
  const series = variantes.map((v, i) => ({ nom: v.nom, court: courts[i], rang: i, pts: courbe(v, categorie) }));
  const nMax = Math.max(...series.map((s) => s.pts.length - 1), 1);
  const yMax = Math.max(5, Math.ceil(Math.max(...series.flatMap((s) => s.pts)) / 5) * 5);
  const px = (x: number) => G + (x / nMax) * (L - G - D);
  const py = (y: number) => HAUT + (1 - y / yMax) * (H - HAUT - BAS);
  // Les étiquettes au bout des courbes, écartées pour ne pas se chevaucher.
  const bouts = series.map((s) => ({ ...s, y: py(s.pts[s.pts.length - 1] ?? 0) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < bouts.length; i++) bouts[i].y = Math.max(bouts[i].y, bouts[i - 1].y + 13);

  function survol(e: PointerEvent<SVGSVGElement>) {
    const r = zone.current!.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * L;
    setN(Math.min(nMax, Math.max(0, Math.round(((x - G) / (L - G - D)) * nMax))));
  }

  return (
    <div className="carte section">
      <h3>{t("Ce que chaque régime verse au départ", "What each plan pays on departure")}</h3>
      <p className="discret">{t("En mois de salaire, selon l'ancienneté à la retraite ; la convention seule en tirets.",
        "In months of salary, by length of service at retirement; the collective agreement alone is dashed.")}</p>
      {cats.length > 1 && (
        <div className="reglages">
          <Segments nom={t("Catégorie", "Category")} valeur={categorie} onChange={setCategorie}
                    options={cats.map((c) => [c, LIBELLE_CATEGORIE(c, cats.length)] as [string, string])} />
        </div>
      )}
      {memes.length > 0 && (
        <p className="discret">{memes.length === variantes.length - 1 ? t("Tous les régimes versent", "All plans pay")
          : t(`${memes.join(", ")} ${memes.length > 1 ? "versent" : "verse"}`, `${memes.join(", ")} ${memes.length > 1 ? "pay" : "pays"}`)}{" "}
          {t("à cette catégorie exactement ce que verse la convention : les courbes se recouvrent.",
            "this category exactly what the collective agreement pays: the curves overlap.")}</p>
      )}
      <div className="trace-courbes" ref={cadre}>
        <svg ref={zone} viewBox={`0 0 ${L} ${H}`} width={L} height={H} role="img" onPointerMove={survol} onPointerDown={survol}
             onPointerLeave={(e) => e.pointerType === "mouse" && setN(null)}
             aria-label={t(`Mois de salaire versés selon l'ancienneté, ${LIBELLE_CATEGORIE(categorie, cats.length)}`,
               `Months of salary paid by length of service, ${LIBELLE_CATEGORIE(categorie, cats.length)}`)}>
          {[0, yMax / 2, yMax].map((g) => (
            <g key={g}>
              <line x1={G} x2={L - D} y1={py(g)} y2={py(g)} className="grille-ligne" />
              <text x={G - 6} y={py(g) + 4} textAnchor="end" className="axe-texte">{g}</text>
            </g>
          ))}
          {Array.from({ length: Math.floor(nMax / (L < 480 ? 10 : 5)) + 1 }, (_, k) => k * (L < 480 ? 10 : 5)).map((a) => (
            <text key={a} x={px(a)} y={H - BAS + 16} textAnchor="middle" className="axe-texte">{a}</text>
          ))}
          <text x={(G + L - D) / 2} y={H - 2} textAnchor="middle" className="axe-texte">{t("ancienneté (années)", "length of service (years)")}</text>
          {n !== null && <line x1={px(n)} x2={px(n)} y1={HAUT} y2={H - BAS} className="reticule" />}
          {series.map((s) => (
            <path key={s.nom} fill="none" stroke={couleur(s.rang)} strokeWidth={2} strokeLinejoin="round"
                  strokeDasharray={s.rang === 0 ? "5 3" : undefined}
                  d={s.pts.map((y, x) => `${x ? "L" : "M"}${px(x).toFixed(1)},${py(y).toFixed(1)}`).join(" ")} />
          ))}
          {n !== null && series.map((s) => (
            <circle key={s.nom} cx={px(n)} cy={py(s.pts[n] ?? 0)} r={4} fill={couleur(s.rang)} stroke="var(--surface)" strokeWidth={2} />
          ))}
          {bouts.map((b) => (
            <g key={b.nom}>
              <circle cx={px(nMax) + 8} cy={b.y - 4} r={3.5} fill={couleur(b.rang)} />
              <text x={px(nMax) + 15} y={b.y} className="etiquette-courbe">{b.court.length > (L < 480 ? 13 : 20) ? `${b.court.slice(0, L < 480 ? 12 : 19)}…` : b.court}</text>
            </g>
          ))}
        </svg>
        {n !== null && (
          <div role="tooltip" className={`bulle-barre bulle-courbe${L < 480 ? " sous" : ""}`}
               style={{ left: `clamp(0px, ${px(n) < (G + L - D) / 2 ? `${px(n) + 16}px` : `${px(n) - 286}px`}, calc(100% - 270px))` }}>
            <strong>{t(`${n} an${n > 1 ? "s" : ""} d'ancienneté`, `${n} year${n === 1 ? "" : "s"} of service`)}</strong>
            <div>{LIBELLE_CATEGORIE(categorie, cats.length)}</div>
            <ul className="parts">
              {series.map((s) => (
                <li key={s.nom}><span className="trait" style={{ background: couleur(s.rang) }} />
                  <span>{s.nom}</span><b>{nombre(s.pts[n] ?? 0, 2)} {t("mois", "months")}</b></li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function GagnantsPerdants({ variantes }: { variantes: Variante[] }) {
  const cats = categories(variantes[0]);
  const [ref, setRef] = useState(0);
  const [categorie, setCategorie] = useState<string>("");
  const reference = variantes[ref];
  return (
    <div className="carte section">
      <h3>{t("Qui gagne, qui perd", "Who gains, who loses")}</h3>
      <p className="discret">{t("Salarié par salarié, l'indemnité qu'il toucherait à son départ, d'un régime à l'autre.",
        "Employee by employee, the benefit they would receive on departure, from one plan to the other.")}</p>
      <div className="reglages">
        <Segments nom={t("Comparer à", "Compare with")} valeur={ref} onChange={setRef} options={variantes.map((v, i) => [i, v.nom] as [number, string])} />
        {cats.length > 1 && (
          <Segments nom={t("Parmi", "Among")} valeur={categorie} onChange={setCategorie}
                    options={[["", t("Tout le personnel", "All staff")], ...cats.map((c) => [c, LIBELLE_CATEGORIE(c, cats.length)] as [string, string])]} />
        )}
      </div>
      <ul className="legende" aria-label={t("Légende des écarts", "Legend of differences")}>
        <li><span className="cle" style={{ background: GAIN }} />{t("gagnent", "gain")}</li>
        <li><span className="cle" style={{ background: EGAL }} />{t("inchangés", "unchanged")}</li>
        <li><span className="cle" style={{ background: PERTE }} />{t("perdent", "lose")}</li>
      </ul>
      <div className="bilans">
        {variantes.map((v, i) => {
          if (i === ref) return null;
          const b = bilan(reference, v, categorie || undefined);
          const total = b.gagnent + b.inchanges + b.perdent || 1;
          const part = (x: number) => `${(x / total) * 100}%`;
          return (
            <div key={v.nom} className="bilan">
              <div className="bilan-tete"><span className="cle" style={{ background: couleur(i) }} /><b>{v.nom}</b>
                <span className="discret">{t(`face à ${reference.nom}`, `against ${reference.nom}`)}</span></div>
              <div className="barre-bilan" role="img"
                   aria-label={t(`${b.gagnent} gagnent, ${b.inchanges} inchangés, ${b.perdent} perdent`,
                                 `${b.gagnent} gain, ${b.inchanges} unchanged, ${b.perdent} lose`)}>
                {b.perdent > 0 && <span style={{ width: part(b.perdent), background: PERTE }} />}
                {b.inchanges > 0 && <span style={{ width: part(b.inchanges), background: EGAL }} />}
                {b.gagnent > 0 && <span style={{ width: part(b.gagnent), background: GAIN }} />}
              </div>
              <p className="bilan-texte">
                <b>{b.gagnent}</b> {t(`gagne${b.gagnent > 1 ? "nt" : ""}`, b.gagnent === 1 ? "gains" : "gain")}
                {b.gagnent > 0 && <> ({signe(b.gainMoyen, montant)} {t("en moyenne", "on average")})</>}
                {" · "}<b>{b.inchanges}</b> {t(`inchangé${b.inchanges > 1 ? "s" : ""}`, "unchanged")}
                {" · "}<b>{b.perdent}</b> {t(`perd${b.perdent > 1 ? "ent" : ""}`, b.perdent === 1 ? "loses" : "lose")}
                {b.perdent > 0 && <> ({signe(b.perteMoyenne, montant)} {t("en moyenne", "on average")})</>}
              </p>
              <p className="discret bilan-texte">
                {t(`Au total, ${signe(b.ecartTotal, montant)} d'indemnités au départ.`,
                  `In total, ${signe(b.ecartTotal, montant)} in departure benefits.`)}
                {b.plusGrosGain && t(` Plus gros gain : ${b.plusGrosGain.matricule}, ${signe(b.plusGrosGain.montant, montant)}.`,
                  ` Largest gain: ${b.plusGrosGain.matricule}, ${signe(b.plusGrosGain.montant, montant)}.`)}
                {b.plusGrossePerte && t(` Plus grosse perte : ${b.plusGrossePerte.matricule}, ${signe(b.plusGrossePerte.montant, montant)}.`,
                  ` Largest loss: ${b.plusGrossePerte.matricule}, ${signe(b.plusGrossePerte.montant, montant)}.`)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Tableau({ variantes }: { variantes: Variante[] }) {
  const lignes: Mesure[] = ["dette", "charge", "cotisation", "dette_par_salarie", "charge_par_salarie"];
  return (
    <div className="carte section defile">
      <table>
        <thead><tr><th />{variantes.map((v) => <th key={v.nom} className="n">{v.nom}</th>)}</tr></thead>
        <tbody>
          {lignes.map((m) => (
            <tr key={m}><td>{MESURES[m].libelle}</td>
              {variantes.map((v) => <td key={v.nom} className="n">{montant(MESURES[m].lire(v))}</td>)}</tr>
          ))}
          <tr><td>{t("Au-delà de la convention", "Above the collective agreement")}</td>{variantes.map((v) => <td key={v.nom} className="n">{montant(v.ecart_convention)}</td>)}</tr>
          <tr><td>{t("Mois versés à 10 / 20 / 30 ans (première catégorie)", "Months paid at 10 / 20 / 30 years (first category)")}</td>
            {variantes.map((v) => {
              const c = courbe(v, categories(variantes[0])[0]);
              return <td key={v.nom} className="n">{[10, 20, 30].map((a) => nombre(c[a] ?? 0, 1)).join(" / ")}</td>;
            })}</tr>
          {variantes.slice(1).map((v, i) => {
            const b = bilan(variantes[0], v);
            return <tr key={v.nom}><td>{t(`${v.nom} face à la convention seule`, `${v.nom} against the collective agreement alone`)}</td>
              {variantes.map((_, j) => <td key={j} className="n">{j === i + 1 ? t(`${b.gagnent} gagnent, ${b.perdent} perdent`, `${b.gagnent} gain, ${b.perdent} lose`) : ""}</td>)}</tr>;
          })}
        </tbody>
      </table>
    </div>
  );
}
