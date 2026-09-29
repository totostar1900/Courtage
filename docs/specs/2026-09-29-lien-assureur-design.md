# Le lien assureur — consulter depuis la plateforme, recevoir l'offre par un lien

Date : 2026-09-29. Couvre les étapes 9 (cahier des charges) et 10 (offres des assureurs) de la carte du parcours.

## 1. Pourquoi

Aujourd'hui le cahier part par courriel, hors de la plateforme, et chaque offre revient au conseiller qui la
ressaisit. Deux manques : on ne peut pas prouver **qui a été consulté, quand**, ce qui fonde une mise en concurrence
loyale ; et la ressaisie des taux et des frais est une source d'erreurs.

## 2. Consulter

Sur un cahier émis et ouvert (date limite non passée, aucune offre choisie), le conseiller ajoute un assureur : son
nom, un contact, une adresse électronique. La plateforme :

- crée la **consultation** (qui, quand, par qui) et un **lien personnel** — un jeton aléatoire, gardé seulement sous
  forme d'empreinte, valable jusqu'à la date limite de réponse ;
- envoie le courriel à l'adresse donnée, en français : le cabinet consulte pour le compte d'un client, le numéro du
  cahier, la date limite, le lien. Le lien n'est écrit nulle part ailleurs.

Un assureur, une consultation active par cahier. **Relancer** émet un lien neuf (l'ancien cesse de valoir) et renvoie
le courriel ; **annuler** ferme le lien. La page du cahier montre, pour chaque assureur : envoyé le, ouvert le,
répondu le, relances, et l'état.

## 3. Répondre, sans compte

`/offre/<jeton>` est une page publique, comme `/verifier`. L'assureur y lit qui le consulte, le numéro du cahier, la
date limite et **les conditions du cahier** ; il télécharge le cahier scellé (sans nom de salarié) ; il remplit la
grille — les mêmes champs que la saisie du conseiller — et joint son offre en PDF (obligatoire : c'est la pièce qui
engage l'assureur).

- La réponse entre dans les réponses du cahier comme une autre : **confrontée aux conditions, classée**, marquée
  « déposée par l'assureur » (`reponses_fiche.consultation_id` ; `saisie_par` vide). Le conseiller la relit, la
  corrige ou la retire par les mêmes gestes qu'aujourd'hui, avec motif.
- Une seule réponse par lien ; ensuite la page dit « réponse reçue le … ». Une réponse déjà saisie par le conseiller
  pour cet assureur l'emporte (`reponse_existante`).
- Après la date limite, ou le cahier attribué, ou la consultation annulée, le lien répond « consultation close ».
- Limité en fréquence ; aucune donnée du client au-delà de ce que le cahier montre déjà ; le jeton n'est jamais
  journalisé.

## 4. Traces et avis

Journal : consultation envoyée, relancée, annulée, ouverte, réponse déposée (sans utilisateur pour l'assureur). Avis
par courriel aux conseillers quand une offre arrive. L'entreprise voit, sur la page du cahier, qui a été consulté.

## 5. Données

Migration 0028 : `consultations_assureurs` (sous RLS) ; `liens_assureurs` (empreinte du jeton → consultation et
organisation ; hors RLS, lu avant qu'une organisation soit connue, comme `adhesions`) ; `reponses_fiche` gagne
`consultation_id` et `saisie_par` devient facultatif quand une consultation le remplace.
