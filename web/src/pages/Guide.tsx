import { useMemo, useState } from "react";
import { Link, NavLink, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { oublierVisite } from "../composants/Visite";
import { dateFr } from "../format";
import { langue, t } from "../i18n";
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
      <nav className="guide-nav" aria-label={t("Sommaire du guide", "Guide contents")}>
        <input type="search" placeholder={t("Chercher dans le guide…", "Search the guide…")} value={recherche}
               aria-label={t("Chercher dans le guide", "Search the guide")}
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
        <div className="guide-groupe">{t("Apprendre", "Learn")}</div>
        <NavLink to="/guide/lecons" onClick={() => setRecherche("")}>{t("Leçons rapides", "Quick lessons")}</NavLink>
        <NavLink to="/guide/astuces" onClick={() => setRecherche("")}>{t("Le saviez-vous ?", "Did you know?")}</NavLink>
        <NavLink to="/guide/glossaire" onClick={() => setRecherche("")}>{t("Glossaire", "Glossary")}</NavLink>
        <NavLink to="/guide/conventions-preremplies" onClick={() => setRecherche("")}>{t("Consulter les conventions", "Browse the collective agreements")}</NavLink>
      </nav>
      <article className="guide-texte">
        {langue() === "en" && <p className="discret" data-guide-langue>The guide's chapters are in French for now.</p>}
        {recherche.trim() ? <Resultats q={recherche} />
          : section === "lecons" ? (sous ? <UneLecon id={sous} /> : <Lecons />)
          : section === "glossaire" ? <Glossaire />
          : section === "astuces" ? <Astuces />
          : section === "conventions-preremplies" ? <Conventions />
          : chapitre ? <UnChapitre c={chapitre} />
          : <p>{t("Ce chapitre n'existe pas.", "This chapter does not exist.")} <Link to="/guide">{t("Retour au guide", "Back to the guide")}</Link></p>}
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
          {s.texte.map((x, k) => <p key={k}>{x}</p>)}
        </section>
      ))}
      {c.id === "conventions" && <p><Link to="/guide/conventions-preremplies">{t("Consulter les conventions préremplies →", "Browse the pre-filled collective agreements →")}</Link></p>}
      {c.id === "bienvenue" && (
        <div className="carte section">
          <h3>{t("Première visite ?", "First visit?")}</h3>
          <p>{t("Une visite guidée de votre dossier, en six bulles, et cinq leçons de deux minutes.", "A guided tour of your file in six bubbles, and five two-minute lessons.")}</p>
          <div className="actions">
            <button className="principal" onClick={() => { oublierVisite(); naviguer("/"); }}>{t("Revoir la visite guidée", "Replay the guided tour")}</button>
            <Link to="/guide/lecons"><button>{t("Les leçons rapides", "Quick lessons")}</button></Link>
          </div>
        </div>
      )}
      {!!c.termes?.length && (
        <section className="section carte">
          <h3>{t("Les mots de ce chapitre", "Terms in this chapter")}</h3>
          <dl className="definitions">
            {c.termes.map((k) => <div key={k}><dt>{GLOSSAIRE[k].terme}</dt><dd>{GLOSSAIRE[k].definition}</dd></div>)}
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
      <h1>{t("Leçons rapides", "Quick lessons")}</h1>
      <p className="guide-resume">{t("Deux ou trois minutes chacune, et une question pour vérifier.", "Two or three minutes each, and a question to check.")}
        {" "}{t(`${faites.length}/${LECONS.length} faites.`, `${faites.length}/${LECONS.length} done.`)}</p>
      <div className="grille g2">
        {LECONS.map((l) => (
          <Link key={l.id} to={`/guide/lecons/${l.id}`} className="carte lien">
            <div className="discret">{l.duree} · {l.pour}{faites.includes(l.id) && t(" · ✓ faite", " · ✓ done")}</div>
            <h3 style={{ marginTop: 6 }}>{l.titre}</h3>
            <div className="discret">{t(`${l.etapes.length} écrans et une question`, `${l.etapes.length} screens and a question`)}</div>
          </Link>
        ))}
      </div>
    </>
  );
}

