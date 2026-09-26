import { useCallback, useEffect, useLayoutEffect, useState } from "react";

import { CLE_VISITE_FAITE, type EtapeVisite } from "../guide/visite";

const lire = (cle: string) => { try { return localStorage.getItem(cle); } catch { return null; } };
const ecrire = (cle: string, v: string) => { try { localStorage.setItem(cle, v); } catch { /* navigation privée */ } };

export function lancerVisite() { window.dispatchEvent(new Event("courtage:visite")); }
export function oublierVisite() { try { localStorage.removeItem(CLE_VISITE_FAITE); } catch { /* rien */ } }

/** La visite guidée : une bulle par étape, posée sur l'élément `[data-visite=…]` de l'écran.
 *  Se lance seule la première fois (`auto`), puis sur demande (`lancerVisite`). */
export default function Visite({ etapes, auto = false }: { etapes: EtapeVisite[]; auto?: boolean }) {
  const [presentes, setPresentes] = useState<EtapeVisite[]>([]);
  const [i, setI] = useState<number | null>(null);
  const [cadre, setCadre] = useState<DOMRect | null>(null);

  const demarrer = useCallback(() => {
    const la = etapes.filter((e) => document.querySelector(`[data-visite="${e.cible}"]`));
    if (la.length) { setPresentes(la); setI(0); }
  }, [etapes]);
  const finir = useCallback(() => { setI(null); ecrire(CLE_VISITE_FAITE, "1"); }, []);

  useEffect(() => {
    window.addEventListener("courtage:visite", demarrer);
    if (auto && !lire(CLE_VISITE_FAITE)) { const t = setTimeout(demarrer, 400); return () => { clearTimeout(t); window.removeEventListener("courtage:visite", demarrer); }; }
    return () => window.removeEventListener("courtage:visite", demarrer);
  }, [auto, demarrer]);

  const etape = i === null ? null : presentes[i];
  useLayoutEffect(() => {
    if (!etape) return;
    const el = document.querySelector(`[data-visite="${etape.cible}"]`) as HTMLElement | null;
    el?.scrollIntoView?.({ block: "center", behavior: "smooth" });
    const mesurer = () => setCadre(el ? el.getBoundingClientRect() : null);
    mesurer();
    const t = setTimeout(mesurer, 350);
    window.addEventListener("resize", mesurer); window.addEventListener("scroll", mesurer, true);
    return () => { clearTimeout(t); window.removeEventListener("resize", mesurer); window.removeEventListener("scroll", mesurer, true); };
  }, [etape]);

  useEffect(() => {
    if (i === null) return;
    const clavier = (e: KeyboardEvent) => {
      if (e.key === "Escape") finir();
      if (e.key === "ArrowRight") setI((x) => (x !== null && x < presentes.length - 1 ? x + 1 : x));
      if (e.key === "ArrowLeft") setI((x) => (x ? x - 1 : x));
    };
    window.addEventListener("keydown", clavier);
    return () => window.removeEventListener("keydown", clavier);
  }, [i, presentes.length, finir]);

  if (!etape || i === null) return null;
  const marge = 8;
  const bas = cadre ? cadre.bottom + 12 : 120;
  const enDessous = !cadre || bas + 200 < window.innerHeight;
  const haut = enDessous ? bas : Math.max(12, (cadre?.top ?? 0) - 212);
  const gauche = Math.min(Math.max(12, cadre?.left ?? 12), window.innerWidth - 392);
  const derniere = i === presentes.length - 1;
  return (
    <div className="visite" role="dialog" aria-modal="true" aria-label={`Visite guidée : ${etape.titre}`}>
      {cadre && <div className="visite-halo" style={{ top: cadre.top - marge, left: cadre.left - marge,
        width: cadre.width + 2 * marge, height: cadre.height + 2 * marge }} />}
      <div className="visite-bulle" style={{ top: haut, left: gauche }}>
        <div className="discret">{i + 1} / {presentes.length}</div>
        <h3>{etape.titre}</h3>
        <p>{etape.texte}</p>
        <div className="actions">
          <button type="button" onClick={finir}>Passer la visite</button>
          <span style={{ flex: 1 }} />
          {i > 0 && <button type="button" onClick={() => setI(i - 1)}>Précédent</button>}
          <button type="button" className="principal" onClick={() => (derniere ? finir() : setI(i + 1))}>
            {derniere ? "Terminer" : "Suivant"}</button>
        </div>
      </div>
    </div>
  );
}
