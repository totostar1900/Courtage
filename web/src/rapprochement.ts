// Du passif à la cotisation, au franc près : chaque ligne affichée, et leur somme est le total affiché.
// Une ligne d'arrondi n'apparaît que si elle existe (chaque total est arrondi au franc séparément).
import type { Totaux } from "./types";

export interface LigneRapprochement {
  libelle: string;
  montant: number;          // signé : ce qui s'ajoute (+) ou se retranche (−)
  total?: boolean;          // un sous-total : la somme de ce qui précède
  note?: string;
}

export function rapprocher(t: Totaux, fonds: number, tauxFrais: number): LigneRapprochement[] {
  const nette = t.cotisation_nette ?? 0;
  const totale = t.cotisation_totale ?? nette;
  const besoin = t.dette + t.charge - fonds;
  const lignes: LigneRapprochement[] = [
    { libelle: "Dette actuarielle", montant: t.dette, note: "les droits acquis à la date d'évaluation" },
    { libelle: "Charge annuelle", montant: t.charge, note: "les droits de l'année qui vient" },
    { libelle: "Fonds constitué", montant: -fonds, note: "déjà placé chez l'assureur" },
  ];
  if (besoin < 0) {
    lignes.push({ libelle: "Excédent du fonds, non reversé", montant: -besoin,
                  note: "le fonds couvre plus que l'engagement : aucune cotisation n'est due" });
  } else if (nette !== besoin) {
    lignes.push({ libelle: "Arrondi", montant: nette - besoin, note: "chaque total est arrondi au franc" });
  }
  lignes.push({ libelle: "Cotisation nette", montant: nette, total: true });
  lignes.push({ libelle: `Frais de gestion sur cotisation (${(tauxFrais * 100).toLocaleString("fr-FR")} %)`,
                montant: totale - nette, note: "prélevés par l'assureur sur ce qui est versé" });
  lignes.push({ libelle: "Cotisation à verser", montant: totale, total: true });
  return lignes;
}

export function tauxFrais(valeurs: Record<string, number | string>): number {
  const v = Number(valeurs["frais_sur_cotisation"] ?? 0);
  return Number.isFinite(v) ? v : 0;
}
