// La visite guidée : des bulles posées sur les vrais éléments de l'écran (attribut data-visite).
// Une étape dont l'élément n'est pas à l'écran est sautée : la visite ne pointe jamais dans le vide.

export interface EtapeVisite { cible: string; titre: string; texte: string }

export const VISITE_DOSSIER: EtapeVisite[] = [
  { cible: "parcours", titre: "Votre parcours", texte: "Cinq étapes, de votre personnel au cahier des charges. Une coche dit ce qui est fait ; l'étape suivante est mise en avant." },
  { cible: "prochaine", titre: "La prochaine étape", texte: "Ici, toujours la chose à faire maintenant, avec un bouton pour y aller." },
  { cible: "chiffres", titre: "Vos chiffres clés", texte: "Dette, charge, fonds, cotisation. Survolez le « ? » d'un chiffre pour sa définition ; dépliez « Comment on arrive à la cotisation » pour le détail au franc près." },
  { cible: "outils", titre: "Simuler et rémunération", texte: "Tester un barème avant de le décider, et lire les conditions de rémunération de votre conseiller." },
  { cible: "conseiller", titre: "Votre conseiller", texte: "La personne qui suit votre dossier, relit et émet vos études." },
  { cible: "guide", titre: "Le guide", texte: "Chapitres, leçons rapides, conventions et glossaire. Vous pouvez relancer cette visite depuis le guide." },
];

export const CLE_VISITE_FAITE = "courtage:visite-faite";