function UneLecon({ id }: { id: string }) {
  const l = LECONS.find((x) => x.id === id);
  if (!l) return <p>{t("Leçon introuvable.", "Lesson not found.")} <Link to="/guide/lecons">{t("Toutes les leçons", "All lessons")}</Link></p>;
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
      <div className="discret"><Link to="/guide/lecons">{t("Leçons rapides", "Quick lessons")}</Link> · {l.duree}</div>
      <h1>{l.titre}</h1>
      <div className="progression" aria-label={t(`Écran ${Math.min(n + 1, l.etapes.length + 1)} sur ${l.etapes.length + 1}`, `Screen ${Math.min(n + 1, l.etapes.length + 1)} of ${l.etapes.length + 1}`)}>
        {[...l.etapes, null].map((_, k) => <span key={k} className={k <= n ? "fait" : ""} />)}
      </div>
      {!quiz ? (
        <div className="carte section lecon">
          <h2>{l.etapes[n].titre}</h2>
          <p>{l.etapes[n].texte}</p>
          <div className="actions">
            {n > 0 && <button onClick={() => setN(n - 1)}>{t("Précédent", "Previous")}</button>}
            <button className="principal" onClick={() => setN(n + 1)}>{n === l.etapes.length - 1 ? t("La question", "The question") : t("Suivant", "Next")}</button>
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
              <div className="titre">{choix === l.quiz.bonne ? t("Exact.", "Correct.") : t("Pas tout à fait.", "Not quite.")}</div>
              <p>{l.quiz.pourquoi}</p>
            </div>
          )}
          <div className="actions">
            <button onClick={() => { setN(0); setChoix(null); }}>{t("Recommencer", "Start again")}</button>
            {choix !== null && suivante && <Link to={`/guide/lecons/${suivante.id}`}><button className="principal">{t("Leçon suivante", "Next lesson")}</button></Link>}
            {choix !== null && !suivante && <Link to="/guide/lecons"><button className="principal">{t("Toutes les leçons", "All lessons")}</button></Link>}
          </div>
        </div>
      )}
    </>
  );
}

// --- Glossaire, astuces, recherche ----------------------------------------------------

function Glossaire() {
  const termes = Object.entries(GLOSSAIRE).sort((a, b) => a[1].terme.localeCompare(b[1].terme, langue()));
  return (
    <>
      <h1>{t("Glossaire", "Glossary")}</h1>
      <p className="guide-resume">{t("Les mots de l'IFC, en une phrase chacun. Les mêmes définitions apparaissent en infobulle (le petit « ? ») partout dans la plateforme.",
        "The vocabulary of IFC, one sentence each. The same definitions appear as tooltips (the small “?”) throughout the platform.")}</p>
      <dl className="definitions">
        {termes.map(([cle, d]) => (
          <div key={cle} id={cle}><dt>{d.terme}</dt><dd>{d.definition}
            {"chapitre" in d && d.chapitre && <> <Link to={`/guide/${d.chapitre}`}>{t("Le chapitre", "The chapter")}</Link></>}</dd></div>
        ))}
      </dl>
    </>
  );
}

function Astuces() {
  return (
    <>
      <h1>{t("Le saviez-vous ?", "Did you know?")}</h1>
      <p className="guide-resume">{t("Une astuce par jour sur votre tableau de bord ; toutes, ici.", "One tip a day on your dashboard; all of them, here.")}</p>
      {ASTUCES.map((a, i) => (
        <div key={i} className="carte astuce" style={{ marginBottom: 10 }}>
          <p style={{ margin: 0 }}>💡 {a.texte}</p>
          {a.chapitre && <Link to={`/guide/${a.chapitre}`}>{t("En savoir plus", "Learn more")}</Link>}
          {a.lecon && <Link to={`/guide/lecons/${a.lecon}`}>{t("La leçon", "The lesson")}</Link>}
        </div>
      ))}
    </>
  );
}

