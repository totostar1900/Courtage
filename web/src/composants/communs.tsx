import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { ErreurApi } from "../api";
import type { Anomalie, Constat } from "../types";
import type { CleTerme } from "../guide/glossaire";
import { Terme } from "./Terme";

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
      {motifs && <div className="discret">Motifs : {motifs.map(libelleMotif).join(" · ")}</div>}
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

const NIVEAUX: Record<string, { libelle: string; classe: string }> = {
  bloque: { libelle: "Bloquant", classe: "grave" },
  bloquant: { libelle: "Bloquant", classe: "grave" },
  avertit: { libelle: "Attention", classe: "attention" },
  avertissement: { libelle: "Attention", classe: "attention" },
  informe: { libelle: "Bon à savoir", classe: "neutre" },
};

export function Constats({ constats, vide = "Rien à signaler." }: { constats: Constat[]; vide?: string }) {
  if (!constats.length) return <p className="discret">{vide}</p>;
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
            <p className="discret">Sources : {c.sources.map((s) => s.titre).join(" ; ")}</p>
          )}
        </div>
      ))}
    </div>
  );
}

export function Anomalies({ anomalies }: { anomalies: Anomalie[] }) {
  return (
    <Constats
      vide="Aucune anomalie."
      constats={anomalies.map((a) => ({
        niveau: a.niveau === "bloquant" ? "bloque" : "avertit",
        code: a.code,
        titre: libelleMotif(a.code) + (a.ligne ? ` — ligne ${a.ligne}` : ""),
        message: a.message,
      }))}
    />
  );
}

export { Echeancier } from "./Echeancier";

const MOTIFS: Record<string, string> = {
  pays_different: "convention d'un autre pays",
  convention_a_valider: "convention à valider",
  hors_vigueur: "convention hors vigueur à la date",
  remuneration_absente: "conditions de rémunération à fixer",
  dossier_suspendu: "dossier suspendu : rien ne s'émet avant sa reprise",
  dossier_cloture: "dossier clôturé : il ne se modifie plus",
  donnees_trop_anciennes: "données de plus de 12 mois",
  matricule_double: "matricule en double",
  regime_non_adopte: "version du régime encore en projet : l'entreprise l'adopte d'abord",
  regime_hors_vigueur: "une autre version du régime est en vigueur",
  non_conformite: "régime sous la convention",
  sous_le_plancher: "sous la convention collective",
  au_dela_de_la_retraite: "au-delà de l'âge de retraite",
  poids_excessif: "un salarié pèse lourd",
  base_salaire_approchee: "base de salaire approchée",
  evenements_non_evalues: "événements non chiffrés",
  ecart_etude_precedente: "écart avec l'étude précédente",
  champ_manquant: "champ manquant",
  date_illisible: "date illisible",
  dates_estimees: "dates probablement estimées",
  commission_sans_mandat: "commission sans mandat de courtage",
  verse_sous_le_du: "versé sous le dû",
  verse_au_dela_du_du: "versé au-delà du dû",
  fonds_demande_au_dela_du_verse: "demande au fonds supérieure au versé",
  fonds_paye_au_dela_demande: "fonds payé au-delà de la demande",
  encore_present: "encore présent dans le personnel",
  motif_inconnu: "motif inconnu",
  depart_en_double: "départ en double",
  depart_avant_embauche: "départ avant l'embauche",
  deja_enregistree: "départ déjà enregistré",
  date_paiement_requise: "paiement sans date",
  montant_illisible: "montant illisible",
  colonnes_introuvables: "colonnes introuvables",
  categorie_inconnue: "catégorie sans règle",
  convention_requise: "convention à préciser",
  a_relire: "à relire",
  non_trouve: "non trouvé dans le texte",
  hors_cemac: "hors CEMAC",
  autre_pays: "un autre pays",
  citation_introuvable: "passage introuvable",
  texte_illisible: "texte illisible",
  bareme_absent: "barème absent",
  derniere_tranche_ouverte: "dernière tranche à vérifier",
  rien_a_reprendre: "rien à reprendre",
  sans_categorie_generale: "pas de catégorie générale",
};

const majuscule = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

export function libelleMotif(code: string): string {
  return MOTIFS[code] ?? code.replace(/_/g, " ");
}

/** Un panneau qui s'ouvre sur la page (résultats, formulaire, détail) et se referme : une croix en haut,
 *  toujours au même endroit. À l'ouverture, la page vient à lui. */
export function Volet({ titre, onFermer, children, className = "" }:
  { titre: ReactNode; onFermer: () => void; children: ReactNode; className?: string }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => { ref.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" }); }, []);
  return (
    <section ref={ref} className={`carte volet ${className}`}>
      <div className="volet-tete">
        <h2>{titre}</h2>
        <button type="button" className="fermer-volet" onClick={onFermer} aria-label="Fermer" title="Fermer">×</button>
      </div>
      {children}
    </section>
  );
}
