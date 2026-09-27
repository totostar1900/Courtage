// Du passif à la cotisation, au franc près : chaque ligne affichée, et leur somme est le total affiché.
// Une ligne d'arrondi n'apparaît que si elle existe (chaque total est arrondi au franc séparément).
import { t as tr } from "./i18n";
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
    { libelle: tr("Dette actuarielle", "Actuarial liability"), montant: t.dette, note: tr("les droits acquis à la date d'évaluation", "rights vested at the valuation date") },
    { libelle: tr("Charge annuelle", "Annual cost"), montant: t.charge, note: tr("les droits de l'année qui vient", "rights earned over the coming year") },
    { libelle: tr("Fonds constitué", "Accumulated fund"), montant: -fonds, note: tr("déjà placé chez l'assureur", "already invested with the insurer") },
  ];
  if (besoin < 0) {
    lignes.push({ libelle: tr("Excédent du fonds, non reversé", "Fund surplus, not refunded"), montant: -besoin,
                  note: tr("le fonds couvre plus que l'engagement : aucune cotisation n'est due", "the fund exceeds the liability: no contribution is due") });
  } else if (nette !== besoin) {
    lignes.push({ libelle: tr("Arrondi", "Rounding"), montant: nette - besoin, note: tr("chaque total est arrondi au franc", "each total is rounded to the franc") });
  }
  lignes.push({ libelle: tr("Cotisation nette", "Net contribution"), montant: nette, total: true });
  lignes.push({ libelle: tr(`Frais de gestion sur cotisation (${(tauxFrais * 100).toLocaleString("fr-FR")} %)`,
                             `Management charges on contributions (${(tauxFrais * 100).toLocaleString("en-GB")}%)`),
                montant: totale - nette, note: tr("prélevés par l'assureur sur ce qui est versé", "deducted by the insurer from what is paid in") });
  lignes.push({ libelle: tr("Cotisation à verser", "Contribution payable"), montant: totale, total: true });
  return lignes;
}

/** Le taux de frais de l'étude ; à défaut (une étude ancienne), celui que ses montants impliquent. */
export function tauxFrais(valeurs: Record<string, unknown>, t?: Totaux): number {
  const v = Number(valeurs["frais_sur_cotisation"]);
  if (Number.isFinite(v)) return v;
  const nette = t?.cotisation_nette ?? 0;
  return nette > 0 ? Math.round(((t!.cotisation_totale ?? nette) / nette - 1) * 1000) / 1000 : 0;
}
