# Essai, inscription, activation — et le courtage seul

Date : 2026-09-28. Décisions prises avec le propriétaire du produit le même jour.

## 1. Pourquoi

Une entreprise doit voir ses chiffres avant de rien confier. Puis s'inscrire seule, sans attendre qu'on lui ouvre un
dossier. Puis être vérifiée par un humain avant que quoi que ce soit ne quitte la plateforme en son nom. Et la
plateforme ne fait plus qu'un métier : le **courtage**. La comparaison, où l'entreprise traitait seule avec son
assureur, disparaît.

## 2. Quatre temps

| Temps | Qui | Ce qui est gardé |
|---|---|---|
| **Visiteur** | anonyme | rien sur le serveur ; la saisie vit dans le navigateur |
| **En attente** | téléphone et courriel vérifiés, entreprise déclarée | le dossier, effacé à 30 jours s'il n'est pas confirmé |
| **Confirmé** | le courtier a vérifié l'entreprise | tout |
| **Sous mandat** | le mandat de courtage est signé | tout, et le travail avec les assureurs |

### 2.1 Le visiteur (essai)

- Personnel (fichier Excel/CSV, **300 salariés au plus**), fonds constitué, régime (convention collective, modèle
  type, ou barème saisi), puis l'étude **à l'écran** : chiffres clés, échéancier, sensibilité principale.
- **Rien n'est gardé** : les routes `/essai/*` calculent et répondent, sans écriture en base ni contenu du fichier dans
  les journaux. Un test le vérifie (aucune ligne créée dans aucune table).
- **Rien ne sort** : pas de PDF, pas d'Excel ; l'impression du navigateur est neutralisée (`@media print`) ; l'écran
  porte le filigrane « Estimation — sans valeur probante, non scellée ».
- Pas de catalogue anonyme, pas de simulations comparées, pas d'expérience réelle.
- Limite de débit par adresse IP (le calcul est coûteux et public).
- La saisie est gardée dans le navigateur (`sessionStorage`) ; « Enregistrer mes résultats » mène à l'inscription et
  la reprend.

### 2.2 L'inscription

1. Téléphone : code à 6 chiffres (SMS/WhatsApp, fournisseur actuel). Courriel : code à 6 chiffres (SMTP, par
   `COURTAGE_SMTP_URL` ; en développement, écrit au journal). Mêmes règles que la connexion : 10 minutes, 5 essais,
   3 demandes par quart d'heure, stockés en HMAC.
2. La personne : nom, fonction. L'entreprise : raison sociale, pays, **numéro RCCM (obligatoire)**, taille (tranche
   d'effectif), secteur, adresse, ville. Le **document RCCM est facultatif** à cette étape.
3. Un numéro RCCM déjà inscrit ne crée pas de second dossier : `entreprise_deja_inscrite` ; l'intéressé s'adresse à
   l'administrateur existant ou à son conseiller. La comparaison se fait sur le numéro normalisé (majuscules, sans
   espaces ni séparateurs), pas sur un format : les registres diffèrent.
4. Un téléphone déjà inscrit se connecte, il ne se réinscrit pas.
5. À la création : utilisateur (téléphone et courriel vérifiés), dossier `en_attente`, adhésion `admin_client`,
   session ouverte ; la saisie de l'essai, si elle est jointe, devient le premier fichier du personnel et une
   version de régime en analyse.

### 2.3 L'attente et l'activation

- Le client voit « Inscription en attente de confirmation — votre conseiller vous contacte sous **2 jours ouvrés** »,
  et peut déposer son RCCM.
- Le courtier (administrateur de la plateforme) voit la **file des inscriptions**, la plus ancienne d'abord, avec
  l'échéance (2 jours ouvrés, samedi et dimanche exclus) et le retard en rouge.
- Il **confirme** (document reçu, appel passé, notes, conseiller désigné) ou **refuse** (motif lisible par le
  client). La décision est tracée : qui, quand, comment, ce qui a été vérifié.
- Une inscription non confirmée depuis **30 jours** est effacée, avec son contenu. Le client peut aussi supprimer
  lui-même son inscription tant qu'elle attend.

### 2.4 Ce que chaque temps permet

Le tableau de décision du 2026-09-28 fait foi. En bref :

- **En attente** : tout le travail — personnel, régime (y compris adopter), simulations, études à l'écran
  (hypothèses, sensibilités, expérience réelle), financement, départs, demande d'accompagnement, messages au
  conseiller, suppression de l'inscription.
- **Après confirmation** : ce qui sort de la plateforme ou engage l'entreprise — rapports scellés et leur émission,
  exports Excel d'études, notes de régime, fiches de calcul, invitation de collègues et droits, catalogue anonyme
  (consultation et partage), lecture de textes par Claude, proposition et signature du mandat.
- **Sous mandat** : cahier des charges (rédigé et envoyé par le courtier), réponses des assureurs, comparaison,
  choix, dossiers de prise en charge.

Le contrôle est côté serveur (`services/activation.py`, `exiger(org, capacite)`), jamais seulement à l'écran ; l'écran
grise l'action et dit pourquoi.

### 2.5 Les messages

Un fil par dossier entre l'entreprise et son conseiller (le courtier tant qu'aucun conseiller n'est désigné) : texte,
date, auteur. Ouvert dès l'inscription. Le rail le montre avec le nombre de messages non lus.

## 3. Le courtage seul

- Plus de service « comparaison » à l'écran ; l'orientation vers l'assureur (fiche « adressez-vous à votre
  assureur ») disparaît. Les données déjà enregistrées gardent leur valeur (`comparaison` reste lisible dans
  l'historique), rien n'est réécrit.
- Sans mandat, un dossier est « sans mandat » ; le contrat de courtage naît de la signature du mandat.
- Le cahier des charges, son envoi, la saisie des réponses sont l'œuvre du **conseiller** ; l'entreprise lit,
  compare et choisit (motivé si ce n'est pas la recommandée).

## 4. Ce qui ne change pas

Le sceau, la vérification publique, l'immuabilité des études émises et des mandats signés, la RLS par organisation,
le rôle applicatif qui ne possède rien.
