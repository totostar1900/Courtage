import { useEffect, useState } from "react";

import { t } from "../i18n";

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
    <div className="visionneuse" role="dialog" aria-label={t("Document", "Document")} onClick={() => setPages(null)}>
      <button className="principal fermer" onClick={() => setPages(null)}>{t("Fermer le document", "Close the document")}</button>
      <div className="feuilles" onClick={(e) => e.stopPropagation()}>
        {pages.length ? pages.map((p, i) => <img key={i} src={p} alt={t(`Page ${i + 1}`, `Page ${i + 1}`)} />)
          : <p style={{ color: "#f5f7f9" }}>{t("Document indisponible dans la démonstration.", "Document not available in the demo.")}</p>}
      </div>
    </div>
  );
}
