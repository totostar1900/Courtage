// Leçons rapides : deux minutes, quelques écrans, une question pour vérifier qu'on a compris.
// Le « pourquoi » de la bonne réponse compte plus que la réponse : il est toujours affiché.

export interface Lecon {
  id: string;
  titre: string;
  duree: string;
  pour: string;                       // à qui elle s'adresse
  etapes: { titre: string; texte: string }[];
  quiz: { question: string; choix: string[]; bonne: number; pourquoi: string };
}

export const LECONS: Lecon[] = [
  {
    id: "ifc-en-2-minutes", titre: "L'IFC en deux minutes", duree: "2 min", pour: "Tout le monde",
    etapes: [
      { titre: "Une dette qui grossit en silence", texte: "Chaque année de service ajoute des droits à l'indemnité de départ en retraite. L'entreprise ne verse rien tant que personne ne part — mais elle doit déjà quelque chose." },
      { titre: "Un barème en mois de salaire", texte: "La convention collective dit combien de mois de salaire par année d'ancienneté : par exemple 45 % d'un mois pour chacune des cinq premières années dans le commerce au Cameroun depuis 2024." },
      { titre: "Pourquoi l'anticiper", texte: "Trois départs la même année peuvent coûter plusieurs mois de trésorerie. Un fonds constitué à l'avance lisse la charge et rapporte des intérêts." },
    ],
    quiz: { question: "Un salarié démissionne après 12 ans. Doit-on lui verser l'IFC ?",
      choix: ["Oui, toujours", "Non : l'IFC est due au départ en retraite", "Seulement s'il est cadre"], bonne: 1,
      pourquoi: "L'IFC est l'indemnité de départ EN RETRAITE. C'est pour cela que l'étude tient compte de la rotation du personnel : un salarié qui partira avant ne coûtera rien à ce titre." },
  },
  {
    id: "lire-les-chiffres", titre: "Lire les quatre chiffres clés", duree: "3 min", pour: "DRH, direction financière",
    etapes: [
      { titre: "La dette actuarielle", texte: "Ce qui est déjà dû pour les années passées, ramené à aujourd'hui. C'est le chiffre du bilan." },
      { titre: "La charge annuelle", texte: "Ce que l'année qui vient ajoute. C'est le coût courant, à budgéter chaque année." },
      { titre: "Le fonds", texte: "Ce qui est déjà placé chez l'assureur. Il se retranche." },
      { titre: "La cotisation", texte: "Dette + charge − fonds = cotisation nette. On ajoute les frais de l'assureur (4 % par défaut) : c'est la cotisation à verser. Le tableau « Du passif à la cotisation » le montre au franc près." },
    ],
    quiz: { question: "Dette 110,7 M, charge 10,3 M, fonds 45,0 M, frais 4 %. Cotisation à verser ?",
      choix: ["76,0 M", "79,1 M", "121,0 M"], bonne: 1,
      pourquoi: "110,7 + 10,3 − 45,0 = 76,0 M de cotisation nette ; + 4 % de frais = 79,1 M. Les 3 M d'écart sont les frais de l'assureur." },
  },
  {
    id: "regime-et-convention", titre: "Régime ou convention : qui gagne ?", duree: "2 min", pour: "DRH",
    etapes: [
      { titre: "Deux textes", texte: "La convention collective fixe le minimum de la branche. Votre régime (accord, usage, contrats) peut donner plus." },
      { titre: "Le plus favorable, ancienneté par ancienneté", texte: "Le calcul retient à chaque ancienneté le plus favorable des deux. Un régime plus généreux à 10 ans mais moins à 30 ans n'enlève rien à 30 ans : la convention s'applique." },
      { titre: "L'entreprise signe", texte: "Vous pouvez adopter un régime sous la convention ; la plateforme le signale et le calcul protège vos salariés. Rien n'est refusé, tout est dit." },
    ],
    quiz: { question: "Votre accord donne 0,40 mois par an ; la convention 0,45 les cinq premières années. Que retient l'étude pour 3 ans d'ancienneté ?",
      choix: ["1,20 mois", "1,35 mois", "Rien, le régime est refusé"], bonne: 1,
      pourquoi: "3 × 0,45 = 1,35 mois, plus favorable que 3 × 0,40 = 1,20 : le plancher de la convention s'applique." },
  },
  {
    id: "choisir-un-assureur", titre: "Comparer deux offres d'assurance", duree: "3 min", pour: "Direction financière",
    etapes: [
      { titre: "Le taux garanti ne suffit pas", texte: "Un taux garanti élevé avec 4 % de frais sur chaque versement peut coûter plus qu'un taux plus bas sans frais. Il faut projeter." },
      { titre: "Trois scénarios", texte: "La plateforme projette chaque offre sous un rendement prudent, central et favorable. Une offre qui ne gagne que dans le scénario favorable est un pari." },
      { titre: "Le découvert", texte: "Regardez les années où le fonds ne suffit pas à payer les départs : c'est là que l'entreprise remet de l'argent en urgence." },
      { titre: "La porte de sortie", texte: "Préavis et pénalité de transfert : une offre qui vous retient coûte plus cher le jour où vous voulez partir." },
    ],
    quiz: { question: "Quel critère compare le mieux deux offres sur dix ans ?",
      choix: ["Le taux garanti", "Le coût net actualisé, scénario central", "Les frais sur encours seuls"], bonne: 1,
      pourquoi: "Le coût net actualisé additionne tout — versements, frais, rendement — et retranche le fonds restant. C'est le seul chiffre qui résume une offre entière." },
  },
  {
    id: "donnees-personnelles", titre: "Pourquoi nous ne demandons aucun nom", duree: "1 min", pour: "Tout le monde",
    etapes: [
      { titre: "Le calcul n'en a pas besoin", texte: "Une date de naissance, une date d'embauche, un salaire : c'est tout ce que l'actuaire utilise." },
      { titre: "Le moins de données possible", texte: "Une donnée qu'on n'a pas ne peut pas fuir. Le cahier des charges regroupe même les salariés par trois au moins." },
      { titre: "L'identité, au bon moment", texte: "Le nom d'un salarié n'est utile que le jour où son indemnité est versée : c'est là, et seulement là, qu'il sera demandé." },
    ],
    quiz: { question: "Votre fichier contient une colonne de noms. Que se passe-t-il ?",
      choix: ["Le dépôt est refusé", "La colonne est ignorée, ni lue ni gardée", "Les noms sont chiffrés et gardés"], bonne: 1,
      pourquoi: "La colonne est ignorée : vous n'avez pas à retoucher votre fichier, et la plateforme ne garde rien qu'elle n'utilise." },
  },
];
