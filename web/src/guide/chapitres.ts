// Le guide : un texte, lu par l'écran Guide, cité par les infobulles, parcouru par la visite.
// Un chapitre dit ce qu'on fait, pourquoi, et ce que la plateforme fait pour vous — dans cet ordre.

// Deux langues : le texte français est écrit ici tel quel ; l'anglais vit à côté, dans ./chapitres-en, chapitre par
// chapitre et section par section, dans le même ordre. `CHAPITRES` se relit dans la langue du moment (une liste
// vivante, comme les étapes de la visite) : pas de texte figé à l'import.

import { langue } from "../i18n";
import { CHAPITRES_EN, GROUPES_EN } from "./chapitres-en";
import type { CleTerme } from "./glossaire";
import { listeVivante } from "./visite";

type Groupe = "Commencer" | "Le parcours" | "Comprendre" | "Référence";

export interface Chapitre {
  id: string;
  groupe: string;           // le nom du groupe, dans la langue du moment (l'un de GROUPES)
  titre: string;
  resume: string;
  sections: { titre: string; texte: string[] }[];
  ecran?: string;           // l'écran du dossier dont parle le chapitre (chemin relatif au dossier)
  termes?: CleTerme[];
}

const FR: (Chapitre & { groupe: Groupe })[] = [
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
        "Le conseiller relit, émet l'étude et le cahier des charges.",
        "Les assureurs répondent au cahier des charges ; vous comparez sur une base commune." ] },
      { titre: "Les points d'attention", texte: [
        "Le tableau de bord du dossier liste ce qui attend : une étude de plus de 12 mois (une clôture est passée), un fichier du personnel trop ancien, un brouillon ou une version du régime en attente depuis plus de 30 jours, un dossier de prise en charge qui n'avance plus (l'assureur tarde à payer, des pièces sont attendues, un refus), un cahier des charges dont la date limite est passée.",
        "Chaque point dit qui agit (l'entreprise ou le conseiller) et mène à la bonne page. « À traiter » passe avant « À surveiller », puis « À savoir ». Rien n'est à « fermer » : un point disparaît quand sa cause est réglée.",
        "« Vos dossiers » compte, sur chaque dossier, ce qui est à traiter et à surveiller." ] },
    ],
    termes: ["ifc", "convention", "regime"],
  },
  {
    id: "inscription", groupe: "Commencer", titre: "Essayer, s'inscrire, être confirmé",
    resume: "Voir ses chiffres sans compte ; s'inscrire en quelques minutes ; tout travailler en attendant la confirmation.",
    sections: [
      { titre: "Essayer sans compte", texte: [
        "« Essayer sans compte » calcule votre engagement à l'écran : votre personnel (300 salariés au plus), votre fonds, la convention seule ou un modèle type.",
        "Rien n'est gardé sur la plateforme ; l'estimation n'est ni scellée ni imprimable. « Enregistrer mes résultats » mène à l'inscription, qui reprend votre saisie." ] },
      { titre: "S'inscrire", texte: [
        "Votre téléphone et votre adresse électronique sont vérifiés par un code chacun. Vous indiquez votre nom, votre fonction et l'entreprise : raison sociale, pays, numéro RCCM (obligatoire), taille, secteur, adresse. Vous acceptez les conditions d'utilisation et la politique de confidentialité ; la version acceptée reste sur votre compte (« Mon profil »).",
        "Le document RCCM peut suivre : déposez-le depuis le bandeau de votre dossier. Une entreprise n'a qu'un dossier : un numéro RCCM déjà inscrit renvoie vers son administrateur." ] },
      { titre: "En attendant la confirmation", texte: [
        "Votre conseiller vous contacte sous deux jours ouvrés, vérifie l'entreprise et confirme l'inscription. D'ici là, tout le travail est ouvert : personnel, régime, simulations, études à l'écran, départs, messages à votre conseiller. Un courriel vous prévient de ce qui vous attend (la confirmation, un message, un mandat à signer) ; ces avis se coupent dans « Mon profil ».",
        "Ce qui sort de la plateforme attend la confirmation : rapports scellés, exports, notes, invitation de collègues, catalogue anonyme, mandat. Une inscription non confirmée est effacée au bout de 30 jours ; vous pouvez aussi la retirer vous-même." ] },
    ],
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
      { titre: "Brouillon ou adoptée", texte: [
        "Une version est un brouillon ou une version adoptée, rien d'autre. Ses dates sont écrites sur sa carte : « s'applique depuis », « s'appliquera à partir du », « remplacée par la version N ». La page range les versions en trois zones : en application, brouillons, et l'historique, replié.",
        "Toutes les actions d'une version sont dans son menu ⋮, en haut à droite de sa carte. Une action impossible reste visible, grisée, avec sa raison.",
        "Un brouillon se modifie sur place, se duplique, s'analyse, se compare dans Simuler, s'adopte ou se supprime (ses études en brouillon partent avec lui).",
        "Adopter, c'est communiquer : l'administrateur de l'entreprise adopte, la version se fige, et ses deux notes se tirent de son menu : aux salariés (ce que le régime leur verse) et aux assureurs (le régime à assurer). Pour la changer, on la duplique en brouillon.",
        "Une version adoptée se supprime tant que rien ne la cite (étude émise, cahier des charges, note émise, partage au catalogue) : c'est revenir sur une décision, avec un motif. « Faire le ménage » propose tout ce qui peut partir.",
        "L'analyse range ses constats en trois niveaux : Bloquant, Attention (un régime moins favorable que la convention s'adopte en le confirmant) et Bon à savoir. Ses points juridiques et fiscaux sont des repères, à examiner avec votre conseil." ] },


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
        "Votre conseiller consulte chaque assureur depuis la page du cahier : l'assureur reçoit par courriel un lien personnel, valable jusqu'à la date limite, lit le cahier et dépose sa grille avec son offre en PDF, sans compte. Sa réponse rejoint les autres, marquée « déposée par l'assureur » ; « Assureurs consultés » dit qui a été consulté, quand, qui a ouvert et qui a répondu — la preuve d'une mise en concurrence loyale.",
        "Votre conseiller peut aussi saisir une réponse reçue autrement ; vous les lisez et choisissez. Retenir une autre offre que la recommandée est permis, et se motive : la raison figure au dossier. Un cahier attribué est clos ; le conseiller enregistre alors le contrat." ] },
      { titre: "Changer d'assureur", texte: [
        "Les conditions de transfert (préavis, pénalité) font partie des exigences : c'est ce qui vous permettra de changer d'assureur plus tard sans perdre votre fonds.",
        "Les réponses s'exportent en Excel : le classement, la conformité critère par critère et la projection sous les trois scénarios de rendement." ] },
    ],
    termes: ["cahier", "anonymat"],
  },
  {
    id: "contrat", groupe: "Le parcours", titre: "Le courtage", ecran: "contrat",
    resume: "La plateforme est votre courtier : mandatée par vous, gratuite pour vous.",
    sections: [
      { titre: "Un seul service", texte: [
        "La plateforme est votre courtier : vous la mandatez, elle consulte les assureurs, place votre engagement, puis porte vos prestations auprès de l'assureur retenu.",
        "Le mandat est gratuit pour l'entreprise : le courtier est rémunéré uniquement par la commission de l'assureur retenu, dont il communique le taux sur simple demande.",
        "Le contrat de courtage naît de la signature du mandat ; l'écran « Contrat » le montre, avec l'assureur une fois le contrat placé." ] },
      { titre: "Signer le mandat", texte: [
        "Depuis « Accompagnement », l'entreprise dit ce qu'elle attend : placer son engagement, remettre son contrat en concurrence, faire porter ses départs, être conseillée sur son régime.",
        "Le conseiller propose un mandat de courtage : les missions, la date d'effet, la durée, le préavis, l'exclusivité. Le texte complet s'affiche sur la page.",
        "L'administrateur le lit et le signe en ligne, sur le texte affiché, en disant en quelle qualité : représentant légal de l'entreprise, ou délégataire — il dépose alors la délégation de pouvoir, que le conseiller vérifie. Le mandat signé est scellé, vérifiable par son numéro. Rien n'engage avant la signature." ] },
      { titre: "Quand un salarié part", texte: [
        "Sous mandat : vous déclarez le départ, nous montons le dossier, le transmettons et suivons le paiement. Pour ce dossier seulement, nous recueillons l'identité du bénéficiaire.",
        "Sans mandat au jour du départ, la prise en charge s'est faite entre l'entreprise et son assureur : vous gardez la fiche de calcul scellée et déclarez ce qui a été payé, sans nom.",
        "Dans les deux cas, le départ enregistré sert l'expérience réelle de vos rapports." ] },
    ],
    termes: ["courtage", "mandat"],
  },
  {
    id: "placement", groupe: "Le parcours", titre: "Le placement : police, primes, virements", ecran: "placement",
    resume: "De l'offre retenue à la police en vigueur ; les primes se paient par virement, jamais sur la plateforme.",
    sections: [
      { titre: "La police", texte: [
        "Une fois l'offre choisie, le conseiller crée la police. Elle avance par des faits, chacun avec sa preuve : police reçue (le document est déposé), signée avec l'assureur (vous en déclarez la date), première prime encaissée (la quittance de l'assureur), puis en vigueur à sa date d'effet.",
        "Rien ne se coche à la main : la frise se lit sur les pièces et les dates. Les avenants s'ajoutent à la police." ] },
      { titre: "Payer une prime", texte: [
        "La plateforme ne paie rien et ne reçoit rien. L'assureur envoie un appel de prime avec ses coordonnées bancaires ; le conseiller l'enregistre ici ; vous virez depuis votre banque, sur le compte de l'assureur, puis vous déclarez le virement (date, montant, référence) et joignez l'avis de votre banque.",
        "Le conseiller dépose la quittance de l'assureur et confirme l'encaissement : l'appel passe de « payé (déclaré) » à « encaissé (confirmé) ». Une échéance dépassée sans virement déclaré s'affiche en retard." ] },
      { titre: "Les coordonnées bancaires, contre la fraude", texte: [
        "Chaque appel est confronté au compte que le courtier a enregistré pour cet assureur, après l'avoir fait confirmer par téléphone. Un compte différent ou inconnu s'affiche en rouge : « Ne pas payer ». Le conseiller rappelle alors l'assureur au numéro qu'il connaît, jamais celui de l'appel reçu, et enregistre qui a confirmé.",
        "Les coordonnées ne partent jamais par courriel : l'avis dit seulement qu'un appel vous attend. Un « nouveau RIB » reçu par courriel ne se paie pas avant d'avoir été confirmé ici." ] },
      { titre: "Les relevés du fonds", texte: [
        "Le conseiller dépose les relevés de l'assureur avec le montant du fonds. La page les rapproche des primes encaissées et du fonds que retient votre dernière étude : un écart est un constat à expliquer, jamais une erreur bloquante." ] },
    ],
    termes: ["courtage"],
  },
  {
    id: "annee", groupe: "Le parcours", titre: "L'année du dossier",
    resume: "L'engagement se remesure chaque année, à la même date : la plateforme tient le calendrier et le rappelle.",
    sections: [
      { titre: "Le calendrier", texte: [
        "La dernière étude émise fixe la date de la prochaine évaluation : la même, un an plus tard. Viennent alors, dans l'ordre, la mise à jour du personnel à cette date (un mois pour la faire), le relevé annuel de l'assureur si le contrat est en vigueur, puis l'évaluation de l'année (deux mois).",
        "Avant l'anniversaire de la police, votre conseiller revoit le contrat avec vous : conditions, rendement servi, opportunité de le remettre en concurrence." ] },
      { titre: "Rien à cocher", texte: [
        "Chaque étape se lit dans vos données : un fichier du personnel daté de l'évaluation, un relevé déposé, une étude émise. Quand l'évaluation de l'année est émise, le calendrier passe à l'année suivante de lui-même.",
        "« L'année du dossier », au tableau de bord, montre chaque étape avec son échéance : faite, à venir, bientôt, en retard." ] },
      { titre: "Les rappels", texte: [
        "Un courriel vous prévient quand une étape devient bientôt due, puis si elle est en retard — une fois pour chacune, jamais plus. Il ne dit rien de votre dossier : l'étape, l'échéance et le lien. Vous pouvez couper ces avis dans « Mon profil »." ] },
    ],
    termes: ["dette"],
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
        "L'identité et les pièces sont effacées douze mois après le paiement. Le numéro du dossier se vérifie toujours : son sceau public ne porte aucune donnée personnelle." ] },
      { titre: "Un départ sans mandat", texte: [
        "Sans mandat au jour du départ, l'entreprise a traité avec son assureur. « Fiche de calcul et paiement » donne la fiche de calcul scellée (numéro FC-…, sans donnée personnelle) et reçoit ce que l'assureur a payé, sans nom." ] },
      { titre: "Ce que les rapports en font", texte: [
        "L'étude lit les départs enregistrés à sa date : les retraites que l'étude précédente prévoyait contre celles qui ont eu lieu, année par année — c'est scellé avec l'étude.",
        "La rotation observée (démissions et licenciements, rapportés à l'effectif) est comparée à l'hypothèse. Avec au moins cinq départs et un écart d'un demi-point, elle est PROPOSÉE ; jamais appliquée d'office : la retenir se fait dans une nouvelle étude, avec une justification qui figure au rapport.",
        "Un salarié enregistré comme parti mais encore présent dans le fichier est signalé : l'engagement le compterait.",
        "Le cahier des charges montre aux assureurs les retraites passées par années regroupées — au moins trois par période — et les délais de paiement constatés sur les dossiers suivis." ] },
    ],
    termes: ["turnover", "fonds", "prise_en_charge", "courtage"],
  },
  {
    id: "equipe", groupe: "Le parcours", titre: "L'équipe du dossier", ecran: "equipe",
    resume: "Qui suit le dossier, ce que chacun peut faire, et comment inscrire quelqu'un.",
    sections: [
      { titre: "Des droits et une fonction", texte: [
        "Chaque membre a des droits, ce qu'il peut faire, et une fonction, ce qu'il est (DRH, DG, DAF, comptable… à écrire librement).",
        "Administrateur de l'entreprise : décide (adopte le régime, choisit l'assureur) et gère ses collègues. Contributeur : dépose le personnel, prépare régimes et études, sans adopter. Lecture seule : consulte tout. Conseiller : suit le dossier, émet les études, gère toute l'équipe.",
        "Côté entreprise, on voit ses collègues ; le conseiller apparaît à part, comme contact. L'administrateur de l'entreprise inscrit, modifie et retire ses collègues ; il ne donne jamais les droits de conseiller." ] },
      { titre: "Inscrire, modifier, retirer", texte: [
        "« Inscrire quelqu'un » : un nom, une fonction, des droits, un numéro de téléphone. La personne se connecte ensuite avec ce numéro, par un code reçu par message.",
        "Le menu ⋮ d'un membre le modifie (nom, fonction, droits) ou le retire du dossier ; ce qu'il y a fait reste au journal, sous son nom. Le dernier administrateur de l'entreprise et le dernier conseiller restent.",
        "Le numéro est l'identité de connexion : pour le changer, on retire la personne et on l'inscrit avec le nouveau numéro." ] },
      { titre: "L'état du dossier", texte: [
        "Un dossier est ouvert, suspendu, clôturé ou archivé. Le conseiller seul en change l'état, depuis la page Équipe, toujours avec un motif daté et signé ; l'historique le garde, et un bandeau le rappelle sur chaque page.",
        "Suspendu (impayé, litige, pièces attendues) : tout se lit et s'exporte, mais aucune étude ne s'émet et aucun cahier ne part avant la reprise.",
        "Clôturé (fin du mandat, changement de courtier, cessation) : lecture seule pour tous. Le conseiller peut encore le reprendre pendant 90 jours ; au-delà, le dossier est archivé.",
        "Archivé : le personnel déposé est effacé et le dossier ne s'ouvre plus. Les études, les rapports scellés et le journal sont conservés : chaque document reste vérifiable par son numéro.",
        "Seul un dossier vide, ouvert par erreur, se supprime. Dès qu'un document a été émis, son numéro circule : le dossier se clôture, il ne disparaît pas." ] },
      { titre: "Nettoyer le dossier", texte: [
        "La plateforme sert à souscrire et suivre une assurance IFC, pas à garder le personnel. « Nettoyer le dossier », en bas de la page Équipe (administrateur de l'entreprise ou conseiller), se fait en trois temps.",
        "Télécharger l'archive : chaque document scellé en PDF, chaque étude émise en Excel, et un sommaire des numéros à vérifier.",
        "Choisir ce qui part : le personnel (allégé, lignes vidées et empreinte gardée, ou supprimé quand aucune étude émise ne le cite), les brouillons, les études émises et leur rapport (sauf celles qu'un cahier des charges cite).",
        "Confirmer en écrivant NETTOYER. Les sceaux et le journal restent : chaque numéro de document se vérifie toujours, pour la vie de l'entreprise." ] },
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

const GROUPES_FR: Groupe[] = ["Commencer", "Le parcours", "Comprendre", "Référence"];

/** L'anglais posé sur le français : même id, mêmes sections, même nombre de paragraphes. Ce qui manquerait reste en
 *  français plutôt que de disparaître. */
function enAnglais(c: Chapitre & { groupe: Groupe }): Chapitre {
  const en = CHAPITRES_EN[c.id];
  return {
    ...c,
    groupe: GROUPES_EN[c.groupe],
    titre: en?.titre ?? c.titre,
    resume: en?.resume ?? c.resume,
    sections: c.sections.map((s, i) => ({
      titre: en?.sections[i]?.titre ?? s.titre,
      texte: s.texte.map((x, k) => en?.sections[i]?.texte[k] ?? x),
    })),
  };
}

// Une liste par langue, construite une fois : un chapitre garde son identité d'une lecture à l'autre
// (`CHAPITRES.indexOf(c)` retrouve le chapitre que `CHAPITRES.find` a rendu).
let anglais: Chapitre[] | undefined;

/** Les chapitres, dans la langue du moment. */
export function chapitres(): Chapitre[] {
  if (langue() !== "en") return FR;
  return (anglais ??= FR.map(enAnglais));
}

/** Les groupes du sommaire, dans la langue du moment. */
export function groupes(): string[] {
  return langue() === "en" ? GROUPES_FR.map((g) => GROUPES_EN[g]) : GROUPES_FR;
}

/** Les mêmes listes, relues à chaque accès : pour qui les importe comme des constantes. */
export const CHAPITRES: Chapitre[] = listeVivante(chapitres);
export const GROUPES: string[] = listeVivante(groupes);
