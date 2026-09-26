// Le guide : un texte, lu par l'écran Guide, cité par les infobulles, parcouru par la visite.
// Un chapitre dit ce qu'on fait, pourquoi, et ce que la plateforme fait pour vous — dans cet ordre.

import type { CleTerme } from "./glossaire";

export interface Chapitre {
  id: string;
  groupe: "Commencer" | "Le parcours" | "Comprendre" | "Référence";
  titre: string;
  resume: string;
  sections: { titre: string; texte: string[] }[];
  ecran?: string;           // l'écran du dossier dont parle le chapitre (chemin relatif au dossier)
  termes?: CleTerme[];
}

export const CHAPITRES: Chapitre[] = [
  {
    id: "bienvenue", groupe: "Commencer", titre: "Ce que fait la plateforme",
    resume: "Votre engagement d'IFC, calculé avant d'être vendu, puis mis en concurrence.",
    sections: [
      { titre: "En une phrase", texte: [
        "Vous déposez l'état de votre personnel, nous calculons ce que vous devez à vos salariés pour leur départ en retraite, et nous mettons les assureurs en concurrence sur ce chiffre.",
        "Vous voyez le calcul AVANT que quiconque vous vende quoi que ce soit : c'est l'inverse de la pratique habituelle, où l'étude vient de l'assureur qui veut le contrat." ] },
      { titre: "Trois principes", texte: [
        "Aucun nom de salarié. Le calcul n'a besoin que d'un matricule, de deux dates et d'un salaire. L'identité d'un salarié ne sert qu'au moment où son indemnité est versée.",
        "Votre entreprise décide. Elle adopte son régime, même s'il est en dessous de la convention : la plateforme le signale clairement, elle ne le refuse pas.",
        "Tout se vérifie. Un rapport émis est scellé ; n'importe qui peut vérifier en ligne qu'il n'a pas été modifié." ] },
      { titre: "Qui fait quoi", texte: [
        "L'entreprise (la DRH) dépose le personnel, décrit et adopte son régime.",
        "Le conseiller relit, émet l'étude et le cahier des charges, fixe sa rémunération de façon transparente.",
        "Les assureurs répondent au cahier des charges ; vous comparez sur une base commune." ] },
    ],
    termes: ["ifc", "convention", "regime"],
  },
  {
    id: "connexion", groupe: "Commencer", titre: "Se connecter",
    resume: "Votre numéro de téléphone, un code reçu par message. Pas de mot de passe.",
    sections: [
      { titre: "Le code", texte: [
        "Saisissez votre numéro : un code à six chiffres arrive par WhatsApp ou SMS. Il vaut dix minutes et ne sert qu'une fois.",
        "Ne le communiquez à personne, pas même à votre conseiller : personne de la plateforme ne vous le demandera jamais.",
        "Après cinq erreurs, le code ne marche plus : demandez-en un nouveau (trois par quart d'heure au plus)." ] },
      { titre: "Je ne reçois rien", texte: [
        "Votre numéro doit avoir été inscrit par votre conseiller. Pour des raisons de confidentialité, la plateforme répond de la même façon qu'il soit inscrit ou non.",
        "Vérifiez l'indicatif : un numéro camerounais peut se saisir sans +237." ] },
    ],
  },
  {
    id: "personnel", groupe: "Le parcours", titre: "1. Déposer le personnel", ecran: "personnel",
    resume: "Un tableur : matricule, date de naissance, date d'embauche, salaire. Rien d'autre.",
    sections: [
      { titre: "Le fichier", texte: [
        "Un fichier Excel (.xlsx) ou CSV, une ligne par salarié. Les colonnes sont reconnues en français ou en anglais, dans n'importe quel ordre.",
        "Une colonne « Catégorie » (Cadre, Employé…) est utile si votre régime diffère selon les catégories.",
        "Une colonne de noms est ignorée : elle n'est ni lue ni conservée." ] },
      { titre: "Les contrôles", texte: [
        "Bloquant : un champ manquant, un salaire nul, un âge impossible, un matricule en double. L'étude ne sortira pas tant qu'il reste un point bloquant.",
        "Avertissement : beaucoup de salariés nés un 1er janvier (dates estimées ?), un salarié au-delà de l'âge de retraite, un salarié qui pèse plus de 20 % de l'engagement.",
        "Cliquez sur un fichier pour voir ses contrôles ; la croix referme le détail." ] },
    ],
    termes: ["anciennete"],
  },
  {
    id: "regime", groupe: "Le parcours", titre: "2. Décrire son régime", ecran: "regime",
    resume: "Ce que vous versez vraiment, catégorie par catégorie, comparé à la convention.",
    sections: [
      { titre: "Faut-il un régime ?", texte: [
        "Non : sans régime, l'étude s'appuie sur la convention collective de votre branche. Décrivez un régime si vous versez plus (accord d'entreprise, usage, contrats).",
        "Un régime a des versions : une nouvelle version s'ajoute, l'ancienne reste, et une étude dit toujours sur quelle version elle repose." ] },
      { titre: "L'analyse", texte: [
        "« Analyser » lit votre régime contre la convention : où il est en dessous du plancher, ce qu'il coûte de plus, les pièges (une tranche mal bornée, un plafond qui annule un avantage).",
        "Avec un fichier du personnel, l'analyse chiffre ce que coûte chaque écart sur VOS salariés." ] },
      { titre: "L'adoption", texte: [
        "C'est l'entreprise qui adopte, jamais le conseiller. Un régime sous la convention peut être adopté en le reconnaissant : vos salariés gardent droit au plancher, et le calcul le retient." ] },
    ],
    termes: ["regime", "plancher", "convention"],
  },
  {
    id: "simulation", groupe: "Le parcours", titre: "Simuler", ecran: "simulation",
    resume: "Comparer plusieurs versions de régime, ou tester une idée, avant de décider.",
    sections: [
      { titre: "Comparer", texte: [
        "Cochez les versions à comparer, ou « Tester une idée de barème » : chaque variante est calculée sur le même personnel à la même date.",
        "Chaque carte dit la dette, ce qu'elle ajoute à la convention, la charge, et qui en profite : si l'ajout va surtout aux mieux payés, la carte le signale.",
        "Les résultats s'ouvrent dans un volet que la croix referme ; vos réglages restent." ] },
    ],
  },
  {
    id: "etude", groupe: "Le parcours", titre: "3. L'étude et le rapport", ecran: "etudes",
    resume: "L'évaluation à une date de clôture, puis un rapport scellé.",
    sections: [
      { titre: "Lancer une étude", texte: [
        "Choisissez le fichier, la date d'évaluation (une fin de mois, votre clôture) et le fonds déjà placé. L'étude est d'abord un brouillon, modifiable.",
        "Les hypothèses (taux d'actualisation, croissance des salaires, rotation, âge de retraite) ont des valeurs par défaut ; toute modification est justifiée et figure au rapport." ] },
      { titre: "Lire les quatre chiffres", texte: [
        "Dette actuarielle + charge annuelle − fonds constitué = cotisation nette. Cotisation nette + frais de l'assureur = cotisation à verser.",
        "Le tableau « Du passif à la cotisation » montre chaque ligne au franc près : les quatre cartes se réconcilient toujours." ] },
      { titre: "L'émission", texte: [
        "Le conseiller émet l'étude quand elle est complète. Elle est alors figée, et son rapport PDF est scellé et numéroté (RL-…)." ] },
    ],
    termes: ["dette", "charge", "fonds", "cotisation_nette", "frais_cotisation", "cotisation", "emission"],
  },
  {
    id: "financer", groupe: "Le parcours", titre: "4. Financer l'engagement", ecran: "financement",
    resume: "Assurance ou provision interne, sous plusieurs scénarios de rendement.",
    sections: [
      { titre: "Comparer les offres", texte: [
        "Saisissez les conditions de chaque offre : taux garanti, participation aux bénéfices, frais sur cotisations et sur encours. La provision interne est toujours ajoutée pour comparaison.",
        "Chaque offre est projetée sur l'horizon choisi, sous trois scénarios de rendement : prudent (3,5 %), central (5 %) et favorable (6,5 %). La moins chère sur le scénario central est marquée.",
        "Regardez aussi les « années sans fonds suffisant » : une offre moins chère qui laisse le fonds à découvert l'année d'un gros départ n'est pas la meilleure." ] },
    ],
    termes: ["taux_garanti", "participation", "cout_net", "provision_interne", "frais_cotisation"],
  },
  {
    id: "cahier", groupe: "Le parcours", titre: "5. Le cahier des charges", ecran: "cahier",
    resume: "Mettre les assureurs en concurrence, sans jamais dévoiler un salarié.",
    sections: [
      { titre: "Ce qu'il contient", texte: [
        "Votre engagement (tiré d'une étude émise), votre régime, et vos exigences minimales : taux garanti, participation, frais maximum, conditions de transfert, délai de paiement.",
        "Le personnel y est décrit par groupes d'au moins trois salariés, les départs par périodes de cinq ans : personne n'est reconnaissable." ] },
      { titre: "Changer d'assureur", texte: [
        "Les conditions de transfert (préavis, pénalité) font partie des exigences : c'est ce qui vous permettra de changer d'assureur plus tard sans perdre votre fonds." ] },
    ],
    termes: ["cahier", "anonymat"],
  },
  {
    id: "contrat", groupe: "Le parcours", titre: "Courtage ou comparaison", ecran: "contrat",
    resume: "Deux services ; le vôtre décide qui s'occupe d'une prestation quand un salarié part.",
    sections: [
      { titre: "Deux services", texte: [
        "En courtage, la plateforme est votre courtier : vous l'avez mandatée, elle place le contrat, puis porte vos prestations auprès de l'assureur.",
        "En comparaison, elle a éclairé votre choix ; vous avez signé directement avec l'assureur et vous traitez avec lui.",
        "Le service se lit sur l'écran « Contrat » : il est daté, et un changement de service prend effet à sa date sans effacer l'ancien." ] },
      { titre: "Quand un salarié part", texte: [
        "En courtage : vous déclarez le départ, nous montons le dossier, le transmettons et suivons le paiement. Pour ce dossier seulement, nous recueillons l'identité du bénéficiaire.",
        "En comparaison : vous vous adressez à votre assureur ; nous vous disons à qui, avec quelles pièces, et le montant dû. Nous ne demandons jamais d'identité.",
        "Dans les deux cas, vous pouvez enregistrer le départ sans nom, pour que vos rapports tiennent compte de l'expérience réelle." ] },
      { titre: "Sans contrat enregistré", texte: [
        "Vous êtes en comparaison : la plateforme ne suppose jamais un mandat qu'elle n'a pas. Une commission prévue sans mandat est signalée à votre conseiller." ] },
    ],
    termes: ["courtage", "comparaison", "mandat"],
  },
  {
    id: "departs", groupe: "Le parcours", titre: "Les départs et l'historique", ecran: "departs",
    resume: "Enregistrer chaque départ par matricule ; la plateforme recalcule ce qui était dû.",
    sections: [
      { titre: "Déclarer un départ", texte: [
        "Matricule, motif, dates d'embauche et de départ, salaire mensuel de référence : « Calculer le dû » montre ce que la règle en vigueur ce jour-là accordait, et d'où vient le chiffre (votre régime, ou la convention).",
        "Vous déclarez ce qui a été versé. Moins que le dû est signalé — le salarié y avait droit ; plus est permis — l'entreprise est souveraine.",
        "Un départ hors retraite (démission, licenciement, décès) ne coûte pas d'IFC, mais il mesure la rotation réelle de votre personnel." ] },
      { titre: "Reprendre l'historique", texte: [
        "Un tableur des départs des cinq dernières années, avec ce qui a été versé et ce que le fonds a payé. La plateforme lit le fichier, calcule chaque dû et montre tout avant d'enregistrer.",
        "Un seul point bloquant (une date illisible, un motif inconnu, un départ déjà enregistré) et rien n'est enregistré : on corrige le fichier et on recommence.",
        "Une colonne de noms est ignorée, comme dans le fichier du personnel." ] },
      { titre: "Corriger sans effacer", texte: [
        "Une ligne ne se modifie pas : « Corriger » ajoute une ligne qui remplace la précédente et dit pourquoi ; « Annuler » aussi. L'historique reste lisible." ] },
      { titre: "La prise en charge, en courtage", texte: [
        "Sur un départ en retraite, « Demander la prise en charge » ouvre un dossier : le montant demandé au fonds, l'identité du bénéficiaire et son moyen de paiement, puis les pièces (certificat de travail, attestation de départ…).",
        "Votre conseiller le vérifie — ou vous dit ce qui manque —, le scelle (numéro PC-…) et l'envoie à l'assureur. Il note sa réponse : payé, et le paiement s'inscrit sur le départ ; ou refusé, avec le motif, et le dossier peut repartir.",
        "Passé le délai de paiement exigé au cahier des charges (30 jours sinon), le retard de l'assureur est signalé.",
        "L'identité et les pièces sont effacées douze mois après le paiement. Le numéro du dossier se vérifie toujours : son sceau public ne porte aucune donnée personnelle.",
        "En comparaison, il n'y a pas de dossier ici : la prise en charge se demande directement à votre assureur." ] },
      { titre: "La demande à l'assureur, en comparaison", texte: [
        "Sur un départ en retraite, « Préparer la demande à l'assureur » dit à qui s'adresser (l'assureur et la police de votre contrat), le montant à demander — le versé, s'il est sous le dû — et le délai de paiement à attendre.",
        "La liste des pièces que les assureurs demandent d'ordinaire se coche au fil de la préparation ; elle vous aide et ne s'enregistre pas.",
        "La fiche de calcul de la plateforme est un PDF scellé (numéro FC-…), sans aucune donnée personnelle : joignez-la, l'assureur vérifie en ligne qu'elle n'a pas été retouchée.",
        "Une fois payé, déclarez le montant et la date : sans nom, cela suffit pour que vos rapports tiennent compte du départ." ] },
    ],
    termes: ["turnover", "fonds", "prise_en_charge", "courtage", "comparaison"],
  },
  {
    id: "comprendre", groupe: "Comprendre", titre: "Comment se calcule l'engagement",
    resume: "La méthode prospective, pas à pas, sur un salarié.",
    sections: [
      { titre: "Pour chaque salarié", texte: [
        "1. L'IFC à la retraite : le salaire projeté à la retraite × les mois dus pour l'ancienneté totale qu'il aura alors.",
        "2. Les chances qu'il la touche : être en vie (table CIMA) et encore dans l'entreprise (rotation du personnel).",
        "3. Ramener à aujourd'hui avec le taux d'actualisation : c'est la VAPF.",
        "4. La dette est la part de la VAPF déjà acquise : VAPF × ancienneté actuelle ÷ ancienneté totale. La charge est une année de plus : VAPF ÷ ancienneté totale." ] },
      { titre: "Ce qui fait bouger le chiffre", texte: [
        "Le taux d'actualisation, d'abord : l'étude montre ce que devient la dette avec un point de moins.",
        "Les salariés proches de la retraite avec une grande ancienneté pèsent le plus : leur IFC est proche, grande, et presque certaine." ] },
    ],
    termes: ["vapf", "dette", "charge", "actualisation", "croissance", "turnover", "mortalite"],
  },
  {
    id: "conventions", groupe: "Référence", titre: "Les conventions préremplies",
    resume: "Les barèmes intégrés, leurs sources et leur degré de vérification.",
    sections: [
      { titre: "Comment les lire", texte: [
        "Chaque convention est datée : une version révisée ne remplace pas l'ancienne, qui reste la référence d'une étude antérieure.",
        "« Valide » : taux concordants entre plusieurs sources. « À valider » : la plateforme n'a pas pu confirmer le barème ; une étude ne sort pas sur une convention à valider.",
        "La vérification dit honnêtement ce qui a été lu : plusieurs barèmes viennent de sources secondaires concordantes, le texte officiel n'ayant pas pu être consulté." ] },
    ],
    termes: ["convention", "plancher"],
  },
  {
    id: "verifier", groupe: "Référence", titre: "Vérifier un document",
    resume: "Un rapport émis se vérifie en ligne, sans compte.",
    sections: [
      { titre: "Comment", texte: [
        "Chaque page d'un rapport porte son numéro (RL-…) et l'adresse de vérification. Saisissez le numéro sur « Vérifier un document » : la plateforme dit qui l'a émis et quand.",
        "Déposez le fichier PDF lui-même : la plateforme dit s'il est l'original, octet pour octet. Un seul caractère changé, et il ne l'est plus." ] },
    ],
    termes: ["sceau"],
  },
];

export const GROUPES = ["Commencer", "Le parcours", "Comprendre", "Référence"] as const;
