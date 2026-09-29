# Cahier du test d'intrusion externe

À remettre au prestataire retenu. Le test est confié à un **prestataire indépendant** : il ne se fait pas ici, et un
test écrit par l'équipe qui a construit la plateforme n'en tient pas lieu. Ce cahier dit ce qu'on attend de lui, ce
qu'il peut toucher et ce qu'il ne doit pas toucher. Il s'accompagne de `docs/securite.md` (ce qui est en place).

## 1. La plateforme en une page

- Une plateforme de **courtage d'assurance** des indemnités de fin de carrière (IFC), pour des entreprises de la zone
  CEMAC. Elle chiffre l'engagement, met les assureurs en concurrence, suit la police et les prises en charge.
  **Elle ne fait circuler aucun argent** : elle enregistre des instructions et des déclarations de virement.
- Une seule application : une API FastAPI (`/api/v1/…`) qui sert aussi l'interface React construite ; PostgreSQL
  avec sécurité au niveau des lignes (RLS) par dossier d'entreprise ; hébergée sur Render.
- Données sensibles : le fichier du personnel d'une entreprise (sans nom de salarié : matricule, dates, salaires) ;
  l'identité d'un bénéficiaire en prise en charge ; les coordonnées bancaires des assureurs (registre des comptes) ;
  des documents scellés.

## 2. Périmètre

| | Dans le périmètre |
|---|---|
| Environnement | la **recette** (`COURTAGE_ENV=recette`), une copie de la production sans donnée réelle, à une adresse communiquée à part |
| Application | toute l'API `/api/v1/…`, l'interface, `/robots.txt`, `/sitemap.xml`, la page de vérification `/verifier/<n°>` |
| Authentification | la connexion par code (SMS/WhatsApp), l'inscription par deux codes, la session par cookie, le jeton porteur |
| Séparation | un dossier d'entreprise ne doit rien laisser voir d'un autre ; un rôle ne doit pas faire ce que sa ligne de droits refuse |
| Liens publics | le lien d'un assureur consulté (`/offre/<jeton>`), le numéro d'un document scellé |
| Téléversements | fichier du personnel (XLSX/CSV), pièces (PDF, JPEG, PNG, 10 Mo), polices |
| Navigateur | CSP, cadres, cookies, en-têtes |

**Hors périmètre** : l'hébergeur (Render) et son infrastructure ; les fournisseurs (Twilio, SMTP, Anthropic) ; le
déni de service et les tests de charge ; l'ingénierie sociale envers le cabinet, les clients ou les assureurs ; la
production.

## 3. Comptes fournis

Un compte par rôle, sur deux dossiers d'entreprise distincts (A et B), pour éprouver la séparation dans les deux sens :

| Rôle | Ce qu'il peut | Dossier |
|---|---|---|
| Administrateur de la plateforme (le courtier) | tout, sur tous les dossiers | — |
| Conseiller | les dossiers qu'il suit | A |
| Administrateur de l'entreprise | tout son dossier | A, et un autre sur B |
| Contributeur | déposer, préparer ; ni émettre, ni signer | A |
| Lecteur | lire | A |
| Sans dossier | rien (un compte inscrit, non rattaché) | — |

En recette, les codes de connexion s'écrivent dans le journal au lieu de partir (DEPLOY.md §1) : le cabinet les
transmet au testeur, ou lui ouvre la lecture du journal. Un lien d'assureur valide et le numéro d'un document scellé
sont fournis aussi.

## 4. Règles d'engagement

- Fenêtre convenue par écrit, dates et heures ; un contact joignable côté cabinet pendant toute la fenêtre.
- Adresses IP sources communiquées à l'avance. Les limites de fréquence s'appliquent : le testeur peut demander
  qu'elles soient relevées pour ses adresses, et doit dire s'il l'obtient (un contournement de limite est un résultat).
- Pas d'effacement volontaire de données au-delà de ses propres comptes ; pas de persistance laissée derrière soi.
- Une faille critique (accès aux données d'un autre dossier, prise de compte, exécution de code) est signalée **le
  jour même**, sans attendre le rapport.
- Rien de ce qui est trouvé n'est publié ni réutilisé hors de la mission.

## 5. Ce qu'on attend en particulier

Les points qu'on sait les plus exposés, à éprouver en priorité :

1. **La séparation des dossiers** : identifiants d'un autre dossier dans l'URL, dans le corps, dans un fichier
   téléversé ; un dossier retiré, archivé, supprimé ; un membre retiré dont la session est encore ouverte.
2. **L'authentification** : devinette et rejeu du code, énumération des numéros, fixation et vol de session,
   CSRF sur les écritures par cookie, jeton porteur.
3. **Les liens publics** : devinette du jeton d'un assureur, lecture d'un cahier après la clôture, dépôt d'une offre
   sur une consultation d'un autre dossier ; énumération des numéros de documents scellés.
4. **Les téléversements** : type annoncé contre contenu, fichiers piégés (XLSX avec formules, PDF actif, polyglottes),
   taille, noms de fichiers.
5. **Le registre des comptes des assureurs** : peut-on faire afficher à un client des coordonnées bancaires qui ne
   sont pas celles confirmées (fraude au changement de RIB) ?
6. **Les rôles** : un contributeur qui émet, un lecteur qui écrit, un administrateur d'entreprise qui se donne des
   droits de conseiller.

## 6. Ce que l'équipe vérifie déjà elle-même

Pour que le testeur ne passe pas son temps sur ce qui est déjà prouvé, et qu'il cherche au-delà — ce que ces tests
affirment n'est pas une preuve que la plateforme est sûre, seulement que ces contrôles tiennent.

`api/tests/test_isolation.py`, sur **toutes** les routes lues dans l'application (une route ajoutée demain y entre
seule) :
- chaque route d'un dossier refuse une personne étrangère au dossier (403/404, avant même la lecture du corps) ;
- aucune route ne répond sans connexion, hors une liste publique déclarée et commentée ;
- chaque route publique qui écrit, ou qui devine un jeton ou un numéro, est limitée en fréquence par adresse ;
- chaque écriture par cookie exige l'en-tête anti-CSRF ;
- une route publique ne rend rien d'un dossier ; un jeton deviné reçoit la même réponse qu'il existe ou non.

Et, ailleurs dans la suite : la RLS vérifiée au démarrage, le journal et les sceaux en ajout seul, la CSP.

L'audit des dépendances (`pip-audit`, `npm audit`) est fait avant le test : aucune vulnérabilité connue au
2026-09-29.

## 7. Ce qu'on attend en retour

- Un rapport en français : résumé pour la direction, puis chaque constat avec sa gravité (CVSS), sa reproduction pas
  à pas, sa preuve et une recommandation.
- Les constats critiques et élevés signalés le jour même (§4).
- Une **contre-vérification** après correction, comprise dans la mission.
- Une attestation datée, à conserver par le cabinet.

Chaque constat corrigé entre dans la suite de tests quand il peut s'y écrire, pour qu'il ne revienne pas.
