# Le parcours client, revu — et une interface plus nette

Retours du 2026-09-29, point par point. Règles inchangées : la plateforme ne fait circuler aucun argent ; rien d'inventé
(ni taux, ni offre) ; le client ne compare que ce que son conseiller lui a apporté.

## 1. L'essai sans compte

- **Le fichier se voit, et se retire.** Le champ natif disait « aucun fichier choisi » alors que l'essai en gardait un
  (repris du navigateur). Un composant de dépôt (`DepotFichier`) remplace le champ : zone à glisser ou à cliquer, puis
  le fichier retenu en clair (nom, taille) avec « Retirer ». Réutilisé partout où l'on dépose un fichier.
- **Rien ne reste après le départ.** L'essai n'était oublié qu'à la fermeture de l'onglet. Il porte désormais sa date
  et expire au bout de 30 minutes ; « Retirer » l'oublie tout de suite ; « Recommencer » efface tout.
- **Et ensuite ?** Sous le résultat, les étapes qui suivent (créer le compte en 2 minutes → un conseiller vous appelle
  sous 2 jours ouvrés → le rapport scellé → les assureurs consultés → vous choisissez), et trois portes : créer le
  compte (la saisie est reprise), écrire au cabinet sur WhatsApp, être rappelé.

## 2. Le téléphone et son indicatif

Un champ unique (`ChampTelephone`) : l'indicatif à choisir (drapeau, pays, +237 par défaut ; la CEMAC, la Côte
d'Ivoire, le Sénégal, la France…) et le numéro national. Il rend la forme E.164 que le serveur attend déjà. Connexion,
inscription, demande de rappel, invitation d'un membre.

## 3. Simuler rejoint l'étude

« Simuler » comparait plusieurs versions du régime côte à côte ; « Étude » en évalue une. Ce n'était pas un doublon,
mais deux pages pour une même question. La comparaison devient un volet repliable de la page Étude (« Comparer des
régimes avant d'étudier »), la page et l'entrée du menu disparaissent ; l'ancienne adresse y renvoie.

## 4. Nous contacter, et moins de bruit

- **Messages → Nous contacter.** Écrire se fait sur WhatsApp ou par courriel, directement : les boutons ouvrent
  WhatsApp au numéro du conseiller (à défaut, celui du cabinet), le courriel, l'appel, ou la demande de rappel. Le fil
  écrit sur la plateforme reste lisible, replié, quand il existe (le courtier y a pu écrire) ; on n'y écrit plus.
- **Le bandeau d'inscription** : « Écrire à votre conseiller » devient un bouton (WhatsApp) ; « Retirer mon inscription »
  disparaît de l'écran (une inscription non confirmée s'efface seule à 30 jours ; le courtier peut la retirer).
- **« Nettoyer le dossier »** disparaît de la page Équipe.

## 5. Les départs attendent le contrat

Les départs et les prises en charge n'ont de sens qu'une fois le contrat d'assurance signé et en vigueur. Nouvelle
capacité `departs`, contrôlée au serveur (déclarer, importer, corriger, demander une prise en charge) : ouverte quand
une police du placement est **en vigueur**, ou qu'un contrat de courtage avec un assureur est enregistré en vigueur par
le conseiller (un client arrivé avec son contrat). Avant : la page dit ce qui manque et où en est le contrat.

## 6. L'accompagnement dès l'inscription

La demande d'accompagnement en courtage est une des premières choses que l'entreprise dit : elle devient la quatrième
étape de l'inscription (« Vos besoins », les mêmes cases que la page Accompagnement, et un mot libre), envoyée juste
après la création du compte. Dans le dossier, « Accompagnement » passe en tête du parcours.

## 7. Les offres : apportées par le conseiller, classées par rendement net

- **Plus de comparaison sur des chiffres inventés.** La page « Financement » laissait le client comparer des offres
  préremplies (« Assureur A, 2,5 % »). Elle devient **« Offres »** : les offres que le conseiller a reçues des assureurs
  consultés (réponses au cahier des charges, déposées par le conseiller ou par l'assureur via son lien), et rien
  d'autre. Avant la confirmation, ou tant qu'aucune offre n'est arrivée, la page dit ce qui vient et qui le fait.
- **Le critère : le rendement net.** L'offre la plus intéressante est celle qui rapporte le plus au fonds, une fois
  tout payé. Pour chaque offre, sous le scénario central : le taux servi (garanti + participation) − les frais sur
  encours − l'effet des frais sur cotisations = **le rendement net**, calculé exactement comme le taux qui égalise
  ce qui entre dans le fonds (cotisations brutes) et ce qui en sort ou y reste (prestations payées, fonds à
  l'horizon). Les offres sont classées par rendement net décroissant ; la recommandée est la meilleure des conformes.
  Le coût net actualisé reste dans le détail.
- **Le client peut ajouter une offre, pour comparer.** Un devis reçu directement, saisi par l'entreprise : il entre dans
  le classement, marqué « ajoutée par vous — pour comparaison » (migration 0033, `reponses_fiche.pour_comparaison`). Il ne
  se retient pas : pour la retenir, le conseiller consulte cet assureur. Il ne s'ajoute qu'une fois une offre du
  conseiller arrivée.

## 8. L'interface

Audit et proposition : `docs/design/audit-2026-09-29.md` (et la page de maquettes publiée). Ce lot applique le socle :

- des sections nettement séparées (titre de section, sous-titre, plus d'air : 56 px entre sections, 24 px dans une
  carte), un fond de page légèrement contrasté, des cartes à ombre douce plutôt qu'à trait ;
- des volets repliables dessinés (`<details class="pli">` : chevron animé, en-tête cliquable plein, résumé à droite) ;
- les boutons : primaire plein, secondaire à contour, lien discret ; des tailles cohérentes ; des états de survol et de
  focus visibles ;
- le dépôt de fichier (§1), le champ téléphone (§2) ;
- la vitrine : un héros plus affirmé, les étapes en frise, la preuve (« ce que vous obtenez ») en cartes à icône.
