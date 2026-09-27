import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

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
  const id = useId();
  const visibles = actions.filter((a) => !a.cache);
  useEffect(() => {
    if (!ouvert) return;
    const dehors = (e: MouseEvent) => { if (!racine.current?.contains(e.target as Node)) setOuvert(false); };
    document.addEventListener("mousedown", dehors);
    racine.current?.querySelector<HTMLElement>('[role="menuitem"]:not([aria-disabled="true"])')?.focus();
    return () => document.removeEventListener("mousedown", dehors);
  }, [ouvert]);
  if (!visibles.length) return null;

  function clavier(e: KeyboardEvent) {
    if (e.key === "Escape") { setOuvert(false); racine.current?.querySelector<HTMLElement>("button.menu-points")?.focus(); }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const items = [...(racine.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])];
      const i = items.indexOf(document.activeElement as HTMLElement);
      items[(i + (e.key === "ArrowDown" ? 1 : items.length - 1)) % items.length]?.focus();
    }
  }
  return (
    <div className="menu-actions" ref={racine} onKeyDown={clavier}>
      <button type="button" className="menu-points" aria-label={libelle} aria-haspopup="menu" aria-expanded={ouvert}
              aria-controls={id} onClick={() => setOuvert(!ouvert)}>⋮</button>
      {ouvert && (
        <ul id={id} role="menu" aria-label={libelle} className="menu-liste">
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
        </ul>
      )}
    </div>
  );
}
