# Plateforme ouverte — le lot P1 (avant le premier client réel)

Date : 2026-09-29. Suite de la carte du parcours client (essai → inscription → mandat → placement → vie du contrat)
et de l'inventaire « ce qui reste pour une plateforme complète ». Ce lot couvre ce qui manque AVANT qu'une première
entreprise réelle arrive : être trouvé, dire qui l'on est et à quelles conditions, prévenir hors plateforme, s'assurer
que le signataire engage l'entreprise, et tenir la production.

Hors lot (P2, P3) : la clôture du placement (police, primes), le lien assureur, le cycle annuel, la prise en charge
jusqu'au paiement, le pipeline du courtier, WhatsApp.

## 1. La vitrine publique

`/` montre la vitrine à qui n'a pas de session, l'accueil des dossiers à qui en a une (une adresse, deux lectures :
le premier lien partagé reste `/`). La vitrine dit :

- ce que fait le service : chiffrer le régime IFC, le placer auprès d'un assureur, suivre les départs ;
- les trois niveaux : essayer sans compte, s'inscrire (confirmation en 2 jours ouvrés), mandater ;
- que l'accompagnement **ne coûte rien à l'entreprise** : le courtier est rémunéré par l'assureur retenu ;
- qui est le cabinet : raison sociale, agrément, adresse, contact — lus par `GET /api/v1/public/cabinet`, depuis la
  configuration (`COURTAGE_COURTIER_*`), jamais inventés : une valeur absente s'affiche entre crochets, comme sur le
  mandat ;
- deux actions : « Essayer sans compte » et « S'inscrire », et « Se connecter » pour qui a un compte.

Un pied de page commun à toutes les pages porte les liens légaux et le cabinet.

## 2. Les pages légales

`/mentions-legales`, `/conditions`, `/confidentialite` : publiques, FR/EN à l'écran (le français fait foi, la page le
dit). Rédaction prudente : elles décrivent ce que la plateforme fait réellement (ce qui est gardé, combien de temps,
qui le lit, où c'est hébergé), et renvoient aux textes applicables sans les citer article par article.

- **Mentions** : le cabinet (identité, agrément), l'hébergeur (Render), le contact.
- **Conditions d'utilisation** : l'objet (outil d'étude et de courtage, gratuit pour l'entreprise), les niveaux
  d'accès, ce que la plateforme ne fait pas (elle ne porte aucun risque, ne reçoit aucune prime, n'engage pas
  l'assureur), la responsabilité des données déposées, la suspension et l'effacement.
- **Confidentialité** : les données traitées (identité du compte, entreprise, fichiers du personnel **sans nom**,
  bénéficiaires en courtage seulement), les finalités, les durées (inscription non confirmée : 30 jours ; dossier de
  prise en charge : 12 mois après paiement ; journal : conservé), les destinataires (le cabinet ; l'assureur sous
  mandat ; Claude seulement avec accord explicite), les droits et à qui les adresser.

La version des conditions est une constante (`CONDITIONS_VERSION`), servie par `/public/cabinet` ; changer le texte
change la version.

## 3. L'acceptation à l'inscription

L'inscription exige `conditions` = la version en vigueur, sinon `conditions_requises` (422). Le compte garde la
version et la date (`utilisateurs.conditions_version`, `conditions_acceptees_le`, migration 0024) ; le profil les
affiche. Les comptes d'avant ne sont pas bloqués (aucun n'est un client réel) ; une version nouvelle se fera
accepter à la connexion dans un lot suivant.

## 4. Le signataire du mandat

Signer, c'est dire en quelle qualité : `representant_legal` (le dirigeant inscrit au RCCM) ou `delegataire` (une
personne qui a reçu pouvoir). Délégataire, il faut le document de délégation, déposé comme justificatif (nature
`delegation`) avant de signer, sinon `delegation_requise` (422). Le mandat garde la qualité et le justificatif
(`mandats_courtage.signataire_qualite`, `delegation_id`, migration 0025) ; le PDF scellé imprime la qualité ; le
conseiller voit la délégation à côté de la signature. Le texte signé (et son empreinte) ne change pas.

## 5. Les avis par courriel

Un événement qui attend quelqu'un l'en prévient par courriel, en français, avec le lien de la page :

| Événement | Destinataires |
|---|---|
| Nouvelle inscription | administrateurs de la plateforme |
| Inscription confirmée / refusée (avec le motif) | administrateurs de l'entreprise |
| Message dans le fil | l'autre côté : les conseillers (à défaut les administrateurs de la plateforme) ou l'entreprise (administrateurs et contributeurs) |
| Accompagnement demandé | conseillers, à défaut administrateurs de la plateforme |
| Mandat proposé | administrateurs de l'entreprise |
| Mandat signé, refusé | conseillers |
| Offre choisie | conseillers |
| Dossier de prise en charge : ouvert / resoumis | conseillers |
| Dossier de prise en charge : réponse du conseiller | administrateurs de l'entreprise |

Règles :

- **Envoyé après la validation** de la transaction : un événement annulé ne prévient personne.
- Un envoi qui échoue est écrit au journal du serveur ; il ne fait jamais échouer l'acte.
- Jamais de donnée du personnel, jamais de montant, jamais de nom de bénéficiaire : « un message vous attend »,
  « le mandat est à signer », et le lien.
- Chacun peut les couper dans son profil (`utilisateurs.avis_courriel`, migration 0026) ; l'auteur de l'acte
  n'est jamais prévenu de son propre acte ; un compte sans adresse n'est pas prévenu.
- Ce sont des avis d'événement. **L'envoi hebdomadaire des alertes reste suspendu** (décision antérieure) ;
  ce lot ne le rouvre pas.

La file des inscriptions dit aussi quand l'entreprise a déjà demandé un accompagnement.

## 6. Exploitation et sécurité

- **En-têtes de sécurité** sur toutes les réponses : CSP (`default-src 'self'`, pas de script tiers, polices
  locales), `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, HSTS en production.
- **Erreur inattendue** : une réponse JSON 500 sans détail interne, avec un numéro d'incident que le journal du
  serveur porte aussi ; si `COURTAGE_ALERTE_URL` est posée, un POST JSON court (numéro, route, type d'erreur)
  part vers elle, au plus un par minute.
- **Sauvegardes** : `deploiement/verifier_sauvegarde.sh` restaure une copie dans une base jetable et y lit les
  contrôles du démarrage et le compte des lignes ; DEPLOY.md dit quand le lancer et quoi lire.
- **Surveillance** : la sonde `/api/v1/sante` (déjà là) suivie par un service externe, et la page d'état qu'il
  publie ; DEPLOY.md dit comment.
- `docs/securite.md` : ce qui est en place, ce qui reste (test d'intrusion externe avant l'ouverture).

## 7. Revu en chemin

- Un dossier de prise en charge **exige déjà** un mandat à la date du départ (`pas_de_mandat`) : rien à ajouter.
- La demande d'accompagnement pendant l'attente reste permise (elle ne fait que dire l'intention).
