import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { api } from "../api";
import { dateFr } from "../format";
import { CHAPITRES } from "../guide/chapitres";
import type { ContexteDossier } from "../pages/Dossier";
import { lancerVisite } from "./Visite";

const PAGES: Record<string, string> = {
  "": "Tableau de bord", personnel: "Personnel", regime: "Régime", simulation: "Simuler", etudes: "Études",
  financement: "Financement", cahier: "Cahier des charges", remuneration: "Rémunération", contrat: "Contrat",
  departs: "Départs", equipe: "Équipe", dossiers: "Départs",
};

/** Où l'on est dans le dossier : Vos dossiers › l'entreprise › la page › le détail. Chaque niveau ramène. */
export function FilAriane({ d }: { d: Pick<ContexteDossier, "org" | "etudes" | "fiches"> }) {
  const { pathname } = useLocation();
  const base = `/dossier/${d.org.id}`;
  const [page, detail, suite] = pathname.slice(base.length).split("/").filter(Boolean);
  const niveaux: { libelle: string; vers?: string }[] = [{ libelle: "Vos dossiers", vers: "/" },
    { libelle: d.org.nom, vers: page ? base : undefined }];
  if (page) {
    const vers = page === "dossiers" ? `${base}/departs` : `${base}/${page}`;
    niveaux.push({ libelle: PAGES[page] ?? page, vers: detail ? vers : undefined });
  }
  if (detail) {
    const etude = page === "etudes" ? d.etudes.find((e) => e.id === detail) : undefined;
    const libelle = etude ? `Étude au ${dateFr(etude.date_evaluation)}`
      : page === "cahier" ? "Réponses des assureurs" : page === "dossiers" ? "Dossier de prise en charge" : "Détail";
    niveaux.push({ libelle, vers: suite ? `${base}/${page}/${detail}` : undefined });
    if (suite) niveaux.push({ libelle: PAGES[suite] ?? suite });
  }
  return (
    <nav className="fil-ariane" aria-label="Fil d'Ariane">
      <ol>
        {niveaux.map((n, i) => (
          <li key={i}>{n.vers ? <Link to={n.vers}>{n.libelle}</Link> : <span aria-current="page">{n.libelle}</span>}</li>
        ))}
      </ol>
    </nav>
  );
}

interface Commande { id: string; groupe: string; libelle: string; indice?: string; agir: () => void }

const normaliser = (t: string) => t.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

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
      ...Object.entries(PAGES).filter(([k]) => k !== "dossiers").map(([k, l]) => ({
        id: `page-${k}`, groupe: "Pages du dossier", libelle: l, agir: fermer(() => aller(k ? `${base}/${k}` : base)) })),
      ...d.etudes.map((e) => ({
        id: `etude-${e.id}`, groupe: "Études", libelle: `Étude au ${dateFr(e.date_evaluation)}`,
        indice: e.statut === "emise" ? "émise" : "brouillon", agir: fermer(() => aller(`${base}/etudes/${e.id}`)) })),
      { id: "canevas", groupe: "Actions", libelle: "Télécharger le canevas du personnel",
        agir: fermer(() => { api.telecharger("/referentiel/canevas-personnel", "canevas-personnel.xlsx").catch(() => undefined); }) },
      { id: "visite", groupe: "Actions", libelle: "Lancer la visite guidée", agir: fermer(lancerVisite) },
      ...CHAPITRES.map((c) => ({ id: `guide-${c.id}`, groupe: "Guide", libelle: c.titre, indice: c.groupe,
                                 agir: fermer(() => aller(`/guide/${c.id}`)) })),
    ];
  }, [d.etudes, base, aller]);

  const mots = normaliser(texte).split(/\s+/).filter(Boolean);
  const trouvees = commandes.filter((c) => mots.every((m) => normaliser(`${c.libelle} ${c.groupe} ${c.indice ?? ""}`).includes(m)));
  const actif = Math.min(choix, Math.max(trouvees.length - 1, 0));

  if (!ouverte) return null;
  return (
    <div className="palette-fond" onMouseDown={(e) => e.target === e.currentTarget && setOuverte(false)}>
      <div className="palette" role="dialog" aria-modal="true" aria-label="Aller à">
        <input ref={champ} value={texte} placeholder="Aller à… une page, une étude, un chapitre du guide"
               aria-label="Rechercher" aria-controls="palette-liste" aria-activedescendant={trouvees[actif]?.id}
               onChange={(e) => { setTexte(e.target.value); setChoix(0); }}
               onKeyDown={(e) => {
                 if (e.key === "Escape") setOuverte(false);
                 else if (e.key === "ArrowDown") { e.preventDefault(); setChoix(Math.min(actif + 1, trouvees.length - 1)); }
                 else if (e.key === "ArrowUp") { e.preventDefault(); setChoix(Math.max(actif - 1, 0)); }
                 else if (e.key === "Enter" && trouvees[actif]) trouvees[actif].agir();
               }} />
        <ul id="palette-liste" role="listbox" aria-label="Résultats">
          {trouvees.length === 0 && <li className="vide">Rien ne correspond.</li>}
          {trouvees.map((c, i) => (
            <li key={c.id} id={c.id} role="option" aria-selected={i === actif} className={i === actif ? "actif" : ""}
                onMouseEnter={() => setChoix(i)} onMouseDown={(e) => { e.preventDefault(); c.agir(); }}>
              <span>{c.libelle}</span><small>{c.indice ?? c.groupe}</small>
            </li>
          ))}
        </ul>
        <div className="palette-pied"><kbd>↑</kbd><kbd>↓</kbd> choisir · <kbd>Entrée</kbd> ouvrir · <kbd>Échap</kbd> fermer</div>
      </div>
    </div>
  );
}

/** Le bouton qui ouvre la palette, pour qui ne connaît pas le raccourci. */
export function BoutonAller() {
  const mac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
  return (
    <button type="button" className="bouton-aller" onClick={() => window.dispatchEvent(new Event("courtage:aller"))}>
      <span>Aller à…</span><kbd>{mac ? "⌘" : "Ctrl"} K</kbd>
    </button>
  );
}
