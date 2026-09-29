# Sécurité — ce qui est en place, ce qui reste

Tenu à jour avec le code. Dernière revue : 2026-09-29 (lot P1, `docs/specs/2026-09-29-plateforme-ouverte-p1-design.md`).

## En place

**Identité et sessions**
- Connexion par code à usage unique (SMS ou WhatsApp) ; inscription par deux codes (téléphone, courriel). Codes gardés
  en HMAC, jamais en clair ; 10 minutes, 5 essais, demandes limitées par numéro et par adresse IP.
- Session par cookie `HttpOnly`, `SameSite=Lax`, `Secure` en production et en recette ; révocable appareil par
  appareil depuis le profil. Jetons gardés sous forme d'empreinte.
- Toute écriture par cookie exige l'en-tête `X-Courtage: 1` (protection CSRF). L'identité par en-tête de
  développement est refusée au démarrage en production, comme l'absence de clé ou de fournisseur d'envoi.
- Une réponse ne varie pas selon qu'un numéro est connu ou non.

**Séparation des données**
- Chaque table d'une entreprise est sous RLS PostgreSQL (`organisation_courante()`) ; le rôle applicatif ne possède
  aucune table et n'est pas exempté de RLS. Le démarrage lit ces conditions dans la base et s'arrête sur un FAIL.
- Droits par rôle déclarés sur chaque route (`acces(...)`) ; l'interface ne cache un bouton que pour la clarté.
- Ce qui sort de la plateforme attend la confirmation de l'inscription ; ce qui touche aux assureurs, un mandat signé.

**Intégrité**
- Journal, sceaux et catalogue en ajout seul pour le rôle applicatif ; études émises, versions adoptées, mandats
  signés immuables par déclencheurs.
- Documents scellés (HMAC sous `COURTAGE_CLE_SCEAU`), vérifiables publiquement par leur numéro.

**Données personnelles**
- Aucun nom de salarié lu ni gardé ; l'identité d'un bénéficiaire n'existe qu'en courtage, effacée douze mois après le
  paiement ; inscription non confirmée effacée à 30 jours.
- Lecture d'un texte par Claude seulement avec l'accord explicite de la personne, le document non gardé.
- Avis par courriel sans contenu du dossier : le lien seulement.

**Transport et navigateur** (`api/securite.py`)
- CSP stricte (`script-src 'self'`, aucune ressource tierce, polices servies par la plateforme), `frame-ancestors
  'none'`, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, COOP ; HSTS en production.
  Vérifiée dans un navigateur sur la vitrine, l'essai, l'inscription, la connexion, le guide et les pages légales :
  aucune violation.
- Pièces déposées limitées à PDF, JPEG, PNG et 10 Mo, servies avec leur type et `nosniff`.

**Exploitation**
- Erreur inattendue : 500 sans détail interne, numéro d'incident au journal, alerte limitée (`COURTAGE_ALERTE_URL`).
- Sonde `/api/v1/sante` (base joignable et schéma à jour) ; sauvegardes prouvées par restauration
  (`deploiement/verifier_sauvegarde.sh`, DEPLOY.md §7).

## Reste à faire

| | Pourquoi | Quand |
|---|---|---|
| **Test d'intrusion externe** | un regard indépendant sur l'authentification, la séparation des dossiers et les téléversements | avant l'ouverture au public |
| Limites de fréquence partagées | elles vivent en mémoire, par processus : à plusieurs instances, chacune compte seule | avant de passer à plus d'une instance |
| Analyse des dépendances en continu | `pip-audit` et `npm audit` dans l'intégration continue, alerte sur une faille connue | P2 |
| Rotation des clés, écrite | `COURTAGE_CLE_AUTH` se change sans perte ; `COURTAGE_CLE_SCEAU` jamais : écrire qui la détient et où | P2 |
| Revue des accès du cabinet | qui est administrateur de la plateforme, qui est conseiller de quoi, une fois par trimestre | P2 |
| Analyse antivirus des pièces | les pièces sont servies telles quelles à d'autres personnes | P2 |
| Registre des traitements | la liste des traitements de données personnelles, tenue par le cabinet | avant l'ouverture au public |
| Nouvelles conditions à la connexion | une version nouvelle des conditions se fait accepter à la connexion (aujourd'hui : à l'inscription seulement) | à la première révision du texte |
