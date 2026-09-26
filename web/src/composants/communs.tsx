import { useCallback, useEffect, useState, type ReactNode } from "react";

import { ErreurApi } from "../api";
import type { Anomalie, Annee, Constat } from "../types";
import { montant } from "../format";

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

export function Cle({ etiquette, valeur, sous }: { etiquette: string; valeur: ReactNode; sous?: ReactNode }) {
  return (
    <div className="carte cle">
      <div className="etiquette">{etiquette}</div>
      <div className="valeur">{valeur}</div>
      {sous && <div className="sous">{sous}</div>}
    </div>
  );
}

const NIVEAUX: Record<string, { libelle: string; classe: string }> = {
  bloque: { libelle: "Bloque", classe: "grave" },
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
            {c.titre ?? libelleMotif(c.code)}
            {c.statut_contenu === "a_valider" && <span className="etat attention">À valider par un juriste</span>}
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

/** L'échéancier des départs : une barre par année, le montant au survol. */
export function Echeancier({ annees }: { annees: Annee[] }) {
  if (!annees.length) return null;
  // Une barre par année, départs ou non : l'axe du temps ne se comprime pas.
  const premiere = annees[0].annee;
  const derniere = annees[annees.length - 1].annee;
  const par = new Map(annees.map((a) => [a.annee, a]));
  const toutes = Array.from({ length: derniere - premiere + 1 }, (_, i) =>
    par.get(premiere + i) ?? { annee: premiere + i, effectif: 0, ifc: 0, prestations_probables: 0, vapf: 0 });
  const max = Math.max(...toutes.map((a) => a.prestations_probables ?? a.ifc), 1);
  return (
    <div>
      <div className="barres" aria-label="Prestations probables par année">
        {toutes.map((a) => {
          const v = a.prestations_probables ?? a.ifc;
          return (
            <div key={a.annee} className="barre" style={{ height: `${(v / max) * 100}%` }}
                 title={`${a.annee} : ${a.effectif} départ(s), ${montant(v)}`} />
          );
        })}
      </div>
      <div className="axe"><span>{premiere}</span><span>{derniere}</span></div>
    </div>
  );
}

const MOTIFS: Record<string, string> = {
  pays_different: "convention d'un autre pays",
  convention_a_valider: "convention à valider",
  hors_vigueur: "convention hors vigueur à la date",
  remuneration_absente: "conditions de rémunération à fixer",
  donnees_trop_anciennes: "données de plus de 12 mois",
  matricule_double: "matricule en double",
  regime_non_adopte: "régime non adopté",
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
};

export function libelleMotif(code: string): string {
  return MOTIFS[code] ?? code.replace(/_/g, " ");
}
