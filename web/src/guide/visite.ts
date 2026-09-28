// La visite guidée : des bulles posées sur les vrais éléments de l'écran (attribut data-visite).
// Une étape dont l'élément n'est pas à l'écran est sautée : la visite ne pointe jamais dans le vide.

import { t } from "../i18n";

export interface EtapeVisite { cible: string; titre: string; texte: string }

/** Une liste relue à chaque accès : exportée comme une constante, elle suit pourtant la langue du moment. */
export function listeVivante<T>(lire: () => T[]): T[] {
  return new Proxy([] as T[], {
    get: (_, p) => Reflect.get(lire(), p),
    has: (_, p) => Reflect.has(lire(), p),
    ownKeys: () => Reflect.ownKeys(lire()),
    getOwnPropertyDescriptor: (_, p) => {
      const d = Reflect.getOwnPropertyDescriptor(lire(), p);
      return d && p !== "length" ? { ...d, configurable: true } : d;
    },
  });
}

/** Les étapes de la visite du dossier, dans la langue du moment. */
export function visiteDossier(): EtapeVisite[] {
  return [
    { cible: "parcours", titre: t("Votre parcours", "Your journey"),
      texte: t("Cinq étapes, de votre personnel au cahier des charges. Chaque étape a son icône ; un point signale l'étape suivante.",
        "Five steps, from your workforce to the specifications. Each step has its icon; a dot marks the next step.") },
    { cible: "prochaine", titre: t("La prochaine étape", "The next step"),
      texte: t("Ici, toujours la chose à faire maintenant, avec un bouton pour y aller.",
        "Here, always the thing to do now, with a button to get there.") },
    { cible: "chiffres", titre: t("Vos chiffres clés", "Your key figures"),
      texte: t("Dette, charge, fonds, cotisation. Survolez le « ? » d'un chiffre pour sa définition ; dépliez « Comment on arrive à la cotisation » pour le détail au franc près.",
        "Liability, cost, fund, contribution. Hover over a figure's “?” for its definition; expand “How the contribution is reached” for the detail to the last franc.") },
    { cible: "outils", titre: t("Simuler, contrat, départs", "Simulate, contract, departures"),
      texte: t("Tester un barème avant de le décider, suivre les départs, et voir votre contrat de courtage, qui décide qui traite une prestation.",
        "Test a scale before deciding on it, track departures, and see your brokerage contract, which decides who handles a benefit payment.") },
    { cible: "conseiller", titre: t("Votre conseiller", "Your adviser"),
      texte: t("La personne qui suit votre dossier, relit et émet vos études.",
        "The person who follows your file, reviews and issues your studies.") },
    { cible: "guide", titre: t("Le guide", "The guide"),
      texte: t("Chapitres, leçons rapides, conventions et glossaire. Vous pouvez relancer cette visite depuis le guide.",
        "Chapters, quick lessons, collective agreements and glossary. You can restart this tour from the guide.") },
  ];
}

/** La même liste, relue à chaque accès : pour qui l'importe comme une constante. */
export const VISITE_DOSSIER: EtapeVisite[] = listeVivante(visiteDossier);

export const CLE_VISITE_FAITE = "courtage:visite-faite";
