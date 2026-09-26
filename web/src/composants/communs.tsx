import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { ErreurApi } from "../api";
import type { Anomalie, Annee, Constat } from "../types";
import { montant, pct } from "../format";
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

/** L'échéancier des départs : une barre par année ; au survol, au clavier ou d'un toucher, une bulle dit
 *  l'année — départs, prestations probables, indemnité si tous partent, valeur actuelle, part et cumul. */
export function Echeancier({ annees }: { annees: Annee[] }) {
  const [actif, setActif] = useState<number | null>(null);
  const graphique = useRef<HTMLDivElement>(null);
  const [largeur, setLargeur] = useState(0);
  useEffect(() => { if (actif !== null && graphique.current) setLargeur(graphique.current.clientWidth); }, [actif]);
  if (!annees.length) return null;
  // Une barre par année, départs ou non : l'axe du temps ne se comprime pas.
  const premiere = annees[0].annee;
  const derniere = annees[annees.length - 1].annee;
  const par = new Map(annees.map((a) => [a.annee, a]));
  const toutes = Array.from({ length: derniere - premiere + 1 }, (_, i) =>
    par.get(premiere + i) ?? { annee: premiere + i, effectif: 0, ifc: 0, prestations_probables: 0, vapf: 0 });
  const probable = (a: Annee) => a.prestations_probables ?? a.ifc;
  const max = Math.max(...toutes.map(probable), 1);
  const total = toutes.reduce((t, a) => t + probable(a), 0) || 1;
  const cumuls = toutes.reduce<number[]>((c, a) => [...c, (c.at(-1) ?? 0) + probable(a)], []);
  const departs = (n: number) => `${n} départ${n > 1 ? "s" : ""} à la retraite`;
  const a = actif === null ? null : toutes[actif];
  // La bulle se pose au-dessus de sa barre, centrée sur elle sauf près d'un bord ; la flèche vise la barre.
  const LARGEUR_BULLE = 270;
  const centre = actif === null ? 0 : ((actif + 0.5) / toutes.length) * largeur;
  const gauche = Math.min(Math.max(centre - LARGEUR_BULLE / 2, 0), Math.max(largeur - LARGEUR_BULLE, 0));
  const hauteur = a ? (probable(a) / max) * 100 : 0;
  return (
    <div className="echeancier" onMouseLeave={() => setActif(null)}>
      <div className="barres" ref={graphique} aria-label="Prestations probables par année">
        {toutes.map((x, i) => (
          <button key={x.annee} type="button" className={`barre${i === actif ? " active" : ""}`}
                  style={{ height: `${(probable(x) / max) * 100}%` }}
                  aria-label={`${x.annee} : ${x.effectif ? departs(x.effectif).replace(" à la retraite", "") : "aucun départ"}, ${montant(probable(x))}`}
                  aria-describedby={i === actif ? "echeancier-bulle" : undefined}
                  onMouseEnter={() => setActif(i)} onFocus={() => setActif(i)} onBlur={() => setActif(null)}
                  onClick={() => setActif(i)} onKeyDown={(e) => e.key === "Escape" && setActif(null)} />
        ))}
      </div>
      {a && actif !== null && (
        <div role="tooltip" id="echeancier-bulle" className="bulle-barre"
             style={{ left: gauche, bottom: `${hauteur * 1.32 + 32}px`,
                      ["--fleche" as string]: `${Math.min(Math.max(centre - gauche, 14), LARGEUR_BULLE - 14)}px` }}>
          <strong>{a.annee}</strong>
          {a.effectif === 0 ? <div>Aucun départ à la retraite prévu</div> : (
            <>
              <div>{departs(a.effectif)}</div>
              <dl>
                <dt>Prestations probables</dt><dd>{montant(probable(a))}</dd>
                <dt>Si tous partent</dt><dd>{montant(a.ifc)}</dd>
                <dt>Valeur actuelle</dt><dd>{montant(a.vapf)}</dd>
                <dt>Part du total</dt><dd>{pct(probable(a) / total)}</dd>
                <dt>Cumul depuis {premiere}</dt><dd>{montant(cumuls[actif])}</dd>
              </dl>
              <p className="discret">Probables : l'indemnité pondérée par la chance d'être en vie et encore dans
                l'entreprise ce jour-là. Valeur actuelle : ce que ce versement futur vaut aujourd'hui.</p>
            </>
          )}
        </div>
      )}
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
