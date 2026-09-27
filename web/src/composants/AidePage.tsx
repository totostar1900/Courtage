import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { CHAPITRES, type Chapitre } from "../guide/chapitres";
import { GLOSSAIRE, type CleTerme } from "../guide/glossaire";
import { lancerVisite } from "./Visite";
import { t } from "../i18n";

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
        <span aria-hidden="true" className="rond">?</span> {t("Aide sur cette page", "Help on this page")}
      </button>
      {ouverte && (
        <div className="aide-fond" onMouseDown={(e) => e.target === e.currentTarget && fermer()}>
          <aside id="aide-page" ref={panneau} tabIndex={-1} className="aide-panneau" role="dialog" aria-modal="true"
                 aria-label={t("Aide sur cette page", "Help on this page")}>
            <div className="aide-tete">
              <span className="discret">{t("Aide sur cette page", "Help on this page")}</span>
              <button type="button" className="fermer-volet" onClick={fermer} aria-label={t("Fermer l'aide", "Close help")} title={t("Fermer", "Close")}>×</button>
            </div>
            {chapitres.length === 0 && <p>{t("Pas d'aide propre à cette page : le guide complet répond au reste.", "No help specific to this page: the full guide covers the rest.")}</p>}
            {chapitres.map((c, i) => (
              <section key={c.id} className="aide-chapitre">
                <h2>{c.titre}</h2>
                <p className="aide-resume">{c.resume}</p>
                {c.sections.map((s, j) => (
                  <details key={s.titre} open={i === 0 && j === 0}>
                    <summary>{s.titre}</summary>
                    {s.texte.map((x) => <p key={x}>{x}</p>)}
                  </details>
                ))}
                <Link to={`/guide/${c.id}`} className="aide-lien">{t("Lire le chapitre dans le guide →", "Read the chapter in the guide →")}</Link>
              </section>
            ))}
            {termes.length > 0 && (
              <section className="aide-chapitre">
                <h2>{t("Les mots de cette page", "Terms on this page")}</h2>
                <dl className="aide-mots">
                  {termes.map((k) => <div key={k}><dt>{GLOSSAIRE[k].terme}</dt><dd>{GLOSSAIRE[k].definition}</dd></div>)}
                </dl>
              </section>
            )}
            <div className="aide-pied">
              <button type="button" className="lien" onClick={() => { fermer(); lancerVisite(); }}>{t("Visite guidée", "Guided tour")}</button>
              <Link to="/guide">{t("Tout le guide", "The full guide")}</Link>
              <span className="discret"><kbd>?</kbd> {t("ouvre cette aide", "opens this help")} · <kbd>{t("Échap", "Esc")}</kbd> {t("la ferme", "closes it")}</span>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
