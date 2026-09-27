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
      { titre: "Les points d'attention", texte: [
        "Le tableau de bord du dossier liste ce qui attend : une étude de plus de 12 mois (une clôture est passée), un fichier du personnel trop ancien, un brouillon ou une version du régime en attente depuis plus de 30 jours, un dossier de prise en charge qui n'avance plus (l'assureur tarde à payer, des pièces sont attendues, un refus), un cahier des charges dont la date limite est passée.",
        "Chaque point dit qui agit (l'entreprise ou le conseiller) et mène à la bonne page. « À traiter » passe avant « À surveiller », puis « À savoir ». Rien n'est à « fermer » : un point disparaît quand sa cause est réglée.",
        "« Vos dossiers » compte, sur chaque dossier, ce qui est à traiter et à surveiller." ] },
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
      { titre: "Reprendre où vous en étiez", texte: [
        "« Vos dossiers » propose de reprendre la dernière page que vous avez ouverte dans un dossier (une étude, votre régime…), avec le temps écoulé : un clic, et vous y êtes.",
        "Ce souvenir reste dans ce navigateur, pour vous seul ; un dossier que vous ne suivez plus n'est pas proposé.",
        "Pour aller ailleurs sans chercher dans les menus : Ctrl+K (⌘K sur Mac), ou « Aller à… » sous le nom du dossier.",
        "Sur chaque page d'un dossier, « Aide sur cette page » (ou la touche ?) ouvre ce que le guide en dit, et les mots du métier qu'elle emploie." ] },
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
      { titre: "Partir d'un modèle type", texte: [
        "Pas encore de régime écrit ? « Partir d'un modèle type » propose quatre barèmes calculés depuis votre convention : le minimum conventionnel, la convention majorée de 25 %, les cadres favorisés (une fois et demie la convention), et un barème unique, un seul taux par année.",
        "Chaque modèle est construit pour ne jamais passer sous la convention, à aucune ancienneté, et il ne vient d'aucune entreprise : c'est un point de départ, pas le régime d'un autre.",
        "Vous le reprenez dans le formulaire, l'ajustez et l'enregistrez ; l'analyse habituelle suit, et c'est vous qui adoptez." ] },
      { titre: "Le catalogue anonyme", texte: [
        "« Partir du catalogue anonyme » montre des régimes que d'autres entreprises ont adoptés et accepté de partager : leurs barèmes, leurs mois d'indemnité à 10, 20 et 30 ans, et leur écart à leur convention. Vous en reprenez un dans le formulaire comme un modèle type.",
        "Personne n'y est nommé : ni entreprise, ni document, ni date. Un régime ne se montre que dans un groupe d'au moins cinq entreprises ; quand un groupe est trop petit, le catalogue l'élargit (la taille, puis le secteur, puis le pays s'effacent) plutôt que de montrer une petite case.",
        "Partager le vôtre est un choix de l'entreprise : depuis sa version adoptée, « Partager anonymement », avec votre accord. Vous voyez ce qui part et ce qui ne part pas, et vous pouvez le retirer à tout moment." ] },
      { titre: "Partir d'un texte existant", texte: [
        "Votre accord d'entreprise existe déjà ? « Partir d'un texte existant » lit le PDF et propose le barème de départ à la retraite, catégorie par catégorie, avec la date d'effet et la base de salaire.",
        "Chaque valeur proposée cite le passage d'où elle vient, et la plateforme vérifie que ce passage est bien dans le texte : « introuvable » veut dire qu'il faut relire cette valeur avant tout.",
        "Rien n'est enregistré sans vous : « Reprendre dans le formulaire » préremplit la version, vous la relisez, la corrigez et l'enregistrez ; l'analyse habituelle suit.",
        "Pour l'instant, les textes des pays de la CEMAC seulement. Selon la configuration, la lecture se fait sur la plateforme (formulations courantes) ou par un service d'IA (Anthropic), qui demande alors votre accord avant l'envoi ; la plateforme ne garde que l'empreinte du document." ] },
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
      { titre: "Le comparatif", texte: [
        "Sous les cartes, « Comparer les régimes » met les variantes côte à côte : la dette, la charge, la cotisation initiale et la dette par salarié, chacune avec son écart à la convention seule.",
        "La courbe montre ce que chaque régime verse au départ, en mois de salaire, selon l'ancienneté ; elle s'ouvre sur la catégorie où les régimes diffèrent le plus. Survolez-la (ou touchez-la) pour lire les mois à une ancienneté.",
        "« Qui gagne, qui perd » compare, salarié par salarié, l'indemnité au départ d'un régime à l'autre : combien gagnent, combien perdent, de combien en moyenne, et le plus gros écart, par matricule. Choisissez le point de comparaison et la catégorie.",
        "« Voir le tableau » donne tous ces chiffres en un tableau." ] },
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
        "Le conseiller émet l'étude quand elle est complète. Elle est alors figée, et son rapport PDF est scellé et numéroté (RL-…).",
        "Le rapport s'ouvre sur une synthèse : les chiffres en phrases (ce que l'entreprise doit, ce que coûte l'année, ce qu'il faudrait verser, quand l'argent sort), puis la décision à prendre. Suivent la courbe du régime face à la convention, la pyramide des âges et des anciennetés, chaque hypothèse avec son rôle et son effet, l'échéancier en graphiques face au fonds constitué, les sensibilités et le lien vers la note de méthode.",
        "« Exporter en Excel » donne l'étude en classeur : la synthèse et les hypothèses, l'échéancier (cumuls et parts en formules), les catégories, les sensibilités, et le calcul salarié par salarié, par matricule." ] },
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
      { titre: "Les réponses des assureurs", texte: [
        "Chaque réponse se saisit dans la grille du cahier, avec l'offre de l'assureur en PDF si elle est jointe. Ce que l'assureur n'a pas dit reste vide : c'est signalé, pas deviné.",
        "La plateforme confronte chaque réponse aux conditions demandées, critère par critère — conforme, en écart, ou non renseigné — et signale une réponse arrivée après la date limite.",
        "Les réponses sont classées par leur coût net actualisé, le même calcul que la comparaison d'offres. La recommandée est la moins chère des CONFORMES : une offre moins chère qui impose une pénalité de transfert ne l'est pas.",
        "L'entreprise choisit. Retenir une autre offre que la recommandée est permis, et se motive : la raison figure au dossier. Un cahier attribué est clos ; le conseiller enregistre alors le contrat." ] },
      { titre: "Changer d'assureur", texte: [
        "Les conditions de transfert (préavis, pénalité) font partie des exigences : c'est ce qui vous permettra de changer d'assureur plus tard sans perdre votre fonds.",
        "Les réponses s'exportent en Excel : le classement, la conformité critère par critère et la projection sous les trois scénarios de rendement." ] },
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
      { titre: "Ce que les rapports en font", texte: [
        "L'étude lit les départs enregistrés à sa date : les retraites que l'étude précédente prévoyait contre celles qui ont eu lieu, année par année — c'est scellé avec l'étude.",
        "La rotation observée (démissions et licenciements, rapportés à l'effectif) est comparée à l'hypothèse. Avec au moins cinq départs et un écart d'un demi-point, elle est PROPOSÉE ; jamais appliquée d'office : la retenir se fait dans une nouvelle étude, avec une justification qui figure au rapport.",
        "Un salarié enregistré comme parti mais encore présent dans le fichier est signalé : l'engagement le compterait.",
        "Le cahier des charges montre aux assureurs les retraites passées par années regroupées — au moins trois par période — et les délais de paiement constatés sur les dossiers suivis." ] },
    ],
    termes: ["turnover", "fonds", "prise_en_charge", "courtage", "comparaison"],
  },
  {
    id: "remuneration", groupe: "Le parcours", titre: "Comment nous sommes rémunérés", ecran: "remuneration",
    resume: "Ce que vous payez, ce que l'assureur nous verse : écrit avant que vous ne signiez.",
    sections: [
      { titre: "Trois façons d'être rémunéré", texte: [
        "Des honoraires, que vous payez : par étude actuarielle et, le cas échéant, par salarié évalué, hors taxes.",
        "Une commission, que l'assureur retenu nous verse : un pourcentage des primes, affiché tel quel.",
        "Ou les deux. La page dit toujours lequel, et depuis quand." ] },
      { titre: "Qui les fixe, et ce que ça change", texte: [
        "Votre conseiller enregistre les conditions, datées ; les anciennes restent dans l'historique.",
        "Tant qu'aucune condition n'est fixée, une étude ne peut pas être émise : vous savez ce qu'elle coûte avant de la recevoir.",
        "Une commission suppose un mandat de courtage : sans mandat enregistré au contrat, la plateforme le signale." ] },
    ],
  },
  {
    id: "equipe", groupe: "Le parcours", titre: "L'équipe du dossier", ecran: "equipe",
    resume: "Qui suit le dossier, ce que chacun peut faire, et comment inscrire quelqu'un.",
    sections: [
      { titre: "Les rôles", texte: [
        "La DRH de l'entreprise dépose le personnel, décrit et adopte le régime, lance les études et choisit l'assureur : l'entreprise décide.",
        "Le conseiller suit le dossier : il relit et émet les études, fixe les conditions de rémunération, inscrit les personnes.",
        "La lecture seule consulte tout, sans rien modifier." ] },
      { titre: "Inscrire quelqu'un", texte: [
        "Le conseiller inscrit une personne par son nom et son numéro de téléphone, avec son rôle.",
        "Elle se connecte ensuite avec ce numéro, par un code reçu par message : aucun mot de passe à transmettre." ] },
      { titre: "L'état du dossier", texte: [
        "Un dossier est ouvert, suspendu, clôturé ou archivé. Le conseiller seul en change l'état, depuis la page Équipe, toujours avec un motif daté et signé ; l'historique le garde, et un bandeau le rappelle sur chaque page.",
        "Suspendu (impayé, litige, pièces attendues) : tout se lit et s'exporte, mais aucune étude ne s'émet et aucun cahier ne part avant la reprise.",
        "Clôturé (fin du mandat, changement de courtier, cessation) : lecture seule pour tous. Le conseiller peut encore le reprendre pendant 90 jours ; au-delà, le dossier est archivé.",
        "Archivé : le personnel déposé est effacé et le dossier ne s'ouvre plus. Les études, les rapports scellés et le journal sont conservés : chaque document reste vérifiable par son numéro.",
        "Seul un dossier vide, ouvert par erreur, se supprime. Dès qu'un document a été émis, son numéro circule : le dossier se clôture, il ne disparaît pas." ] },
    ],
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
    id: "methode", groupe: "Comprendre", titre: "La méthode actuarielle en détail",
    resume: "Les formules, les hypothèses et leurs valeurs par défaut, le financement, et ce que le calcul ne fait pas.",
    sections: [
      { titre: "La méthode", texte: [
        "La plateforme applique la méthode prospective des unités de crédit projetées, avec une répartition linéaire des droits au prorata de l'ancienneté. Le calcul se fait salarié par salarié, puis on additionne. Les calculs se font sans arrondi intermédiaire ; les totaux sont arrondis au franc.",
        "Âge et ancienneté se comptent en années révolues, plus les jours écoulés depuis le dernier anniversaire divisés par 365 (comme DATEDIF dans un tableur)." ] },
      { titre: "Les formules, pour un salarié", texte: [
        "Années restantes n = âge de retraite − âge. Ancienneté totale A = l'ancienneté qu'il aura à la retraite.",
        "Salaire de fin de carrière (mensuel) = salaire annuel ÷ 12 × ((1 + inflation) × (1 + croissance des salaires))ⁿ.",
        "Mois dus = le barème appliqué à A (arrondie en années révolues ou en mois, selon le régime), nuls sous l'ancienneté minimale, bornés par le plafond ; avec un régime, la convention reste le plancher et le plus favorable des deux est retenu.",
        "IFC = salaire de fin de carrière × mois dus.",
        "Survie = l(âge de retraite) ÷ l(âge actuel), lus dans la table de mortalité TV CIMA F.",
        "Présence = le produit, de l'âge actuel à la veille de la retraite, de (1 − taux de rotation).",
        "VAPF = IFC × survie × présence × (1 + taux d'actualisation)⁻ⁿ.",
        "Dette = VAPF × ancienneté actuelle ÷ A. Charge de l'année = VAPF ÷ A." ] },
      { titre: "Du total à la cotisation", texte: [
        "Cotisation nette = dette + charge − fonds déjà constitué (jamais négative).",
        "Cotisation totale = cotisation nette × (1 + frais sur cotisation). L'étude affiche ce rapprochement ligne à ligne." ] },
      { titre: "Les hypothèses par défaut", texte: [
        "Taux d'actualisation 3,5 %. Croissance des salaires 2 %. Inflation 0 %. Départ à 60 ans. Rotation 2 % par an à tout âge. Table TV CIMA F. Frais sur cotisation 4 %.",
        "Toutes se règlent dans la section « Hypothèses » du formulaire de l'étude, repliée par défaut : chacune dit sa valeur par défaut, son rôle, son effet et comment la fixer, et « Revenir aux valeurs par défaut » annule tout. La rotation peut y être donnée par tranche d'âge.",
        "S'écarter d'une valeur par défaut demande une justification. Elle est imprimée dans le rapport scellé.",
        "L'étude recalcule la dette avec le taux d'actualisation, la croissance des salaires et la rotation à un point de moins et à un point de plus : ce sont les sensibilités." ] },
      { titre: "Le financement", texte: [
        "Chaque année, l'entreprise cotise : la charge indexée sur les salaires, plus une part du déficit initial (dette − fonds) amorti sur le nombre d'années choisi. L'assureur prélève ses frais, crédite le fonds au taux garanti plus sa participation aux bénéfices, puis les prestations probables de l'année sont payées par le fonds, dans la limite de ce qu'il contient.",
        "Trois scénarios de rendement : prudent 3,5 %, central 5 %, favorable 6,5 %. Les offres se comparent sur leur coût net actualisé, dans le scénario central : cotisations et découverts actualisés, moins le fonds restant à l'horizon." ] },
      { titre: "L'expérience réelle", texte: [
        "La rotation observée est le nombre de démissions et de licenciements ÷ (années × effectif), sur cinq ans au plus. Elle n'est crédible qu'à partir de cinq départs, et proposée seulement si elle s'écarte d'au moins un demi-point. Elle n'est jamais appliquée d'office." ] },
      { titre: "Ce que le calcul ne fait pas", texte: [
        "Seul le départ à la retraite est chiffré ; les autres événements couverts par un régime (départ anticipé, licenciement économique, décès) sont signalés, pas évalués.",
        "Une seule table de mortalité pour tous, la table féminine : c'est une hypothèse prudente, les femmes y vivant plus longtemps.",
        "Une croissance des salaires uniforme, sans échelle par âge. Un régime fondé sur la moyenne des 12 derniers mois est évalué sur le salaire courant projeté, et c'est signalé.",
        "L'étude est un calcul d'aide à la décision, pas un avis juridique ou fiscal." ] },
    ],
    termes: ["vapf", "dette", "charge", "actualisation", "croissance", "turnover", "mortalite", "plancher"],
  },
  {
    id: "conventions", groupe: "Référence", titre: "Les conventions préremplies",
    resume: "Les barèmes intégrés pour les pays de la CEMAC, leurs sources et leur degré de vérification.",
    sections: [
      { titre: "Comment les lire", texte: [
        "La plateforme couvre pour l'instant les six pays de la CEMAC : Cameroun, Gabon, Congo, Tchad, Centrafrique, Guinée équatoriale. Un pays sans convention préremplie est dit comme tel.",
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
