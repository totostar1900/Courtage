import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";

/** Une entrée du menu ⋮. `raison` : l'action existe mais n'est pas possible ici — elle reste visible, grisée, avec
 *  pourquoi, plutôt que de disparaître sans explication. */
export interface Action {
  libelle: string;
  agir?: () => void;
  raison?: string | null;
  danger?: boolean;
  cache?: boolean;
}

/** Le menu ⋮ commun : toujours le même ordre — ouvrir ou télécharger, modifier, dupliquer, l'acte propre à l'objet,
 *  supprimer (en dernier, en rouge). Clavier : Entrée ou Espace ouvre, Échap ferme, flèches pour se déplacer. */
export function MenuActions({ actions, libelle = "Actions" }: { actions: Action[]; libelle?: string }) {
  const [ouvert, setOuvert] = useState(false);
  const racine = useRef<HTMLDivElement>(null);
  const liste = useRef<HTMLUListElement>(null);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const id = useId();
  const visibles = actions.filter((a) => !a.cache);
  // Le menu se pose au-dessus de la page (portail, position fixe) : aucune boîte qui défile ne le coupe. Il s'aligne
  // sur le bouton, et s'ouvre vers le haut quand la place manque en bas.
  useLayoutEffect(() => {
    if (!ouvert) return;
    const placer = () => {
      const b = racine.current?.getBoundingClientRect();
      const m = liste.current?.getBoundingClientRect();
      if (!b) return;
      const largeur = m?.width ?? 260, hauteur = m?.height ?? 200;
      const left = Math.max(8, Math.min(b.right - largeur, window.innerWidth - largeur - 8));
      const top = b.bottom + 4 + hauteur > window.innerHeight - 8 ? Math.max(8, b.top - 4 - hauteur) : b.bottom + 4;
      setPosition({ top, left });
    };
    placer();
    window.addEventListener("resize", placer);
    window.addEventListener("scroll", placer, true);
    return () => { window.removeEventListener("resize", placer); window.removeEventListener("scroll", placer, true); };
  }, [ouvert]);
  useEffect(() => {
    if (!ouvert) return;
    const dehors = (e: MouseEvent) => {
      const cible = e.target as Node;
      if (!racine.current?.contains(cible) && !liste.current?.contains(cible)) setOuvert(false);
    };
    document.addEventListener("mousedown", dehors);
    liste.current?.querySelector<HTMLElement>('[role="menuitem"]:not([aria-disabled="true"])')?.focus();
    return () => document.removeEventListener("mousedown", dehors);
  }, [ouvert, position === null]);
  if (!visibles.length) return null;

  function clavier(e: KeyboardEvent) {
    if (e.key === "Escape") { setOuvert(false); racine.current?.querySelector<HTMLElement>("button.menu-points")?.focus(); }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const items = [...(liste.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])];
      const i = items.indexOf(document.activeElement as HTMLElement);
      items[(i + (e.key === "ArrowDown" ? 1 : items.length - 1)) % items.length]?.focus();
    }
  }
  return (
    <div className="menu-actions" ref={racine} onKeyDown={clavier}>
      <button type="button" className="menu-points" aria-label={libelle} aria-haspopup="menu" aria-expanded={ouvert}
              aria-controls={id} onClick={() => { setPosition(null); setOuvert(!ouvert); }}>⋮</button>
      {ouvert && createPortal(
        <ul id={id} ref={liste} role="menu" aria-label={libelle} className="menu-liste" onKeyDown={clavier}
            style={{ position: "fixed", top: position?.top ?? -9999, left: position?.left ?? -9999 }}>
          {visibles.map((a) => (
            <li key={a.libelle} role="none">
              <button type="button" role="menuitem" className={a.danger ? "danger" : ""} aria-disabled={Boolean(a.raison)}
                      title={a.raison ?? undefined}
                      onClick={() => { if (a.raison) return; setOuvert(false); a.agir?.(); }}>
                <span>{a.libelle}</span>
                {a.raison && <small>{a.raison}</small>}
              </button>
            </li>
          ))}
        </ul>, document.body)}
    </div>
  );
}
