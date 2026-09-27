import { useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";

import { GLOSSAIRE, type CleTerme } from "../guide/glossaire";
import { t } from "../i18n";

/** Un mot du métier et sa définition en infobulle : au survol, au clavier (focus) ou d'un toucher. */
export function Terme({ cle, children }: { cle: CleTerme; children?: ReactNode }) {
  const d = GLOSSAIRE[cle];
  const [ouvert, setOuvert] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);
  const [aDroite, setADroite] = useState(false);
  // Près du bord droit, la bulle s'aligne à droite du mot au lieu de sortir de l'écran.
  useLayoutEffect(() => {
    if (ouvert && ref.current) setADroite(ref.current.getBoundingClientRect().left + 312 > window.innerWidth);
  }, [ouvert]);
  return (
    <span ref={ref} className="terme" onMouseEnter={() => setOuvert(true)} onMouseLeave={() => setOuvert(false)}>
      {children ?? d.terme}
      <button type="button" className="aide" aria-label={t(`Définition : ${d.terme}`, `Definition: ${d.terme}`)} aria-expanded={ouvert}
              aria-describedby={ouvert ? id : undefined}
              onClick={() => setOuvert(true)} onFocus={() => setOuvert(true)} onBlur={() => setOuvert(false)}
              onKeyDown={(e) => e.key === "Escape" && setOuvert(false)}>?</button>
      {ouvert && <span role="tooltip" id={id} className={`bulle${aDroite ? " a-droite" : ""}`}>{d.definition}</span>}
    </span>
  );
}
