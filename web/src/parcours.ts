// Le parcours d'un dossier, à la manière de Policygenius : des étapes, ce qui est fait, ce qui vient.

import { t } from "./i18n";

export interface EtatDossier {
  fichiers: number;
  versionsAdoptees: number;
  versions: number;
  etudesEmises: number;
  etudesBrouillon: number;
  fiches: number;
  /** Où en est l'accompagnement : rien demandé, demandé, un mandat proposé à signer, signé. `null` : inconnu. */
  mandat?: "aucun" | "demande" | "propose" | "signe" | null;
}

export interface Etape {
  cle: "accompagnement" | "personnel" | "regime" | "etudes" | "financement" | "cahier";
  libelle: string;
  fait: boolean;
  suivant: boolean;
  aide: string;
}

export function etapes(e: EtatDossier): Etape[] {
  const brutes: Omit<Etape, "suivant">[] = [
    // L'accompagnement d'abord : c'est ce que l'entreprise vient chercher. « Fait » dès qu'il est demandé, sauf quand
    // un mandat attend sa signature.
    { cle: "accompagnement", libelle: t("Accompagnement", "Support"),
      fait: e.mandat == null || e.mandat === "demande" || e.mandat === "signe",
      aide: e.mandat === "propose" ? t("Un mandat de courtage vous attend : lisez-le, puis signez-le.",
                                       "A brokerage mandate is waiting for you: read it, then sign it.")
        : t("Dites ce que vous attendez de votre courtier : il vous propose ensuite un mandat.",
            "Say what you expect from your broker: they then propose a mandate.") },
    { cle: "personnel", libelle: t("Personnel", "Workforce"), fait: e.fichiers > 0,
      aide: t("Déposez le fichier de votre personnel : matricules, dates, salaires. Aucun nom.",
        "Upload your workforce file: employee numbers, dates, salaries. No names.") },
    { cle: "regime", libelle: t("Régime", "Plan"), fait: e.versionsAdoptees > 0,
      aide: e.versions > 0 ? t("Une version attend votre adoption.", "A version is awaiting your adoption.") :
        t("Décrivez votre régime, ou restez sur votre convention collective.",
          "Describe your plan, or stay on your collective agreement.") },
    { cle: "etudes", libelle: t("Étude", "Study"), fait: e.etudesEmises > 0,
      aide: e.etudesBrouillon > 0 ? t("Un brouillon attend l'émission par votre conseiller.",
                                      "A draft is waiting to be issued by your adviser.") :
        t("Lancez l'évaluation de votre engagement.", "Start the valuation of your liability.") },
    { cle: "financement", libelle: t("Financement", "Funding"), fait: e.fiches > 0,
      aide: t("Comparez l'assurance et la provision interne sous plusieurs scénarios.",
        "Compare insurance and an internal provision under several scenarios.") },
    { cle: "cahier", libelle: t("Cahier des charges", "Specifications"), fait: e.fiches > 0,
      aide: t("Mettez les assureurs en concurrence sur une base commune.",
        "Put insurers in competition on a common basis.") },
  ];
  // Le régime est facultatif : une étude émise sur la convention seule le rend « fait ».
  if (e.etudesEmises > 0) brutes[2].fait = true;
  const premier = brutes.findIndex((x) => !x.fait);
  return brutes.map((x, i) => ({ ...x, suivant: i === premier }));
}
