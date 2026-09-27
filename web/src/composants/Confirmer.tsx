import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { Erreur } from "./communs";
import { t } from "../i18n";

export interface Demande {
  titre: string;
  message: ReactNode;
  /** Le mot à écrire pour confirmer (« SUPPRIMER ») : un clic distrait ne suffit pas. */
  mot?: string;
  bouton?: string;
  /** L'acte lui-même : s'il échoue, l'erreur s'affiche dans la fenêtre, qui reste ouverte. */
  action: () => Promise<unknown>;
}

/** Une confirmation écrite, dans une fenêtre au-dessus de la page, qui ne bouge rien derrière elle.
 *  `demander(...)` l'ouvre ; rendre `fenetre` quelque part dans la page. */
export function useConfirmation(): [(d: Demande) => void, ReactNode] {
  const [demande, setDemande] = useState<Demande | null>(null);
  const fenetre = demande && <Fenetre demande={demande} onFermer={() => setDemande(null)} />;
  return [setDemande, fenetre];
}

function Fenetre({ demande, onFermer }: { demande: Demande; onFermer: () => void }) {
  const [saisie, setSaisie] = useState("");
  const [erreur, setErreur] = useState<unknown>(null);
  const [enCours, setEnCours] = useState(false);
  const titre = useId();
  const champ = useRef<HTMLInputElement>(null);
  const bouton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    (demande.mot ? champ.current : bouton.current)?.focus();
    const echap = (e: KeyboardEvent) => { if (e.key === "Escape") onFermer(); };
    document.addEventListener("keydown", echap);
    return () => document.removeEventListener("keydown", echap);
  }, [demande, onFermer]);
  const pret = !demande.mot || saisie.trim().toUpperCase() === demande.mot;

  async function confirmer(ev: React.FormEvent) {
    ev.preventDefault();
    if (!pret || enCours) return;
    setErreur(null);
    setEnCours(true);
    try {
      await demande.action();
      onFermer();
    } catch (e) {
      setErreur(e);
      setEnCours(false);
    }
  }

  return createPortal(
    <div className="voile" onMouseDown={(e) => { if (e.target === e.currentTarget) onFermer(); }}>
      <form role="dialog" aria-modal="true" aria-labelledby={titre} className="carte fenetre" onSubmit={confirmer}>
        <h2 id={titre}>{demande.titre}</h2>
        <div>{demande.message}</div>
        {demande.mot && (
          <label>{t("Pour confirmer, écrire ", "To confirm, type ")}<code>{demande.mot}</code>
            <input ref={champ} aria-label={t("Confirmation", "Confirmation")} value={saisie} autoComplete="off"
                   onChange={(e) => setSaisie(e.target.value)} />
          </label>
        )}
        <Erreur erreur={erreur} />
        <div className="actions">
          <button ref={bouton} className="danger" disabled={!pret || enCours}>{demande.bouton ?? t("Supprimer", "Delete")}</button>
          <button type="button" onClick={onFermer}>{t("Annuler", "Cancel")}</button>
        </div>
      </form>
    </div>,
    document.body,
  );
}
