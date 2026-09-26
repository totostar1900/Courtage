import { useMemo, useState } from "react";
import { Link, NavLink, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { oublierVisite } from "../composants/Visite";
import { dateFr } from "../format";
import { ASTUCES } from "../guide/astuces";
import { CHAPITRES, GROUPES, type Chapitre } from "../guide/chapitres";
import { GLOSSAIRE } from "../guide/glossaire";
import { LECONS, type Lecon } from "../guide/lecons";

// Le guide : public (rien d'un client n'y figure), lisible avant même d'avoir un compte.
// /guide/<chapitre>, /guide/lecons[/<id>], /guide/conventions, /guide/glossaire, /guide/astuces.

const plat = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export default function Guide() {
  const chemin = useParams()["*"] ?? "";
  const [recherche, setRecherche] = useState("");
  const [section, sous] = chemin.split("/");
  const chapitre = CHAPITRES.find((c) => c.id === (section || "bienvenue"));

  return (
    <div className="guide">
      <nav className="guide-nav" aria-label="Sommaire du guide">
        <input type="search" placeholder="Chercher dans le guide…" value={recherche} aria-label="Chercher dans le guide"
               onChange={(e) => setRecherche(e.target.value)} />
        {GROUPES.map((g) => (
          <div key={g}>
            <div className="guide-groupe">{g}</div>
            {CHAPITRES.filter((c) => c.groupe === g).map((c) => (
              <NavLink key={c.id} to={`/guide/${c.id}`} onClick={() => setRecherche("")}
                       className={({ isActive }) => (isActive || (!section && c.id === "bienvenue") ? "actif" : "")}>{c.titre}</NavLink>
            ))}
          </div>
        ))}
        <div className="guide-groupe">Apprendre</div>
        <NavLink to="/guide/lecons" onClick={() => setRecherche("")}>Leçons rapides</NavLink>
        <NavLink to="/guide/astuces" onClick={() => setRecherche("")}>Le saviez-vous ?</NavLink>
        <NavLink to="/guide/glossaire" onClick={() => setRecherche("")}>Glossaire</NavLink>
        <NavLink to="/guide/conventions-preremplies" onClick={() => setRecherche("")}>Consulter les conventions</NavLink>
      </nav>
      <article className="guide-texte">
        {recherche.trim() ? <Resultats q={recherche} />
          : section === "lecons" ? (sous ? <UneLecon id={sous} /> : <Lecons />)
          : section === "glossaire" ? <Glossaire />
          : section === "astuces" ? <Astuces />
          : section === "conventions-preremplies" ? <Conventions />
          : chapitre ? <UnChapitre c={chapitre} />
          : <p>Ce chapitre n'existe pas. <Link to="/guide">Retour au guide</Link></p>}
      </article>
    </div>
  );
}

function UnChapitre({ c }: { c: Chapitre }) {
  const naviguer = useNavigate();
  const i = CHAPITRES.indexOf(c);
  const [prec, suiv] = [CHAPITRES[i - 1], CHAPITRES[i + 1]];
  return (
    <>
      <div className="discret">{c.groupe}</div>
      <h1>{c.titre}</h1>
      <p className="guide-resume">{c.resume}</p>
      {c.sections.map((s) => (
        <section key={s.titre} className="section">
          <h2>{s.titre}</h2>
          {s.texte.map((t, k) => <p key={k}>{t}</p>)}
        </section>
      ))}
      {c.id === "conventions" && <p><Link to="/guide/conventions-preremplies">Consulter les conventions préremplies →</Link></p>}
      {c.id === "bienvenue" && (
        <div className="carte section">
          <h3>Première visite ?</h3>
          <p>Une visite guidée de votre dossier, en six bulles, et cinq leçons de deux minutes.</p>
          <div className="actions">
            <button className="principal" onClick={() => { oublierVisite(); naviguer("/"); }}>Revoir la visite guidée</button>
            <Link to="/guide/lecons"><button>Les leçons rapides</button></Link>
          </div>
        </div>
      )}
      {!!c.termes?.length && (
        <section className="section carte">
          <h3>Les mots de ce chapitre</h3>
          <dl className="definitions">
            {c.termes.map((t) => <div key={t}><dt>{GLOSSAIRE[t].terme}</dt><dd>{GLOSSAIRE[t].definition}</dd></div>)}
          </dl>
        </section>
      )}
      <div className="actions section guide-suite">
        {prec ? <Link to={`/guide/${prec.id}`}>← {prec.titre}</Link> : <span />}
        {suiv && <Link to={`/guide/${suiv.id}`}>{suiv.titre} →</Link>}
      </div>
    </>
  );
}

// --- Leçons rapides ------------------------------------------------------------------

const CLE_LECONS = "courtage:lecons-faites";
function leconsFaites(): string[] { try { return JSON.parse(localStorage.getItem(CLE_LECONS) ?? "[]"); } catch { return []; } }

function Lecons() {
  const faites = leconsFaites();
  return (
    <>
      <h1>Leçons rapides</h1>
      <p className="guide-resume">Deux ou trois minutes chacune, et une question pour vérifier.
        {" "}{faites.length}/{LECONS.length} faites.</p>
      <div className="grille g2">
        {LECONS.map((l) => (
          <Link key={l.id} to={`/guide/lecons/${l.id}`} className="carte lien">
            <div className="discret">{l.duree} · {l.pour}{faites.includes(l.id) && " · ✓ faite"}</div>
            <h3 style={{ marginTop: 6 }}>{l.titre}</h3>
            <div className="discret">{l.etapes.length} écrans et une question</div>
          </Link>
        ))}
      </div>
    </>
  );
}

function UneLecon({ id }: { id: string }) {
  const l = LECONS.find((x) => x.id === id);
  if (!l) return <p>Leçon introuvable. <Link to="/guide/lecons">Toutes les leçons</Link></p>;
  return <Deroule key={l.id} l={l} />;
}

function Deroule({ l }: { l: Lecon }) {
  const [n, setN] = useState(0);
  const [choix, setChoix] = useState<number | null>(null);
  const quiz = n === l.etapes.length;
  const repondre = (k: number) => {
    setChoix(k);
    if (k === l.quiz.bonne) {
      const f = leconsFaites();
      if (!f.includes(l.id)) try { localStorage.setItem(CLE_LECONS, JSON.stringify([...f, l.id])); } catch { /* rien */ }
    }
  };
  const suivante = LECONS[LECONS.indexOf(l) + 1];
  return (
    <>
      <div className="discret"><Link to="/guide/lecons">Leçons rapides</Link> · {l.duree}</div>
      <h1>{l.titre}</h1>
      <div className="progression" aria-label={`Écran ${Math.min(n + 1, l.etapes.length + 1)} sur ${l.etapes.length + 1}`}>
        {[...l.etapes, null].map((_, k) => <span key={k} className={k <= n ? "fait" : ""} />)}
      </div>
      {!quiz ? (
        <div className="carte section lecon">
          <h2>{l.etapes[n].titre}</h2>
          <p>{l.etapes[n].texte}</p>
          <div className="actions">
            {n > 0 && <button onClick={() => setN(n - 1)}>Précédent</button>}
            <button className="principal" onClick={() => setN(n + 1)}>{n === l.etapes.length - 1 ? "La question" : "Suivant"}</button>
          </div>
        </div>
      ) : (
        <div className="carte section lecon">
          <h2>{l.quiz.question}</h2>
          <div className="choix" role="radiogroup" aria-label={l.quiz.question}>
            {l.quiz.choix.map((c, k) => (
              <button key={k} role="radio" aria-checked={choix === k} disabled={choix !== null}
                      className={choix === null ? "" : k === l.quiz.bonne ? "bonne" : k === choix ? "mauvaise" : ""}
                      onClick={() => repondre(k)}>{c}</button>
            ))}
          </div>
          {choix !== null && (
            <div className={`constat ${choix === l.quiz.bonne ? "informe" : "avertit"} section`}>
              <div className="titre">{choix === l.quiz.bonne ? "Exact." : "Pas tout à fait."}</div>
              <p>{l.quiz.pourquoi}</p>
            </div>
          )}
          <div className="actions">
            <button onClick={() => { setN(0); setChoix(null); }}>Recommencer</button>
            {choix !== null && suivante && <Link to={`/guide/lecons/${suivante.id}`}><button className="principal">Leçon suivante</button></Link>}
            {choix !== null && !suivante && <Link to="/guide/lecons"><button className="principal">Toutes les leçons</button></Link>}
          </div>
        </div>
      )}
    </>
  );
}

// --- Glossaire, astuces, recherche ----------------------------------------------------

function Glossaire() {
  const termes = Object.entries(GLOSSAIRE).sort((a, b) => a[1].terme.localeCompare(b[1].terme, "fr"));
  return (
    <>
      <h1>Glossaire</h1>
      <p className="guide-resume">Les mots de l'IFC, en une phrase chacun. Les mêmes définitions apparaissent en infobulle
        (le petit « ? ») partout dans la plateforme.</p>
      <dl className="definitions">
        {termes.map(([cle, d]) => (
          <div key={cle} id={cle}><dt>{d.terme}</dt><dd>{d.definition}
            {"chapitre" in d && d.chapitre && <> <Link to={`/guide/${d.chapitre}`}>Le chapitre</Link></>}</dd></div>
        ))}
      </dl>
    </>
  );
}

function Astuces() {
  return (
    <>
      <h1>Le saviez-vous ?</h1>
      <p className="guide-resume">Une astuce par jour sur votre tableau de bord ; toutes, ici.</p>
      {ASTUCES.map((a, i) => (
        <div key={i} className="carte astuce" style={{ marginBottom: 10 }}>
          <p style={{ margin: 0 }}>💡 {a.texte}</p>
          {a.chapitre && <Link to={`/guide/${a.chapitre}`}>En savoir plus</Link>}
          {a.lecon && <Link to={`/guide/lecons/${a.lecon}`}>La leçon</Link>}
        </div>
      ))}
    </>
  );
}

function Resultats({ q }: { q: string }) {
  const mots = plat(q).split(/\s+/).filter((m) => m.length > 1);
  const trouve = (t: string) => mots.every((m) => plat(t).includes(m));
  const chapitres = CHAPITRES.filter((c) => trouve([c.titre, c.resume, ...c.sections.flatMap((s) => [s.titre, ...s.texte])].join(" ")));
  const termes = Object.entries(GLOSSAIRE).filter(([, d]) => trouve(`${d.terme} ${d.definition}`));
  const lecons = LECONS.filter((l) => trouve([l.titre, ...l.etapes.map((e) => e.titre + " " + e.texte)].join(" ")));
  const rien = !chapitres.length && !termes.length && !lecons.length;
  return (
    <>
      <h1>« {q} »</h1>
      {rien && <p>Rien dans le guide. Essayez un autre mot, ou posez la question à votre conseiller.</p>}
      {termes.length > 0 && <section className="section"><h2>Définitions</h2><dl className="definitions">
        {termes.map(([k, d]) => <div key={k}><dt>{d.terme}</dt><dd>{d.definition}</dd></div>)}</dl></section>}
      {chapitres.length > 0 && <section className="section"><h2>Chapitres</h2>
        {chapitres.map((c) => <p key={c.id}><Link to={`/guide/${c.id}`}>{c.titre}</Link> — {c.resume}</p>)}</section>}
      {lecons.length > 0 && <section className="section"><h2>Leçons</h2>
        {lecons.map((l) => <p key={l.id}><Link to={`/guide/lecons/${l.id}`}>{l.titre}</Link> ({l.duree})</p>)}</section>}
    </>
  );
}

// --- Les conventions préremplies --------------------------------------------------------

interface ConventionPubliee {
  pays: string; pays_libelle: string; code: string; libelle: string; statut: "valide" | "a_valider";
  en_vigueur_du: string; en_vigueur_au: string | null; en_vigueur_aujourd_hui: boolean;
  sources: { titre: string; url: string | null; consulte_le: string | null }[];
  verification: string; notes: string[];
  bareme: { forme: "tranches_cumulatives"; tranches: { jusqu_a: number | null; mois_par_annee: number }[] }
        | { forme: "paliers"; sous_premier_palier_mois_par_annee: number; paliers: { a_partir_de: number; mois: number }[] };
  illustration: { anciennete: number; mois: number }[];
}

const virgule = (x: number) => x.toLocaleString("fr-FR", { maximumFractionDigits: 2 });

function Conventions() {
  const { donnee, erreur } = useCharge(() => api.get<{ version: string; conventions: ConventionPubliee[] }>("/referentiel/conventions"), []);
  const [pays, setPays] = useState("");
  const liste = useMemo(() => (donnee?.conventions ?? []).filter((c) => !pays || c.pays === pays), [donnee, pays]);
  const tousPays = [...new Map((donnee?.conventions ?? []).map((c) => [c.pays, c.pays_libelle])).entries()];
  return (
    <>
      <h1>Les conventions préremplies</h1>
      <p className="guide-resume">Les barèmes d'IFC intégrés à la plateforme, avec leurs dates, leurs sources et ce qui a
        été vérifié. Consultables sans compte.</p>
      <Erreur erreur={erreur} />
      {donnee && (
        <>
          <label style={{ maxWidth: 260 }}>Pays
            <select value={pays} onChange={(e) => setPays(e.target.value)}>
              <option value="">Tous ({donnee.conventions.length} versions)</option>
              {tousPays.map(([code, nom]) => <option key={code} value={code}>{nom}</option>)}
            </select>
          </label>
          <p className="discret">Référentiel du {dateFr(donnee.version)}.</p>
          {liste.map((c) => <CarteConvention key={`${c.code}-${c.en_vigueur_du}`} c={c} />)}
        </>
      )}
    </>
  );
}

function CarteConvention({ c }: { c: ConventionPubliee }) {
  return (
    <details className="carte section convention" data-convention={`${c.code}@${c.en_vigueur_du}`} open={c.en_vigueur_aujourd_hui && c.pays === "CM"}>
      <summary>
        <strong>{c.libelle}</strong>
        <div className="discret">
          {c.pays_libelle} · {c.code} · du {dateFr(c.en_vigueur_du)}{c.en_vigueur_au ? ` au ${dateFr(c.en_vigueur_au)}` : ", en vigueur"}
          {" "}<span className={`etat ${c.statut === "valide" ? "bien" : "attention"}`}>{c.statut === "valide" ? "Valide" : "À valider"}</span>
          {!c.en_vigueur_aujourd_hui && <> <span className="etat neutre">Historique</span></>}
        </div>
      </summary>
      <div className="grille g2 section">
        <div>
          <h3>Barème</h3>
          <table><tbody>
            {c.bareme.forme === "tranches_cumulatives"
              ? c.bareme.tranches.map((t, i, ts) => {
                  const de = i === 0 ? 1 : (ts[i - 1].jusqu_a ?? 0) + 1;
                  return <tr key={i}><td>{t.jusqu_a ? `De ${de} à ${t.jusqu_a} ans` : `Au-delà de ${de - 1} ans`}</td>
                    <td className="n">{virgule(t.mois_par_annee * 100)} % d'un mois par année</td></tr>;
                })
              : [<tr key="s"><td>Sous le premier palier</td><td className="n">{virgule(c.bareme.sous_premier_palier_mois_par_annee)} mois par année</td></tr>,
                 ...c.bareme.paliers.map((p) => <tr key={p.a_partir_de}><td>À partir de {p.a_partir_de} ans</td><td className="n">{virgule(p.mois)} mois</td></tr>)]}
          </tbody></table>
        </div>
        <div>
          <h3>Ce que cela donne</h3>
          <table><thead><tr><th>Ancienneté</th><th className="n">Mois de salaire</th></tr></thead><tbody>
            {c.illustration.map((x) => <tr key={x.anciennete}><td>{x.anciennete} ans</td><td className="n">{virgule(x.mois)}</td></tr>)}
          </tbody></table>
        </div>
      </div>
      {c.notes.length > 0 && <><h3>À savoir</h3><ul>{c.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></>}
      <h3>Vérification</h3>
      <p>{c.verification}</p>
      <h3>Sources</h3>
      <ul>{c.sources.map((s, i) => (
        <li key={i}>{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.titre}</a> : s.titre}
          {s.consulte_le && <span className="discret"> — consultée le {dateFr(s.consulte_le)}</span>}</li>
      ))}</ul>
    </details>
  );
}
