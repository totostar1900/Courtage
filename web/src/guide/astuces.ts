// « Le saviez-vous ? » : une phrase vraie et utile, avec le chapitre qui la développe.

export interface Astuce { texte: string; chapitre?: string; lecon?: string }

export const ASTUCES: Astuce[] = [
  { texte: "Au Cameroun, la convention du commerce révisée en janvier 2024 a relevé le barème d'IFC : 45 % d'un mois par année au lieu de 40 % pour les cinq premières années, 80 % au lieu de 75 % au-delà de vingt ans.", chapitre: "conventions" },
  { texte: "Un point de taux d'actualisation en moins augmente souvent la dette de l'ordre de 10 % : l'étude montre toujours cette sensibilité.", chapitre: "comprendre" },
  { texte: "Un salarié qui quitte l'entreprise avant la retraite ne coûte pas d'IFC : c'est pourquoi la rotation du personnel réduit l'engagement.", lecon: "ifc-en-2-minutes" },
  { texte: "Votre fichier peut garder sa colonne de noms : elle est ignorée, ni lue ni conservée.", lecon: "donnees-personnelles" },
  { texte: "Le fonds placé chez l'assureur vous appartient : il se retranche de la cotisation, et il vous suit si vous changez d'assureur selon les conditions de transfert.", chapitre: "financer" },
  { texte: "La cotisation à verser comprend les frais de l'assureur : 4 % par défaut. Le tableau « Du passif à la cotisation » les montre ligne à ligne.", lecon: "lire-les-chiffres" },
  { texte: "Un rapport émis se vérifie en ligne par n'importe qui, sans compte : il suffit de son numéro RL-….", chapitre: "verifier" },
  { texte: "Un régime peut différer par catégorie : les cadres peuvent avoir un barème plus généreux que le reste du personnel.", chapitre: "regime" },
  { texte: "La provision interne n'a aucun frais, mais aucun rendement : trois départs la même année se paient sur la trésorerie du moment.", chapitre: "financer" },
  { texte: "Dans le cahier des charges, aucune ligne ne décrit moins de trois salariés : un assureur ne peut reconnaître personne.", chapitre: "cahier" },
  { texte: "En courtage, nous portons vos prestations auprès de l'assureur ; en comparaison, vous traitez directement avec lui. L'écran « Contrat » dit lequel s'applique.", chapitre: "contrat" },
  { texte: "Un départ en démission ne coûte pas d'IFC, mais l'enregistrer (sans nom) mesure la rotation réelle de votre personnel — et une rotation mesurée vaut mieux qu'une rotation supposée.", chapitre: "departs" },
  { texte: "En courtage, l'identité d'un bénéficiaire ne sert qu'à son paiement : elle est effacée douze mois après, et le dossier scellé se vérifie toujours par son numéro.", chapitre: "departs" },
  { texte: "La date d'évaluation est toujours une fin de mois : c'est votre date de clôture, celle du bilan.", chapitre: "etude" },
  { texte: "Une convention révisée ne remplace pas l'ancienne : une étude de 2023 garde le barème de 2023.", chapitre: "conventions" },
];

/** L'astuce du jour : la même toute la journée, une autre demain. */
export function astuceDuJour(jour = new Date()): number {
  const n = Math.floor(jour.getTime() / 86_400_000);
  return n % ASTUCES.length;
}
