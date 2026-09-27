import { useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";

import { api } from "../api";
import { dateFr } from "../format";
import { CHAPITRES } from "../guide/chapitres";
import type { ContexteDossier } from "../pages/Dossier";
import { lancerVisite } from "./Visite";
import { t } from "../i18n";

/** Les pages du dossier, par segment d'adresse. Une fonction : la langue se lit au rendu. */
const pages = (): Record<string, string> => ({
  "": t("Tableau de bord", "Dashboard"), personnel: t("Personnel", "Workforce"), regime: t("Régime", "Plan"),
  simulation: t("Simuler", "Simulate"), etudes: t("Études", "Studies"), financement: t("Financement", "Funding"),
  cahier: t("Cahier des charges", "Specifications"), contrat: t("Contrat", "Contract"),
  accompagnement: t("Accompagnement", "Support"), departs: t("Départs", "Departures"), equipe: t("Équipe", "Team"),
  dossiers: t("Départs", "Departures"),
});

export interface Niveau { libelle: string; vers?: string }

/** Les niveaux du fil d'Ariane pour un chemin du dossier : Vos dossiers › l'entreprise › la page › le détail. */
export function niveauxDe(pathname: string, d: Pick<ContexteDossier, "org" | "etudes">): Niveau[] {
  const base = `/dossier/${d.org.id}`;
  const [page, detail, suite] = pathname.slice(base.length).split("/").filter(Boolean);
  const PAGES = pages();
  const niveaux: Niveau[] = [{ libelle: t("Vos dossiers", "Your files"), vers: "/" }, { libelle: d.org.nom, vers: page ? base : undefined }];
  if (page) {
    const vers = page === "dossiers" ? `${base}/departs` : `${base}/${page}`;
    niveaux.push({ libelle: PAGES[page] ?? page, vers: detail ? vers : undefined });
  }
  if (detail) {
    const etude = page === "etudes" ? d.etudes.find((e) => e.id === detail) : undefined;
    const libelle = etude ? t(`Étude au ${dateFr(etude.date_evaluation)}`, `Study as at ${dateFr(etude.date_evaluation)}`)
      : page === "cahier" ? t("Réponses des assureurs", "Insurers' responses")
      : page === "dossiers" ? t("Dossier de prise en charge", "Claim file") : t("Détail", "Detail");
    niveaux.push({ libelle, vers: suite ? `${base}/${page}/${detail}` : undefined });
    if (suite) niveaux.push({ libelle: PAGES[suite] ?? suite });
  }
  return niveaux;
}

/** Où l'on est dans le dossier. Chaque niveau ramène. */
export function FilAriane({ d }: { d: Pick<ContexteDossier, "org" | "etudes"> }) {
  const { pathname } = useLocation();
  const niveaux = niveauxDe(pathname, d);
  return (
    <nav className="fil-ariane" aria-label={t("Fil d'Ariane", "Breadcrumb")}>
      <ol>
        {niveaux.map((n, i) => (
          <li key={i}>{n.vers ? <Link to={n.vers}>{n.libelle}</Link> : <span aria-current="page">{n.libelle}</span>}</li>
        ))}
      </ol>
    </nav>
  );
}

interface Commande { id: string; groupe: string; libelle: string; indice?: string; agir: () => void }

const normaliser = (x: string) => x.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** « Aller à… » : Ctrl+K (⌘K) ouvre une recherche sur tout ce qu'on peut atteindre depuis le dossier. */
export function PaletteAller({ d }: { d: Pick<ContexteDossier, "org" | "etudes"> }) {
  const [ouverte, setOuverte] = useState(false);
  const [texte, setTexte] = useState("");
  const [choix, setChoix] = useState(0);
  const aller = useNavigate();
  const champ = useRef<HTMLInputElement>(null);
  const base = `/dossier/${d.org.id}`;

  useEffect(() => {
    const touche = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOuverte((o) => !o); }
    };
    const demande = () => setOuverte(true);
    window.addEventListener("keydown", touche);
    window.addEventListener("courtage:aller", demande);
    return () => { window.removeEventListener("keydown", touche); window.removeEventListener("courtage:aller", demande); };
  }, []);
  useEffect(() => { if (ouverte) { setTexte(""); setChoix(0); champ.current?.focus(); } }, [ouverte]);

  const commandes: Commande[] = useMemo(() => {
    const fermer = (f: () => void) => () => { setOuverte(false); f(); };
    return [
      ...Object.entries(pages()).filter(([k]) => k !== "dossiers").map(([k, l]) => ({
        id: `page-${k}`, groupe: t("Pages du dossier", "File pages"), libelle: l, agir: fermer(() => aller(k ? `${base}/${k}` : base)) })),
      ...d.etudes.map((e) => ({
        id: `etude-${e.id}`, groupe: t("Études", "Studies"),
        libelle: t(`Étude au ${dateFr(e.date_evaluation)}`, `Study as at ${dateFr(e.date_evaluation)}`),
        indice: e.statut === "emise" ? t("émise", "issued") : t("brouillon", "draft"), agir: fermer(() => aller(`${base}/etudes/${e.id}`)) })),
      { id: "canevas", groupe: t("Actions", "Actions"),
        libelle: t("Télécharger le canevas du personnel", "Download the workforce template"),
        agir: fermer(() => { api.telecharger("/referentiel/canevas-personnel", "canevas-personnel.xlsx").catch(() => undefined); }) },
      { id: "visite", groupe: t("Actions", "Actions"), libelle: t("Lancer la visite guidée", "Start the guided tour"), agir: fermer(lancerVisite) },
      ...CHAPITRES.map((c) => ({ id: `guide-${c.id}`, groupe: t("Guide", "Guide"), libelle: c.titre, indice: c.groupe,
                                 agir: fermer(() => aller(`/guide/${c.id}`)) })),
    ];
  }, [d.etudes, base, aller]);

  const mots = normaliser(texte).split(/\s+/).filter(Boolean);
  const trouvees = commandes.filter((c) => mots.every((m) => normaliser(`${c.libelle} ${c.groupe} ${c.indice ?? ""}`).includes(m)));
  const actif = Math.min(choix, Math.max(trouvees.length - 1, 0));

  if (!ouverte) return null;
  return (
    <div className="palette-fond" onMouseDown={(e) => e.target === e.currentTarget && setOuverte(false)}>
      <div className="palette" role="dialog" aria-modal="true" aria-label={t("Aller à", "Go to")}>
        <input ref={champ} value={texte} placeholder={t("Aller à… une page, une étude, un chapitre du guide", "Go to… a page, a study, a guide chapter")}
               aria-label={t("Rechercher", "Search")} aria-controls="palette-liste" aria-activedescendant={trouvees[actif]?.id}
               onChange={(e) => { setTexte(e.target.value); setChoix(0); }}
               onKeyDown={(e) => {
                 if (e.key === "Escape") setOuverte(false);
                 else if (e.key === "ArrowDown") { e.preventDefault(); setChoix(Math.min(actif + 1, trouvees.length - 1)); }
                 else if (e.key === "ArrowUp") { e.preventDefault(); setChoix(Math.max(actif - 1, 0)); }
                 else if (e.key === "Enter" && trouvees[actif]) trouvees[actif].agir();
               }} />
        <ul id="palette-liste" role="listbox" aria-label={t("Résultats", "Results")}>
          {trouvees.length === 0 && <li className="vide">{t("Rien ne correspond.", "No match.")}</li>}
          {trouvees.map((c, i) => (
            <li key={c.id} id={c.id} role="option" aria-selected={i === actif} className={i === actif ? "actif" : ""}
                onMouseEnter={() => setChoix(i)} onMouseDown={(e) => { e.preventDefault(); c.agir(); }}>
              <span>{c.libelle}</span><small>{c.indice ?? c.groupe}</small>
            </li>
          ))}
        </ul>
        <div className="palette-pied"><kbd>↑</kbd><kbd>↓</kbd> {t("choisir", "select")} · <kbd>{t("Entrée", "Enter")}</kbd> {t("ouvrir", "open")} · <kbd>{t("Échap", "Esc")}</kbd> {t("fermer", "close")}</div>
      </div>
    </div>
  );
}

