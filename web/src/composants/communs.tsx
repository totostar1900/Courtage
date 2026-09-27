import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { ErreurApi } from "../api";
import type { Anomalie, Constat } from "../types";
import type { CleTerme } from "../guide/glossaire";
import { Terme } from "./Terme";
import { t } from "../i18n";

/** Charge une donnée, garde l'erreur, sait recharger. */
export function useCharge<T>(charger: () => Promise<T>, deps: unknown[]) {
  const [donnee, setDonnee] = useState<T | null>(null);
  const [erreur, setErreur] = useState<Error | null>(null);
  const [enCours, setEnCours] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const recharger = useCallback(() => {
    setEnCours(true);
    charger()
      .then((d) => { setDonnee(d); setErreur(null); })
      .catch((e: Error) => setErreur(e))
      .finally(() => setEnCours(false));
  }, deps);
  useEffect(recharger, [recharger]);
  return { donnee, erreur, enCours, recharger };
}

export function Erreur({ erreur }: { erreur: unknown }) {
  if (!erreur) return null;
  const message = erreur instanceof Error ? erreur.message : String(erreur);
  const motifs = erreur instanceof ErreurApi ? (erreur.details?.motifs as string[] | undefined) : undefined;
  return (
    <div className="erreur" role="alert">
      {message}
      {motifs && <div className="discret">{t("Motifs : ", "Reasons: ")}{motifs.map(libelleMotif).join(" · ")}</div>}
    </div>
  );
}

export function Cle({ etiquette, valeur, sous, terme }:
  { etiquette: string; valeur: ReactNode; sous?: ReactNode; terme?: CleTerme }) {
  return (
    <div className="carte cle">
      <div className="etiquette">{terme ? <Terme cle={terme}>{etiquette}</Terme> : etiquette}</div>
      <div className="valeur">{valeur}</div>
      {sous && <div className="sous">{sous}</div>}
    </div>
  );
}

const niveaux = (): Record<string, { libelle: string; classe: string }> => ({
  bloque: { libelle: t("Bloquant", "Blocking"), classe: "grave" },
  bloquant: { libelle: t("Bloquant", "Blocking"), classe: "grave" },
  avertit: { libelle: t("Attention", "Warning"), classe: "attention" },
  avertissement: { libelle: t("Attention", "Warning"), classe: "attention" },
  informe: { libelle: t("Bon à savoir", "Good to know"), classe: "neutre" },
});

export function Constats({ constats, vide }: { constats: Constat[]; vide?: string }) {
  if (!constats.length) return <p className="discret">{vide ?? t("Rien à signaler.", "Nothing to report.")}</p>;
  const NIVEAUX = niveaux();
  return (
    <div>
      {constats.map((c, i) => (
        <div key={`${c.code}-${i}`} className={`constat ${c.niveau}`} data-code={c.code}>
          <div className="titre">
            <span className={`etat ${NIVEAUX[c.niveau].classe}`}>{NIVEAUX[c.niveau].libelle}</span>
            {majuscule(c.titre ?? libelleMotif(c.code))}
          </div>
          <p>{c.message}</p>
          {!!c.sources?.length && (
            <p className="discret">{t("Sources : ", "Sources: ")}{c.sources.map((s) => s.titre).join(" ; ")}</p>
          )}
        </div>
      ))}
    </div>
  );
}

export function Anomalies({ anomalies }: { anomalies: Anomalie[] }) {
  return (
    <Constats
      vide={t("Aucune anomalie.", "No anomalies.")}
      constats={anomalies.map((a) => ({
        niveau: a.niveau === "bloquant" ? "bloque" : "avertit",
        code: a.code,
        titre: libelleMotif(a.code) + (a.ligne ? t(` — ligne ${a.ligne}`, ` — row ${a.ligne}`) : ""),
        message: a.message,
      }))}
    />
  );
}

export { Echeancier } from "./Echeancier";

