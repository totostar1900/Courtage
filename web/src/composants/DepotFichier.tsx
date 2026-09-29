import { useId, useRef, useState, type DragEvent, type ReactNode } from "react";

import { t } from "../i18n";

/** Taille lisible : « 38 Ko », « 1,2 Mo ». */
export function taille(octets: number): string {
  if (octets < 1024) return `${octets} o`;
  if (octets < 1024 * 1024) return `${Math.round(octets / 1024)} Ko`;
  return `${(octets / 1024 / 1024).toFixed(1).replace(".", ",")} Mo`;
}

/** Le dépôt d'un fichier : une zone à glisser ou à cliquer, puis le fichier retenu en clair, avec « Retirer ».
 *
 *  Le champ natif disait « aucun fichier choisi » quand le fichier venait d'ailleurs (l'essai repris du navigateur) :
 *  ici, ce qui s'affiche est ce qui sera envoyé. Contrôlé (`fichier` + `onChange`), ou dans un formulaire (`name` :
 *  le champ reste dans le formulaire, « Retirer » le vide). */
export function DepotFichier({ libelle, accept, aide, fichier, onChange, name, required, disabled }: {
  libelle: ReactNode; accept?: string; aide?: ReactNode; fichier?: File | null; onChange?: (f: File | null) => void;
  name?: string; required?: boolean; disabled?: boolean;
}) {
  const champ = useRef<HTMLInputElement>(null);
  const id = useId();
  const [interne, setInterne] = useState<File | null>(null);
  const [survol, setSurvol] = useState(false);
  const controle = fichier !== undefined;
  const courant = controle ? fichier : interne;

  function choisir(f: File | null) {
    if (!controle) setInterne(f);
    onChange?.(f);
  }
  function retirer() {
    if (champ.current) champ.current.value = "";
    choisir(null);
  }
  function lacher(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setSurvol(false);
    const f = e.dataTransfer.files?.[0];
    if (!f || disabled) return;
    if (champ.current && typeof DataTransfer !== "undefined") {
      try { const dt = new DataTransfer(); dt.items.add(f); champ.current.files = dt.files; } catch { /* navigateur ancien */ }
    }
    choisir(f);
  }

  return (
    <div className={`televersement${courant ? " rempli" : ""}${survol ? " survol" : ""}${disabled ? " inactif" : ""}`}>
      <label onDragOver={(e) => { e.preventDefault(); setSurvol(true); }} onDragLeave={() => setSurvol(false)} onDrop={lacher}>
        <span className="televersement-libelle" id={`${id}-libelle`}>{libelle}</span>
        <input ref={champ} type="file" className="visuellement-cache" aria-labelledby={`${id}-libelle`} accept={accept} name={name} required={required && !courant}
               disabled={disabled} onChange={(e) => choisir(e.target.files?.[0] ?? null)} />
        {!courant && (
          <span className="televersement-zone" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8"
                 strokeLinecap="round" strokeLinejoin="round"><path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></svg>
            <span><strong>{t("Choisir un fichier", "Choose a file")}</strong>{t(" ou le glisser ici", " or drop it here")}</span>
          </span>
        )}
      </label>
      {courant && (
        <div className="televersement-fichier" role="status">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"
               strokeLinecap="round" strokeLinejoin="round"><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z" /><path d="M14 3v5h5" /></svg>
          <span className="televersement-nom">{courant.name}</span>
          <span className="discret">{taille(courant.size)}</span>
          {!disabled && <>
            <button type="button" className="lien" onClick={() => champ.current?.click()}>{t("Changer", "Change")}</button>
            <button type="button" className="lien" onClick={retirer}
                    aria-label={t(`Retirer ${courant.name}`, `Remove ${courant.name}`)}>{t("Retirer", "Remove")}</button>
          </>}
        </div>
      )}
      {aide && <div className="discret televersement-aide">{aide}</div>}
    </div>
  );
}