function Resultats({ q }: { q: string }) {
  const mots = plat(q).split(/\s+/).filter((m) => m.length > 1);
  const trouve = (x: string) => mots.every((m) => plat(x).includes(m));
  const chapitres = CHAPITRES.filter((c) => trouve([c.titre, c.resume, ...c.sections.flatMap((s) => [s.titre, ...s.texte])].join(" ")));
  const termes = Object.entries(GLOSSAIRE).filter(([, d]) => trouve(`${d.terme} ${d.definition}`));
  const lecons = LECONS.filter((l) => trouve([l.titre, ...l.etapes.map((e) => e.titre + " " + e.texte)].join(" ")));
  const rien = !chapitres.length && !termes.length && !lecons.length;
  return (
    <>
      <h1>{t(`« ${q} »`, `“${q}”`)}</h1>
      {rien && <p>{t("Rien dans le guide. Essayez un autre mot, ou posez la question à votre conseiller.", "Nothing in the guide. Try another word, or ask your adviser.")}</p>}
      {termes.length > 0 && <section className="section"><h2>{t("Définitions", "Definitions")}</h2><dl className="definitions">
        {termes.map(([k, d]) => <div key={k}><dt>{d.terme}</dt><dd>{d.definition}</dd></div>)}</dl></section>}
      {chapitres.length > 0 && <section className="section"><h2>{t("Chapitres", "Chapters")}</h2>
        {chapitres.map((c) => <p key={c.id}><Link to={`/guide/${c.id}`}>{c.titre}</Link> — {c.resume}</p>)}</section>}
      {lecons.length > 0 && <section className="section"><h2>{t("Leçons", "Lessons")}</h2>
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

const virgule = (x: number) => x.toLocaleString(langue() === "en" ? "en-GB" : "fr-FR", { maximumFractionDigits: 2 });

function Conventions() {
  const { donnee, erreur } = useCharge(() => api.get<{ version: string; pays_couverts?: Record<string, string>;
    conventions: ConventionPubliee[] }>("/referentiel/conventions"), []);
  const [pays, setPays] = useState("");
  const liste = useMemo(() => (donnee?.conventions ?? []).filter((c) => !pays || c.pays === pays), [donnee, pays]);
  const tousPays = [...new Map((donnee?.conventions ?? []).map((c) => [c.pays, c.pays_libelle])).entries()];
  // Les pays de la CEMAC sans convention préremplie : dits, pas tus.
  const aVenir = Object.entries(donnee?.pays_couverts ?? {}).filter(([code]) => !tousPays.some(([p]) => p === code))
    .map(([, nom]) => nom);
  return (
    <>
      <h1>{t("Les conventions préremplies", "Pre-filled collective agreements")}</h1>
      <p className="guide-resume">{t("Les barèmes d'IFC intégrés à la plateforme pour les pays de la CEMAC, avec leurs dates, leurs sources et ce qui a été vérifié. Consultables sans compte.",
        "The IFC scales built into the platform for the CEMAC countries, with their dates, their sources and what has been checked. Open to all, no account needed.")}</p>
      <Erreur erreur={erreur} />
      {donnee && (
        <>
          <label style={{ maxWidth: 260 }}>{t("Pays", "Country")}
            <select value={pays} onChange={(e) => setPays(e.target.value)}>
              <option value="">{t(`Tous (${donnee.conventions.length} versions)`, `All (${donnee.conventions.length} versions)`)}</option>
              {tousPays.map(([code, nom]) => <option key={code} value={code}>{nom}</option>)}
            </select>
          </label>
          <p className="discret">{t(`Référentiel du ${dateFr(donnee.version)}.`, `Reference data of ${dateFr(donnee.version)}.`)}</p>
          {aVenir.length > 0 && (
            <p className="discret" data-a-venir>{t(`Pas encore de convention préremplie pour : ${aVenir.join(", ")}. Une entreprise de ces pays peut décrire son régime à partir de son propre texte.`,
              `No pre-filled collective agreement yet for: ${aVenir.join(", ")}. A company in these countries can describe its scheme from its own text.`)}</p>
          )}
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
          {c.pays_libelle} · {c.code} · {t("du", "from")} {dateFr(c.en_vigueur_du)}{c.en_vigueur_au ? t(` au ${dateFr(c.en_vigueur_au)}`, ` to ${dateFr(c.en_vigueur_au)}`) : t(", en vigueur", ", in force")}
          {" "}<span className={`etat ${c.statut === "valide" ? "bien" : "attention"}`}>{c.statut === "valide" ? t("Valide", "Validated") : t("À valider", "To be validated")}</span>
          {!c.en_vigueur_aujourd_hui && <> <span className="etat neutre">{t("Historique", "Historical")}</span></>}
        </div>
      </summary>
      <div className="grille g2 section">
        <div>
          <h3>{t("Barème", "Scale")}</h3>
          <table><tbody>
            {c.bareme.forme === "tranches_cumulatives"
              ? c.bareme.tranches.map((tr, i, ts) => {
                  const de = i === 0 ? 1 : (ts[i - 1].jusqu_a ?? 0) + 1;
                  return <tr key={i}><td>{tr.jusqu_a ? t(`De ${de} à ${tr.jusqu_a} ans`, `${de} to ${tr.jusqu_a} years`) : t(`Au-delà de ${de - 1} ans`, `Over ${de - 1} years`)}</td>
                    <td className="n">{t(`${virgule(tr.mois_par_annee * 100)} % d'un mois par année`, `${virgule(tr.mois_par_annee * 100)}% of a month per year`)}</td></tr>;
                })
              : [<tr key="s"><td>{t("Sous le premier palier", "Below the first step")}</td><td className="n">{t(`${virgule(c.bareme.sous_premier_palier_mois_par_annee)} mois par année`, `${virgule(c.bareme.sous_premier_palier_mois_par_annee)} months per year`)}</td></tr>,
                 ...c.bareme.paliers.map((p) => <tr key={p.a_partir_de}><td>{t(`À partir de ${p.a_partir_de} ans`, `From ${p.a_partir_de} years`)}</td><td className="n">{t(`${virgule(p.mois)} mois`, `${virgule(p.mois)} months`)}</td></tr>)]}
          </tbody></table>
        </div>
        <div>
          <h3>{t("Ce que cela donne", "What it comes to")}</h3>
          <table><thead><tr><th>{t("Ancienneté", "Length of service")}</th><th className="n">{t("Mois de salaire", "Months of salary")}</th></tr></thead><tbody>
            {c.illustration.map((x) => <tr key={x.anciennete}><td>{t(`${x.anciennete} ans`, `${x.anciennete} years`)}</td><td className="n">{virgule(x.mois)}</td></tr>)}
          </tbody></table>
        </div>
      </div>
      {c.notes.length > 0 && <><h3>{t("À savoir", "Good to know")}</h3><ul>{c.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></>}
      <h3>{t("Vérification", "Verification")}</h3>
      <p>{c.verification}</p>
      <h3>{t("Sources", "Sources")}</h3>
      <ul>{c.sources.map((s, i) => (
        <li key={i}>{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.titre}</a> : s.titre}
          {s.consulte_le && <span className="discret">{t(` — consultée le ${dateFr(s.consulte_le)}`, ` — accessed on ${dateFr(s.consulte_le)}`)}</span>}</li>
      ))}</ul>
    </details>
  );
}