/** Le libellé de chaque code de motif. Une fonction : la langue se lit à l'appel, jamais à l'import. */
const motifs = (): Record<string, string> => ({
  pays_different: t("convention d'un autre pays", "agreement from another country"),
  convention_a_valider: t("convention à valider", "agreement to be validated"),
  hors_vigueur: t("convention hors vigueur à la date", "agreement not in force at that date"),
  dossier_suspendu: t("dossier suspendu : rien ne s'émet avant sa reprise", "file suspended: nothing is issued until it resumes"),
  dossier_cloture: t("dossier clôturé : il ne se modifie plus", "file closed: it can no longer be changed"),
  donnees_trop_anciennes: t("données de plus de 12 mois", "data more than 12 months old"),
  matricule_double: t("matricule en double", "duplicate employee number"),
  regime_non_adopte: t("version du régime encore en projet : l'entreprise l'adopte d'abord", "plan version still a draft: the company adopts it first"),
  regime_hors_vigueur: t("une autre version du régime est en vigueur", "another plan version is in force"),
  non_conformite: t("régime sous la convention", "plan below the agreement"),
  sous_le_plancher: t("sous la convention collective", "below the collective agreement"),
  au_dela_de_la_retraite: t("au-delà de l'âge de retraite", "beyond retirement age"),
  poids_excessif: t("un salarié pèse lourd", "one employee weighs heavily"),
  base_salaire_approchee: t("base de salaire approchée", "approximate salary base"),
  evenements_non_evalues: t("événements non chiffrés", "events not costed"),
  ecart_etude_precedente: t("écart avec l'étude précédente", "gap with the previous study"),
  champ_manquant: t("champ manquant", "missing field"),
  date_illisible: t("date illisible", "unreadable date"),
  dates_estimees: t("dates probablement estimées", "dates probably estimated"),
  verse_sous_le_du: t("versé sous le dû", "paid below the amount due"),
  verse_au_dela_du_du: t("versé au-delà du dû", "paid above the amount due"),
  fonds_demande_au_dela_du_verse: t("demande au fonds supérieure au versé", "fund claim above the amount paid in"),
  fonds_paye_au_dela_demande: t("fonds payé au-delà de la demande", "fund paid above the claim"),
  encore_present: t("encore présent dans le personnel", "still on the workforce"),
  motif_inconnu: t("motif inconnu", "unknown reason"),
  depart_en_double: t("départ en double", "duplicate departure"),
  depart_avant_embauche: t("départ avant l'embauche", "departure before hire"),
  deja_enregistree: t("départ déjà enregistré", "departure already recorded"),
  date_paiement_requise: t("paiement sans date", "payment without a date"),
  montant_illisible: t("montant illisible", "unreadable amount"),
  colonnes_introuvables: t("colonnes introuvables", "columns not found"),
  categorie_inconnue: t("catégorie sans règle", "category without a rule"),
  convention_requise: t("convention à préciser", "agreement to be specified"),
  a_relire: t("à relire", "to review"),
  non_trouve: t("non trouvé dans le texte", "not found in the text"),
  hors_cemac: t("hors CEMAC", "outside CEMAC"),
  autre_pays: t("un autre pays", "another country"),
  citation_introuvable: t("passage introuvable", "passage not found"),
  texte_illisible: t("texte illisible", "unreadable text"),
  bareme_absent: t("barème absent", "scale missing"),
  derniere_tranche_ouverte: t("dernière tranche à vérifier", "last band to check"),
  rien_a_reprendre: t("rien à reprendre", "nothing to import"),
  sans_categorie_generale: t("pas de catégorie générale", "no general category"),
});

const majuscule = (x: string) => x.charAt(0).toUpperCase() + x.slice(1);

export function libelleMotif(code: string): string {
  return motifs()[code] ?? code.replace(/_/g, " ");
}

/** Un panneau qui s'ouvre sur la page (résultats, formulaire, détail) et se referme : une croix en haut,
 *  toujours au même endroit. À l'ouverture, la page vient à lui. */
const DansTiroir = createContext(false);

/** Un panneau fixé à droite (plein écran sur téléphone), au-dessus de la page : ce qui s'y ouvre ou s'y ferme ne
 *  déplace rien derrière. Échap le ferme. Un `Volet` qu'il contient ne fait pas défiler la page. */
export function Tiroir({ onFermer, children, etiquette }: { onFermer: () => void; children: ReactNode; etiquette: string }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const echap = (e: KeyboardEvent) => { if (e.key === "Escape" && !document.querySelector(".voile")) onFermer(); };
    document.addEventListener("keydown", echap);
    return () => document.removeEventListener("keydown", echap);
  }, [onFermer]);
  useEffect(() => { ref.current?.scrollTo?.(0, 0); }, [children]);
  return createPortal(
    <aside ref={ref} className="tiroir" aria-label={etiquette}>
      <DansTiroir.Provider value={true}>{children}</DansTiroir.Provider>
    </aside>,
    document.body,
  );
}

export function Volet({ titre, onFermer, children, className = "" }:
  { titre: ReactNode; onFermer: () => void; children: ReactNode; className?: string }) {
  const ref = useRef<HTMLElement>(null);
  const tiroir = useContext(DansTiroir);
  useEffect(() => { if (!tiroir) ref.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" }); }, [tiroir]);
  return (
    <section ref={ref} className={tiroir ? "volet dans-tiroir" : `carte volet ${className}`}>
      <div className="volet-tete">
        <h2>{titre}</h2>
        <button type="button" className="fermer-volet" onClick={onFermer} aria-label={t("Fermer", "Close")} title={t("Fermer", "Close")}>×</button>
      </div>
      {children}
    </section>
  );
}
