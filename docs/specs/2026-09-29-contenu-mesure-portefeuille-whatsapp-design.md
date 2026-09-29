# Contenus, mesure d'audience, portefeuille du courtier, WhatsApp, préparation du test d'intrusion

Date : 2026-09-29.

## 1. Deux pages de contenu

- **`/ifc` — Les indemnités de fin de carrière** : ce que c'est (une somme due au salarié qui part à la retraite, fixée
  par la convention collective ou l'accord d'entreprise, en mois de salaire selon l'ancienneté) ; pourquoi c'est un
  engagement qui grandit chaque année ; comment il se mesure (méthode actuarielle, hypothèses datées) ; comment le
  financer (provision interne ou contrat d'assurance) ; ce que fait la plateforme ; renvoi vers l'essai.
- **`/ifc/cameroun` — Les IFC au Cameroun** : la source de l'obligation (les conventions collectives, et l'accord
  d'entreprise quand il est plus favorable) ; **les barèmes préremplis de la plateforme pour le Cameroun**, lus en
  direct dans le référentiel avec leur statut, leur date d'effet et leurs sources ; la comptabilisation (SYSCOHADA
  révisé) et la fiscalité, dans la rédaction prudente des notes juridiques existantes ; le financement.
- Règle : **rien d'inventé**. Un barème vient du référentiel, sourcé ; un point de droit est formulé avec prudence
  (« selon notre lecture », « à examiner avec votre expert-comptable / fiscaliste ») ; aucune mention « à valider ».
- Publiques, titrées, dans le plan du site, reliées depuis la vitrine et le pied de page.

## 2. Une mesure d'audience qui respecte la vie privée

- **Aucun témoin, aucun identifiant, aucune adresse IP gardée, aucun tiers.** Un compteur par jour, par événement et
  par source : `mesures(jour, evenement, source, n)`.
- Événements, d'une liste fermée : `vitrine`, `contenu_ifc`, `contenu_cameroun`, `essai_ouvert`, `essai_calcule`,
  `inscription_ouverte` (envoyés par la page) ; `inscription_faite`, `mandat_signe` (comptés par le serveur au moment
  de l'acte).
- Source : la catégorie du référent (`direct`, `recherche`, `reseau_social`, `autre`), jamais l'adresse.
- Le navigateur n'envoie rien si « Do Not Track » ou « Global Privacy Control » est actif.
- Le courtier lit l'entonnoir des 30 derniers jours sur son accueil, avec les taux de passage.
- La politique de confidentialité le dit (nouvelle version).

## 3. Le pipeline et le portefeuille du courtier

`/portefeuille`, pour l'administrateur de la plateforme (tous les dossiers) et le conseiller (les siens) :

- **Pipeline** : chaque dossier à son étape — inscrit en attente, confirmé, accompagnement demandé, mandat proposé,
  sous mandat, en consultation, offre choisie, police en vigueur — avec le nombre de dossiers par étape, depuis quand
  il y est, et son conseiller.
- **Portefeuille** : les dossiers sous mandat — assureur et statut de la police, primes en retard, prochaine étape de
  l'année et son échéance, dossiers de prise en charge ouverts, alertes graves.
- Lu dossier par dossier dans son propre contexte (RLS) ; rien de nouveau n'est stocké.

## 4. Les avis sur WhatsApp

- Chacun peut, dans son profil, recevoir **aussi** ses avis sur WhatsApp, au numéro vérifié de son compte (désactivé
  par défaut ; migration 0032).
- WhatsApp exige, pour un message qu'une entreprise envoie la première, un **modèle approuvé** : un seul modèle
  générique (« Courtage : {{1}} — {{2}} », le sujet de l'avis et le lien), déclaré par `TWILIO_WHATSAPP_MODELE` (son
  identifiant de contenu Twilio). Sans modèle ou sans émetteur WhatsApp, rien ne part sur WhatsApp ; le courriel
  reste.
- Mêmes règles que le courriel : après validation, jamais à l'auteur, rien du dossier.

## 5. Préparer le test d'intrusion externe

Le test lui-même est confié à un prestataire indépendant, sur l'environnement de recette. Ce lot prépare :

- **Le cahier du test** (`docs/securite/test-intrusion.md`) : périmètre, environnement, comptes par rôle, règles
  d'engagement, hors périmètre, ce qui est attendu en retour.
- **Les contrôles que le testeur ferait d'abord**, écrits comme des tests : chaque route d'un dossier refuse un
  étranger au dossier ; chaque écriture par cookie exige l'en-tête anti-CSRF ; les routes publiques sont limitées en
  fréquence ; une route publique ne rend rien d'un dossier.
- **L'audit des dépendances** (Python, JavaScript) et la correction de ce qu'il trouve.
