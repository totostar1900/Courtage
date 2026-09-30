# Vitrine, contrat, WhatsApp, pénombre — 2026-09-30

Six demandes, une livraison.

## 1. Les marchés de l'équipe

« Amérique » disparaît de la plateforme. Le repère « Quatre marchés » devient **« Du Cameroun à l'Europe »** — « Une
pratique des marchés locaux, africains et européens ». Le texte de l'équipe cite le Cameroun, l'Afrique et l'Europe.
Un test lit les sources et refuse le mot.

## 2. Le visuel du bandeau

Un aperçu qui défile (`ApercuDefilant`), quatre panneaux, 5,5 s chacun : l'engagement chiffré et scellé ; les offres
classées par rendement net (assureurs A, B, C) ; les départs des cinq années à venir ; un dossier de départ suivi
jusqu'au paiement. Des chiffres d'exemple, dits « Exemple ». Il s'arrête sous la souris ou le focus, reste immobile
si l'appareil demande moins de mouvement ; quatre traits le mènent à la main.

## 3. Plus de page Accompagnement

Le mandat de courtage — demande, proposition, lecture, signature, historique — vit dans la page **Contrat**, qui
ouvre désormais le parcours du menu (il n'y est plus en double). `/accompagnement` mène à `/contrat` ; les avis par
courriel et WhatsApp aussi. Rien ne change côté API : les routes `/mandats` restent les mêmes.

## 4. Plus de fil écrit ; un bouton WhatsApp

L'historique « Messages écrits sur la plateforme » disparaît de Contact, avec le compte de non-lus du menu et de la
file des inscriptions. Un bouton WhatsApp flotte en bas à droite : dans un dossier, vers le conseiller (à défaut, le
cabinet) ; sur les pages publiques, vers le cabinet ; jamais pour le courtier, ni sur la page d'un assureur consulté.
Le message prérempli ne dit que le sujet. Au-dessus de la barre du dossier sur téléphone ; jamais imprimé.

## 5. La base de calcul d'une étude

« Base » et « Convention (sans régime) » côte à côte laissaient croire à deux choix, alors que le second ne compte
que sans régime (l'API l'ignore sinon, et refuse une convention étrangère au régime). Le formulaire dit désormais
**« Base de calcul »** : le minimum de la convention collective — et seulement alors le code de la convention — ou
« Votre régime : … », une version adoptée, dont chaque catégorie porte déjà sa convention. Une phrase dit ce que
chaque base mesure : le minimum légal et conventionnel de la branche ; ce que l'entreprise s'est engagée à verser
en plus. Les comparer, c'est lire ce que coûtent ses engagements propres (le pli « Comparer » de la même page).

## 6. Le thème pénombre

Un troisième thème, le vrai milieu : une ardoise (fond #46515e, surface #515d6b, L* 34 à 39, quand le clair est à 97
et le sombre à 3), le texte clair dessus, chaque couleur au moins à 4,5:1 sur la surface. `data-theme="dim"`, écrit
après le sombre pour l'emporter à poids égal ; la barre du navigateur sur téléphone prend son fond ; l'impression
reste claire.
