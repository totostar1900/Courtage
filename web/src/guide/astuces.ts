// « Le saviez-vous ? » : une phrase vraie et utile, avec le chapitre qui la développe.

import { t } from "../i18n";
import { listeVivante } from "./visite";

export interface Astuce { texte: string; chapitre?: string; lecon?: string }

/** Les astuces, dans la langue du moment : une fonction, lue au rendu. */
export function astuces(): Astuce[] {
  return [
  { texte: t("Au Cameroun, la convention du commerce révisée en janvier 2024 a relevé le barème d'IFC : 45 % d'un mois par année au lieu de 40 % pour les cinq premières années, 80 % au lieu de 75 % au-delà de vingt ans.",
      "In Cameroon, the commerce collective agreement revised in January 2024 raised the end-of-service benefit scale: 45% of a month per year instead of 40% for the first five years, and 80% instead of 75% beyond twenty years."), chapitre: "conventions" },
  { texte: t("Un point de taux d'actualisation en moins augmente souvent la dette de l'ordre de 10 % : l'étude montre toujours cette sensibilité.",
      "One point less on the discount rate often raises the liability by around 10%: the study always shows this sensitivity."), chapitre: "comprendre" },
  { texte: t("Un salarié qui quitte l'entreprise avant la retraite ne coûte pas d'IFC : c'est pourquoi la rotation du personnel réduit l'engagement.",
      "An employee who leaves the company before retirement costs no end-of-service benefit: that is why staff turnover reduces the liability."), lecon: "ifc-en-2-minutes" },
  { texte: t("Votre fichier peut garder sa colonne de noms : elle est ignorée, ni lue ni conservée.",
      "Your file can keep its names column: it is ignored, neither read nor stored."), lecon: "donnees-personnelles" },
  { texte: t("Le fonds placé chez l'assureur vous appartient : il se retranche de la cotisation, et il vous suit si vous changez d'assureur selon les conditions de transfert.",
      "The fund held with the insurer belongs to you: it is deducted from the contribution, and it follows you if you change insurer, subject to the transfer terms."), chapitre: "financer" },
  { texte: t("La cotisation à verser comprend les frais de l'assureur : 4 % par défaut. Le tableau « Du passif à la cotisation » les montre ligne à ligne.",
      "The contribution to pay includes the insurer's charges: 4% by default. The “From liability to contribution” table shows them line by line."), lecon: "lire-les-chiffres" },
  { texte: t("Un rapport émis se vérifie en ligne par n'importe qui, sans compte : il suffit de son numéro RL-….",
      "An issued report can be verified online by anyone, without an account: its RL-… number is all it takes."), chapitre: "verifier" },
  { texte: t("Un régime peut différer par catégorie : les cadres peuvent avoir un barème plus généreux que le reste du personnel.",
      "A plan can differ by category: managers can have a more generous scale than the rest of the workforce."), chapitre: "regime" },
  { texte: t("La provision interne n'a aucun frais, mais aucun rendement : trois départs la même année se paient sur la trésorerie du moment.",
      "An internal provision has no charges, but no return either: three departures in the same year are paid from the cash available at the time."), chapitre: "financer" },
  { texte: t("Dans le cahier des charges, aucune ligne ne décrit moins de trois salariés : un assureur ne peut reconnaître personne.",
      "In the specifications, no line describes fewer than three employees: an insurer cannot identify anyone."), chapitre: "cahier" },
  { texte: t("Un départ en démission ne coûte pas d'IFC, mais l'enregistrer (sans nom) mesure la rotation réelle de votre personnel — et une rotation mesurée vaut mieux qu'une rotation supposée.",
      "A resignation costs no end-of-service benefit, but recording it (without a name) measures your actual staff turnover — and measured turnover beats assumed turnover."), chapitre: "departs" },
  { texte: t("En courtage, l'identité d'un bénéficiaire ne sert qu'à son paiement : elle est effacée douze mois après, et le dossier scellé se vérifie toujours par son numéro.",
      "Under brokerage, a beneficiary's identity is used only for their payment: it is erased twelve months later, and the sealed file can still be verified by its number."), chapitre: "departs" },
  { texte: t("La fiche de calcul scellée d'un départ se vérifie en ligne par son numéro FC-… : l'assureur voit que le calcul n'a pas été retouché.",
      "A departure's sealed calculation sheet can be verified online by its FC-… number: the insurer sees the calculation has not been altered."), chapitre: "departs" },
  { texte: t("Cinq départs au moins avant de changer une hypothèse : en dessous, la rotation observée est montrée, pas proposée — deux démissions ne font pas une tendance.",
      "At least five departures before changing an assumption: below that, the observed turnover is shown, not proposed — two resignations do not make a trend."), chapitre: "departs" },
  { texte: t("L'offre au meilleur rendement n'est pas toujours la recommandée : une pénalité de transfert ou un préavis trop long la rend non conforme — c'est ce qui vous permettra de partir plus tard.",
      "The offer with the best return is not always the recommended one: a transfer penalty or an overly long notice period makes it non-compliant — and that is what will let you leave later."), chapitre: "cahier" },
  { texte: t("Votre accord d'entreprise peut préremplir votre régime : chaque taux proposé cite son passage du texte, et un passage introuvable est signalé.",
      "Your company agreement can prefill your plan: each proposed rate cites its passage in the text, and a passage that cannot be found is flagged."), chapitre: "regime" },
  { texte: t("La date d'évaluation est toujours une fin de mois : c'est votre date de clôture, celle du bilan.",
      "The valuation date is always a month end: it is your closing date, the balance-sheet date."), chapitre: "etude" },
  { texte: t("Une convention révisée ne remplace pas l'ancienne : une étude de 2023 garde le barème de 2023.",
      "A revised collective agreement does not replace the old one: a 2023 study keeps the 2023 scale."), chapitre: "conventions" },
  ];
}

/** La même liste, relue à chaque accès : pour qui l'importe comme une constante. */
export const ASTUCES: Astuce[] = listeVivante(astuces);

/** L'astuce du jour : la même toute la journée, une autre demain. */
export function astuceDuJour(jour = new Date()): number {
  const n = Math.floor(jour.getTime() / 86_400_000);
  return n % astuces().length;
}
