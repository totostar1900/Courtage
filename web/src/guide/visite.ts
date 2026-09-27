// La visite guidée : des bulles posées sur les vrais éléments de l'écran (attribut data-visite).
// Une étape dont l'élément n'est pas à l'écran est sautée : la visite ne pointe jamais dans le vide.

export interface EtapeVisite { cible: string; titre: string; texte: string }

export const VISITE_DOSSIER: EtapeVisite[] = [
  { cible: "parcours", titre: "Votre parcours", texte: "Cinq étapes, de votre personnel au cahier des charges. Chaque étape a son icône ; un point signale l'étape suivante." },
  { cible: "prochaine", titre: "La prochaine étape", texte: "Ici, toujours la chose à faire maintenant, avec un bouton pour y aller." },
  { cible: "chiffres", titre: "Vos chiffres clés", texte: "Dette, charge, fonds, cotisation. Survolez le « ? » d'un chiffre pour sa définition ; dépliez « Comment on arrive à la cotisation » pour le détail au franc près." },
  { cible: "outils", titre: "Simuler, contrat, départs", texte: "Tester un barème avant de le décider, suivre les départs, et voir votre service — courtage ou comparaison — qui décide qui traite une prestation." },
  { cible: "conseiller", titre: "Votre conseiller", texte: "La personne qui suit votre dossier, relit et émet vos études." },
  { cible: "guide", titre: "Le guide", texte: "Chapitres, leçons rapides, conventions et glossaire. Vous pouvez relancer cette visite depuis le guide." },
];

export const CLE_VISITE_FAITE = "courtage:visite-faite";
