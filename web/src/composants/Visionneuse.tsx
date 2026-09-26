import { useEffect, useState } from "react";

/** Les pages d'un document, affichées sur place (démonstration : pas de PDF à ouvrir dans un onglet). */
export default function Visionneuse() {
  const [pages, setPages] = useState<string[] | null>(null);
  useEffect(() => {
    const ouvrir = (e: Event) => setPages((e as CustomEvent<string[]>).detail);
    const echap = (e: KeyboardEvent) => e.key === "Escape" && setPages(null);
    window.addEventListener("courtage:document", ouvrir);
    window.addEventListener("keydown", echap);
    return () => { window.removeEventListener("courtage:document", ouvrir); window.removeEventListener("keydown", echap); };
  }, []);
  if (!pages) return null;
  return (
    <div className="visionneuse" role="dialog" aria-label="Document" onClick={() => setPages(null)}>
      <button className="principal fermer" onClick={() => setPages(null)}>Fermer le document</button>
      <div className="feuilles" onClick={(e) => e.stopPropagation()}>
        {pages.length ? pages.map((p, i) => <img key={i} src={p} alt={`Page ${i + 1}`} />)
          : <p style={{ color: "#fff" }}>Document indisponible dans la démonstration.</p>}
      </div>
    </div>
  );
}