/** Le bouton qui ouvre la palette, pour qui ne connaît pas le raccourci. */
export function BoutonAller() {
  const mac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
  return (
    <button type="button" className="bouton-aller" onClick={() => window.dispatchEvent(new Event("courtage:aller"))}>
      <span>{t("Aller à…", "Go to…")}</span><kbd>{mac ? "⌘" : "Ctrl"} K</kbd>
    </button>
  );
}

/** Sur téléphone : les quatre accès du pouce, en bas de l'écran. Masquée sur ordinateur (le menu est à gauche). */
export function BarreMobile({ d }: { d: Pick<ContexteDossier, "org" | "etudes"> }) {
  const base = `/dossier/${d.org.id}`;
  const etude = d.etudes.find((e) => e.statut === "emise") ?? d.etudes[0];
  const actif = ({ isActive }: { isActive: boolean }) => (isActive ? "actif" : "");
  return (
    <nav className="barre-mobile" aria-label={t("Accès rapides", "Quick access")}>
      <NavLink to={base} end className={actif}><span aria-hidden="true">◧</span>{t("Tableau", "Dashboard")}</NavLink>
      <NavLink to={etude ? `${base}/etudes/${etude.id}` : `${base}/etudes`} className={actif}>
        <span aria-hidden="true">∑</span>{t("Étude", "Study")}</NavLink>
      <NavLink to={`${base}/personnel`} className={actif}><span aria-hidden="true">☰</span>{t("Personnel", "Workforce")}</NavLink>
      <button type="button" onClick={() => window.dispatchEvent(new Event("courtage:aller"))}>
        <span aria-hidden="true">⌕</span>{t("Aller à…", "Go to…")}</button>
    </nav>
  );
}
