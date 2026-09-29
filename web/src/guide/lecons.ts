// Leçons rapides : deux minutes, quelques écrans, une question pour vérifier qu'on a compris.
// Le « pourquoi » de la bonne réponse compte plus que la réponse : il est toujours affiché.

import { langue, t, type Langue } from "../i18n";
import { listeVivante } from "./visite";

export interface Lecon {
  id: string;
  titre: string;
  duree: string;
  pour: string;                       // à qui elle s'adresse
  etapes: { titre: string; texte: string }[];
  quiz: { question: string; choix: string[]; bonne: number; pourquoi: string };
}

function construire(): Lecon[] {
  return [
  {
    id: "ifc-en-2-minutes", titre: t("L'IFC en deux minutes", "End-of-service benefits in two minutes"), duree: "2 min", pour: t("Tout le monde", "Everyone"),
    etapes: [
      { titre: t("Une dette qui grossit en silence", "A liability that grows quietly"), texte: t("Chaque année de service ajoute des droits à l'indemnité de départ en retraite. L'entreprise ne verse rien tant que personne ne part — mais elle doit déjà quelque chose.", "Each year of service adds entitlements to the retirement benefit. The company pays nothing as long as nobody leaves — but it already owes something.") },
      { titre: t("Un barème en mois de salaire", "A scale in months of salary"), texte: t("La convention collective dit combien de mois de salaire par année d'ancienneté : par exemple 45 % d'un mois pour chacune des cinq premières années dans le commerce au Cameroun depuis 2024.", "The collective agreement says how many months of salary per year of service: for example 45% of a month for each of the first five years in commerce in Cameroon since 2024.") },
      { titre: t("Pourquoi l'anticiper", "Why plan ahead"), texte: t("Trois départs la même année peuvent coûter plusieurs mois de trésorerie. Un fonds constitué à l'avance lisse la charge et rapporte des intérêts.", "Three departures in the same year can cost several months of cash. A fund built up in advance smooths the cost and earns interest.") },
    ],
    quiz: { question: t("Un salarié démissionne après 12 ans. Doit-on lui verser l'IFC ?", "An employee resigns after 12 years. Must they be paid the end-of-service benefit?"),
      choix: [t("Oui, toujours", "Yes, always"), t("Non : l'IFC est due au départ en retraite", "No: the benefit is due on retirement"), t("Seulement s'il est cadre", "Only if they are a manager")], bonne: 1,
      pourquoi: t("L'IFC est l'indemnité de départ EN RETRAITE. C'est pour cela que l'étude tient compte de la rotation du personnel : un salarié qui partira avant ne coûtera rien à ce titre.", "The IFC is the benefit paid ON RETIREMENT. That is why the study takes staff turnover into account: an employee who leaves before then will cost nothing on this account.") },
  },
  {
    id: "lire-les-chiffres", titre: t("Lire les quatre chiffres clés", "Reading the four key figures"), duree: "3 min", pour: t("DRH, direction financière", "HR directors, finance departments"),
    etapes: [
      { titre: t("La dette actuarielle", "The actuarial liability"), texte: t("Ce qui est déjà dû pour les années passées, ramené à aujourd'hui. C'est le chiffre du bilan.", "What is already owed for past years, brought back to today. It is the balance-sheet figure.") },
      { titre: t("La charge annuelle", "The annual cost"), texte: t("Ce que l'année qui vient ajoute. C'est le coût courant, à budgéter chaque année.", "What the coming year adds. It is the current cost, to be budgeted every year.") },
      { titre: t("Le fonds", "The fund"), texte: t("Ce qui est déjà placé chez l'assureur. Il se retranche.", "What is already invested with the insurer. It is deducted.") },
      { titre: t("La cotisation", "The contribution"), texte: t("Dette + charge − fonds = cotisation nette. On ajoute les frais de l'assureur (4 % par défaut) : c'est la cotisation à verser. Le tableau « Du passif à la cotisation » le montre au franc près.", "Liability + annual cost − fund = net contribution. Add the insurer's fees (4% by default): that is the contribution to pay. The “From liability to contribution” table shows it to the last franc.") },
    ],
    quiz: { question: t("Dette 110,7 M, charge 10,3 M, fonds 45,0 M, frais 4 %. Cotisation à verser ?", "Liability 110.7 M, annual cost 10.3 M, fund 45.0 M, fees 4%. Contribution to pay?"),
      choix: [t("76,0 M", "76.0 M"), t("79,1 M", "79.1 M"), t("121,0 M", "121.0 M")], bonne: 1,
      pourquoi: t("110,7 + 10,3 − 45,0 = 76,0 M de cotisation nette ; + 4 % de frais = 79,1 M. Les 3 M d'écart sont les frais de l'assureur.", "110.7 + 10.3 − 45.0 = 76.0 M net contribution; + 4% fees = 79.1 M. The 3 M difference is the insurer's fees.") },
  },
  {
    id: "regime-et-convention", titre: t("Régime ou convention : qui gagne ?", "Plan or collective agreement: which prevails?"), duree: "2 min", pour: t("DRH", "HR directors"),
    etapes: [
      { titre: t("Deux textes", "Two texts"), texte: t("La convention collective fixe le minimum de la branche. Votre régime (accord, usage, contrats) peut donner plus.", "The collective agreement sets the sector minimum. Your plan (agreement, custom, contracts) can give more.") },
      { titre: t("Le plus favorable, ancienneté par ancienneté", "The more favourable, length of service by length of service"), texte: t("Le calcul retient à chaque ancienneté le plus favorable des deux. Un régime plus généreux à 10 ans mais moins à 30 ans n'enlève rien à 30 ans : la convention s'applique.", "At each length of service, the calculation keeps the more favourable of the two. A plan that is more generous at 10 years but less so at 30 takes nothing away at 30: the collective agreement applies.") },
      { titre: t("L'entreprise signe", "The company signs"), texte: t("Vous pouvez adopter un régime sous la convention ; la plateforme le signale et le calcul protège vos salariés. Rien n'est refusé, tout est dit.", "You can adopt a plan below the collective agreement; the platform flags it and the calculation protects your employees. Nothing is refused, everything is stated.") },
    ],
    quiz: { question: t("Votre accord donne 0,40 mois par an ; la convention 0,45 les cinq premières années. Que retient l'étude pour 3 ans d'ancienneté ?", "Your agreement gives 0.40 months per year; the collective agreement 0.45 for the first five years. What does the study use for 3 years of service?"),
      choix: [t("1,20 mois", "1.20 months"), t("1,35 mois", "1.35 months"), t("Rien, le régime est refusé", "Nothing, the plan is refused")], bonne: 1,
      pourquoi: t("3 × 0,45 = 1,35 mois, plus favorable que 3 × 0,40 = 1,20 : le plancher de la convention s'applique.", "3 × 0.45 = 1.35 months, more favourable than 3 × 0.40 = 1.20: the collective agreement's floor applies.") },
  },
  {
    id: "choisir-un-assureur", titre: t("Comparer deux offres d'assurance", "Comparing two insurance offers"), duree: "3 min", pour: t("Direction financière", "Finance departments"),
    etapes: [
      { titre: t("Le taux garanti ne suffit pas", "The guaranteed rate is not enough"), texte: t("Un taux garanti élevé avec 4 % de frais sur chaque versement peut coûter plus qu'un taux plus bas sans frais. Il faut projeter.", "A high guaranteed rate with 4% fees on every payment can cost more than a lower rate with no fees. You have to project.") },
      { titre: t("Trois scénarios", "Three scenarios"), texte: t("La plateforme projette chaque offre sous un rendement prudent, central et favorable. Une offre qui ne gagne que dans le scénario favorable est un pari.", "The platform projects each offer under a prudent, central and favourable return. An offer that only wins in the favourable scenario is a gamble.") },
      { titre: t("Le découvert", "The shortfall"), texte: t("Regardez les années où le fonds ne suffit pas à payer les départs : c'est là que l'entreprise remet de l'argent en urgence.", "Look at the years when the fund is not enough to pay the departures: that is when the company has to put money in urgently.") },
      { titre: t("La porte de sortie", "The way out"), texte: t("Préavis et pénalité de transfert : une offre qui vous retient coûte plus cher le jour où vous voulez partir.", "Notice period and transfer penalty: an offer that locks you in costs more on the day you want to leave.") },
    ],
    quiz: { question: t("Quel critère compare le mieux deux offres sur dix ans ?", "Which criterion best compares two offers over ten years?"),
      choix: [t("Le taux garanti", "The guaranteed rate"), t("Le coût net actualisé, scénario central", "The net present cost, central scenario"), t("Les frais sur encours seuls", "The fees on assets alone")], bonne: 1,
      pourquoi: t("Le coût net actualisé additionne tout — versements, frais, rendement — et retranche le fonds restant. C'est le seul chiffre qui résume une offre entière.", "The net present cost adds everything up — payments, fees, return — and deducts the remaining fund. It is the only figure that sums up a whole offer.") },
  },
  {
    id: "donnees-personnelles", titre: t("Pourquoi nous ne demandons aucun nom", "Why we ask for no names"), duree: "1 min", pour: t("Tout le monde", "Everyone"),
    etapes: [
      { titre: t("Le calcul n'en a pas besoin", "The calculation does not need them"), texte: t("Une date de naissance, une date d'embauche, un salaire : c'est tout ce que l'actuaire utilise.", "A date of birth, a hiring date, a salary: that is all the actuary uses.") },
      { titre: t("Le moins de données possible", "As little data as possible"), texte: t("Une donnée qu'on n'a pas ne peut pas fuir. Le cahier des charges regroupe même les salariés par trois au moins.", "Data we do not have cannot leak. The tender specifications even group employees in threes at least.") },
      { titre: t("L'identité, au bon moment", "Identity, at the right time"), texte: t("Le nom d'un salarié n'est utile que le jour où son indemnité est versée : c'est là, et seulement là, qu'il sera demandé.", "An employee's name is only useful on the day their benefit is paid: that is when, and only when, it will be asked for.") },
    ],
    quiz: { question: t("Votre fichier contient une colonne de noms. Que se passe-t-il ?", "Your file contains a names column. What happens?"),
      choix: [t("Le dépôt est refusé", "The upload is refused"), t("La colonne est ignorée, ni lue ni gardée", "The column is ignored, neither read nor kept"), t("Les noms sont chiffrés et gardés", "The names are encrypted and kept")], bonne: 1,
      pourquoi: t("La colonne est ignorée : vous n'avez pas à retoucher votre fichier, et la plateforme ne garde rien qu'elle n'utilise.", "The column is ignored: you do not have to edit your file, and the platform keeps nothing it does not use.") },
  },
];
}

// Une liste par langue, construite une fois : une leçon garde son identité d'une lecture à l'autre
// (`LECONS.indexOf(l)` retrouve la leçon que `LECONS.find` a rendue).
const parLangue: Partial<Record<Langue, Lecon[]>> = {};

/** Les leçons, dans la langue du moment. */
export function lecons(): Lecon[] {
  return (parLangue[langue()] ??= construire());
}

/** La même liste, relue à chaque accès : pour qui l'importe comme une constante. */
export const LECONS: Lecon[] = listeVivante(lecons);
