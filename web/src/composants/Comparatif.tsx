import { useEffect, useRef, useState, type PointerEvent } from "react";

import { bilan, categorieParlante, categories, confondues, couleur, courbe, ecartRelatif, EGAL, GAIN, MESURES,
  nomsCourts, PERTE, type Mesure, type Variante } from "../comparatif";
import { millions, montant, pct } from "../format";
import { Segments } from "./Echeancier";

const LIBELLE_CATEGORIE = (c: string, n: number) => (c === "*" ? (n === 1 ? "Tout le personnel" : "Autres salariés") : c);
const signe = (v: number, f: (x: number) => string) => (v > 0 ? `+${f(v)}` : v < 0 ? `−${f(-v)}` : f(0));

/** Les régimes simulés, comparés : les chiffres côte à côte, la courbe des mois versés, qui gagne et qui perd.
 *  `variantes[0]` est la convention seule, la référence par défaut. */
export function Comparatif({ variantes }: { variantes: Variante[] }) {
  const [tableau, setTableau] = useState(false);
  if (variantes.length < 2) return null;
  return (
    <div className="comparatif">
      <div className="actions" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ margin: 0 }}>Comparer les régimes</h2>
        <button type="button" className="lien" onClick={() => setTableau(!tableau)}>
          {tableau ? "Voir les graphiques" : "Voir le tableau"}</button>
      </div>
      <ul className="legende" aria-label="Légende">
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
      <h3>Les chiffres côte à côte</h3>
      <p className="discret">L'écart se lit contre la convention seule.</p>
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
                       aria-label={`${v.nom} : ${montant(valeurs[i])}`}
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
                            <dt>Écart</dt><dd>{signe(valeurs[i] - valeurs[0], montant)}{e !== null ? ` (${signe(e, (x) => pct(x))})` : ""}</dd>
                            <dt>Convention seule</dt><dd>{montant(valeurs[0])}</dd>
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
      <h3>Ce que chaque régime verse au départ</h3>
      <p className="discret">En mois de salaire, selon l'ancienneté à la retraite ; la convention seule en tirets.</p>
      {cats.length > 1 && (
        <div className="reglages">
          <Segments nom="Catégorie" valeur={categorie} onChange={setCategorie}
                    options={cats.map((c) => [c, LIBELLE_CATEGORIE(c, cats.length)] as [string, string])} />
        </div>
      )}
      {memes.length > 0 && (
        <p className="discret">{memes.length === variantes.length - 1 ? "Tous les régimes versent" : `${memes.join(", ")} ${memes.length > 1 ? "versent" : "verse"}`}{" "}
          à cette catégorie exactement ce que verse la convention : les courbes se recouvrent.</p>
      )}
      <div className="trace-courbes" ref={cadre}>
        <svg ref={zone} viewBox={`0 0 ${L} ${H}`} width={L} height={H} role="img" onPointerMove={survol} onPointerDown={survol}
             onPointerLeave={(e) => e.pointerType === "mouse" && setN(null)}
             aria-label={`Mois de salaire versés selon l'ancienneté, ${LIBELLE_CATEGORIE(categorie, cats.length)}`}>
          {[0, yMax / 2, yMax].map((g) => (
            <g key={g}>
              <line x1={G} x2={L - D} y1={py(g)} y2={py(g)} className="grille-ligne" />
              <text x={G - 6} y={py(g) + 4} textAnchor="end" className="axe-texte">{g}</text>
            </g>
          ))}
          {Array.from({ length: Math.floor(nMax / (L < 480 ? 10 : 5)) + 1 }, (_, k) => k * (L < 480 ? 10 : 5)).map((a) => (
            <text key={a} x={px(a)} y={H - BAS + 16} textAnchor="middle" className="axe-texte">{a}</text>
          ))}
          <text x={(G + L - D) / 2} y={H - 2} textAnchor="middle" className="axe-texte">ancienneté (années)</text>
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
            <strong>{n} an{n > 1 ? "s" : ""} d'ancienneté</strong>
            <div>{LIBELLE_CATEGORIE(categorie, cats.length)}</div>
            <ul className="parts">
              {series.map((s) => (
                <li key={s.nom}><span className="trait" style={{ background: couleur(s.rang) }} />
                  <span>{s.nom}</span><b>{(s.pts[n] ?? 0).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} mois</b></li>
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
      <h3>Qui gagne, qui perd</h3>
      <p className="discret">Salarié par salarié, l'indemnité qu'il toucherait à son départ, d'un régime à l'autre.</p>
      <div className="reglages">
        <Segments nom="Comparer à" valeur={ref} onChange={setRef} options={variantes.map((v, i) => [i, v.nom] as [number, string])} />
        {cats.length > 1 && (
          <Segments nom="Parmi" valeur={categorie} onChange={setCategorie}
                    options={[["", "Tout le personnel"], ...cats.map((c) => [c, LIBELLE_CATEGORIE(c, cats.length)] as [string, string])]} />
        )}
      </div>
      <ul className="legende" aria-label="Légende des écarts">
        <li><span className="cle" style={{ background: GAIN }} />gagnent</li>
        <li><span className="cle" style={{ background: EGAL }} />inchangés</li>
        <li><span className="cle" style={{ background: PERTE }} />perdent</li>
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
                <span className="discret">face à {reference.nom}</span></div>
              <div className="barre-bilan" role="img"
                   aria-label={`${b.gagnent} gagnent, ${b.inchanges} inchangés, ${b.perdent} perdent`}>
                {b.perdent > 0 && <span style={{ width: part(b.perdent), background: PERTE }} />}
                {b.inchanges > 0 && <span style={{ width: part(b.inchanges), background: EGAL }} />}
                {b.gagnent > 0 && <span style={{ width: part(b.gagnent), background: GAIN }} />}
              </div>
              <p className="bilan-texte">
                <b>{b.gagnent}</b> gagne{b.gagnent > 1 ? "nt" : ""}{b.gagnent > 0 && <> ({signe(b.gainMoyen, montant)} en moyenne)</>}
                {" · "}<b>{b.inchanges}</b> inchangé{b.inchanges > 1 ? "s" : ""}
                {" · "}<b>{b.perdent}</b> perd{b.perdent > 1 ? "ent" : ""}{b.perdent > 0 && <> ({signe(b.perteMoyenne, montant)} en moyenne)</>}
              </p>
              <p className="discret bilan-texte">
                Au total, {signe(b.ecartTotal, montant)} d'indemnités au départ.
                {b.plusGrosGain && <> Plus gros gain : {b.plusGrosGain.matricule}, {signe(b.plusGrosGain.montant, montant)}.</>}
                {b.plusGrossePerte && <> Plus grosse perte : {b.plusGrossePerte.matricule}, {signe(b.plusGrossePerte.montant, montant)}.</>}
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
          <tr><td>Au-delà de la convention</td>{variantes.map((v) => <td key={v.nom} className="n">{montant(v.ecart_convention)}</td>)}</tr>
          <tr><td>Mois versés à 10 / 20 / 30 ans (première catégorie)</td>
            {variantes.map((v) => {
              const c = courbe(v, categories(variantes[0])[0]);
              return <td key={v.nom} className="n">{[10, 20, 30].map((a) => (c[a] ?? 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 })).join(" / ")}</td>;
            })}</tr>
          {variantes.slice(1).map((v, i) => {
            const b = bilan(variantes[0], v);
            return <tr key={v.nom}><td>{v.nom} face à la convention seule</td>
              {variantes.map((_, j) => <td key={j} className="n">{j === i + 1 ? `${b.gagnent} gagnent, ${b.perdent} perdent` : ""}</td>)}</tr>;
          })}
        </tbody>
      </table>
    </div>
  );
}
