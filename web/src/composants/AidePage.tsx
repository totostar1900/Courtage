import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { CHAPITRES, type Chapitre } from "../guide/chapitres";
import { GLOSSAIRE, type CleTerme } from "../guide/glossaire";
import { lancerVisite } from "./Visite";

// Les chapitres d'une page : ceux qui déclarent son écran, et quelques renvois utiles au-delà.
const EN_PLUS: Record<string, string[]> = {
  "": ["bienvenue"],
  etudes: ["comprendre", "methode"],
  financement: ["methode"],
  dossiers: ["departs"],
};

export function chapitresDe(page: string): Chapitre[] {
  const ids = [...CHAPITRES.filter((c) => c.ecran === page).map((c) => c.id), ...(EN_PLUS[page] ?? [])];
  return [...new Set(ids)].map((id) => CHAPITRES.find((c) => c.id === id)).filter((c): c is Chapitre => Boolean(c));
}

const saisie = (cible: EventTarget | null) =>
  cible instanceof HTMLElement && (["INPUT", "TEXTAREA", "SELECT"].includes(cible.tagName) || cible.isContentEditable);

/** « Aide sur cette page » : le bouton, la touche « ? », et le panneau qui lit le guide pour la page ouverte. */
export function AidePage({ base }: { base: string }) {
  const { pathname } = useLocation();
  const page = pathname.slice(base.length).split("/").filter(Boolean)[0] ?? "";
  const [ouverte, setOuverte] = useState(false);
  const bouton = useRef<HTMLButtonElement>(null);
  const panneau = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const touche = (e: KeyboardEvent) => {
      if (e.key === "?" && !e.ctrlKey && !e.metaKey && !e.altKey && !saisie(e.target)) { e.preventDefault(); setOuverte(true); }
      else if (e.key === "Escape") setOuverte(false);
    };
    window.addEventListener("keydown", touche);
    return () => window.removeEventListener("keydown", touche);
  }, []);
  useEffect(() => { if (ouverte) panneau.current?.focus(); }, [ouverte]);
  useEffect(() => { setOuverte(false); }, [page]);      // une autre page, une autre aide

  const chapitres = chapitresDe(page);
  const termes = [...new Set(chapitres.flatMap((c) => c.termes ?? []))] as CleTerme[];
  const fermer = () => { setOuverte(false); bouton.current?.focus(); };

  return (
    <>
      <button ref={bouton} type="button" className="bouton-aide" aria-expanded={ouverte} aria-controls="aide-page"
              onClick={() => setOuverte(!ouverte)}>
        <span aria-hidden="true" className="rond">?</span> Aide sur cette page
      </button>
      {ouverte && (
        <div className="aide-fond" onMouseDown={(e) => e.target === e.currentTarget && fermer()}>
          <aside id="aide-page" ref={panneau} tabIndex={-1} className="aide-panneau" role="dialog" aria-modal="true"
                 aria-label="Aide sur cette page">
            <div className="aide-tete">
              <span className="discret">Aide sur cette page</span>
              <button type="button" className="fermer-volet" onClick={fermer} aria-label="Fermer l'aide" title="Fermer">×</button>
            </div>
            {chapitres.length === 0 && <p>Pas d'aide propre à cette page : le guide complet répond au reste.</p>}
            {chapitres.map((c, i) => (
              <section key={c.id} className="aide-chapitre">
                <h2>{c.titre}</h2>
                <p className="aide-resume">{c.resume}</p>
                {c.sections.map((s, j) => (
                  <details key={s.titre} open={i === 0 && j === 0}>
                    <summary>{s.titre}</summary>
                    {s.texte.map((t) => <p key={t}>{t}</p>)}
                  </details>
                ))}
                <Link to={`/guide/${c.id}`} className="aide-lien">Lire le chapitre dans le guide →</Link>
              </section>
            ))}
            {termes.length > 0 && (
              <section className="aide-chapitre">
                <h2>Les mots de cette page</h2>
                <dl className="aide-mots">
                  {termes.map((t) => <div key={t}><dt>{GLOSSAIRE[t].terme}</dt><dd>{GLOSSAIRE[t].definition}</dd></div>)}
                </dl>
              </section>
            )}
            <div className="aide-pied">
              <button type="button" className="lien" onClick={() => { fermer(); lancerVisite(); }}>Visite guidée</button>
              <Link to="/guide">Tout le guide</Link>
              <span className="discret"><kbd>?</kbd> ouvre cette aide · <kbd>Échap</kbd> la ferme</span>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
