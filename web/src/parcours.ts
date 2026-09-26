// Le parcours d'un dossier, à la manière de Policygenius : des étapes, ce qui est fait, ce qui vient.

export interface EtatDossier {
  fichiers: number;
  versionsAdoptees: number;
  versions: number;
  etudesEmises: number;
  etudesBrouillon: number;
  fiches: number;
}

export interface Etape {
  cle: "personnel" | "regime" | "etudes" | "financement" | "cahier";
  libelle: string;
  fait: boolean;
  suivant: boolean;
  aide: string;
}

export function etapes(e: EtatDossier): Etape[] {
  const brutes: Omit<Etape, "suivant">[] = [
    { cle: "personnel", libelle: "Personnel", fait: e.fichiers > 0,
      aide: "Déposez le fichier de votre personnel : matricules, dates, salaires. Aucun nom." },
    { cle: "regime", libelle: "Régime", fait: e.versionsAdoptees > 0,
      aide: e.versions > 0 ? "Une version attend votre adoption." :
        "Décrivez votre régime, ou restez sur votre convention collective." },
    { cle: "etudes", libelle: "Étude", fait: e.etudesEmises > 0,
      aide: e.etudesBrouillon > 0 ? "Un brouillon attend l'émission par votre conseiller." :
        "Lancez l'évaluation de votre engagement." },
    { cle: "financement", libelle: "Financement", fait: e.fiches > 0,
      aide: "Comparez l'assurance et la provision interne sous plusieurs scénarios." },
    { cle: "cahier", libelle: "Cahier des charges", fait: e.fiches > 0,
      aide: "Mettez les assureurs en concurrence sur une base commune." },
  ];
  // Le régime est facultatif : une étude émise sur la convention seule le rend « fait ».
  if (e.etudesEmises > 0) brutes[1].fait = true;
  const premier = brutes.findIndex((x) => !x.fait);
  return brutes.map((x, i) => ({ ...x, suivant: i === premier }));
}
