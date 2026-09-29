# Clôture du placement — la police, les appels de prime, les virements, les relevés

Date : 2026-09-29. Suite du lot P1. Couvre les étapes 12 (contrat signé) et 13 (financement) de la carte du parcours.

## 0. Le principe : la plateforme trace, elle ne paie pas

Aucun paiement ne passe par la plateforme : ni lien de paiement, ni carte, ni mobile money, ni compte du cabinet.
Les primes se paient **par virement bancaire, sur le compte de l'assureur**, après un appel de prime qui porte ses
coordonnées bancaires. La plateforme range l'appel, montre les coordonnées **à l'écran seulement**, reçoit la
déclaration du virement et la quittance de l'assureur. Elle ne garde jamais l'argent des primes (CLAUDE.md) : une
prime payée par l'intermédiaire du cabinet n'existe pas ici.

## 1. La police

Une **police** est le contrat placé chez l'assureur retenu (table `polices`, sous RLS). Le conseiller la crée, en
principe depuis l'offre choisie (l'assureur en est repris), sinon à la main pour un contrat placé autrement.

Elle avance par des faits, chacun avec sa preuve :

| Étape | Le fait | Qui |
|---|---|---|
| Offre retenue | la police existe (depuis le choix, ou saisie) | conseiller |
| Police reçue | le document de la police est déposé (`police`) ; le numéro est saisi | conseiller |
| Signée | la date de signature est déclarée, la copie signée déposée si on l'a (`police_signee`) | administrateur de l'entreprise ou conseiller |
| Première prime encaissée | l'appel marqué « première prime » est confirmé par la quittance de l'assureur | conseiller |
| **En vigueur** | signée ET première prime encaissée ET date d'effet atteinte | calculé |

Le statut se **calcule** à la lecture ; rien ne se coche à la main. Les avenants (`avenant`) s'ajoutent à la police.

## 2. Les appels de prime

Le conseiller enregistre l'appel reçu de l'assureur : référence, montant, échéance, « première prime » ou non, le
document de l'appel (`appel`), et les **coordonnées bancaires qu'il porte** (banque, titulaire, IBAN ou RIB, BIC).

Un appel est : **à payer** → **payé (déclaré)** → **encaissé (confirmé)**, ou **en retard** si l'échéance passe sans
déclaration.

- **Déclarer le virement** (administrateur ou contributeur de l'entreprise) : date, montant, référence bancaire,
  l'avis de virement si on l'a. Un montant différent de l'appel est un constat, pas un refus.
- **Confirmer l'encaissement** (conseiller) : la quittance ou le relevé de l'assureur, déposé. Sans pièce, pas de
  confirmation.

## 3. Les coordonnées bancaires : contre la fraude au changement de RIB

Le détournement de virement vise précisément ce moment : un « nouveau RIB » envoyé par courriel, et le virement
suivant part ailleurs. D'où quatre règles.

1. **Un registre, tenu par le courtier.** `comptes_assureurs` (plateforme, hors RLS : les assureurs sont les mêmes
   pour tous les clients) : pour chaque assureur, le compte en vigueur. Seul l'administrateur de la plateforme
   l'enregistre, et **chaque enregistrement exige un contre-appel** : qui a été appelé, à quel numéro, quand. Un
   changement ajoute une ligne qui remplace la précédente ; l'ancienne reste, datée.
2. **Chaque appel est confronté au registre.** Même compte : « conforme au registre ». Compte différent :
   **« coordonnées modifiées »**. Assureur sans compte au registre : **« compte non enregistré »**.
3. **Un écart se lève par un contre-appel, jamais par un clic.** Le conseiller rappelle l'assureur au numéro qu'il
   connaît (pas celui de l'appel) et enregistre l'interlocuteur, le numéro, la date. Jusque-là l'écran de l'entreprise
   dit, en rouge : « Ne pas payer : coordonnées bancaires à confirmer par votre conseiller. »
4. **Les coordonnées ne sortent pas de la plateforme.** Aucun courriel, aucun message ne les porte : « un appel de
   prime vous attend », et le lien.

Un virement déclaré sur un appel non confirmé est enregistré (c'est un fait) et signalé au conseiller, en grave.

## 4. Les relevés du fonds

Le conseiller dépose le relevé de l'assureur (`releve`) avec sa date et le **montant du fonds** qu'il affiche. La
page le rapproche des primes encaissées et du fonds retenu par la dernière étude émise : l'écart est un constat.

## 5. Ce que chacun voit, et les avis

- Les alertes du dossier : appel en retard (grave pour l'entreprise), coordonnées à confirmer (grave pour le
  conseiller), virement déclaré à confirmer (attention pour le conseiller), police reçue à signer (attention pour
  l'entreprise).
- Avis par courriel (§5 du lot P1) : appel de prime émis → entreprise ; virement déclaré → conseillers ; encaissement
  confirmé → entreprise ; police reçue → entreprise. Jamais de coordonnées ni de montant dans le courriel.
- Qui peut quoi : le conseiller crée, dépose, confirme ; l'administrateur de l'entreprise déclare la signature et les
  virements, le contributeur les virements ; le lecteur lit. Le registre des comptes : administrateur de la
  plateforme seulement. Sous mandat seulement (capacité `cahier`), comme la consultation.
