# Plan — Essai, inscription, activation, courtage seul

Spécification : `docs/specs/2026-09-28-inscription-et-courtage-seul-design.md`.

1. [ ] **Courtage seul.** Contrat : un seul service à l'écran ; « sans mandat » tant qu'aucun mandat n'est signé ;
   l'orientation vers l'assureur retirée (route, page, guide). Cahier, envoi et réponses : conseiller seulement ;
   choix : administrateur de l'entreprise.
2. [ ] **Activation (socle).** Migration 0023 : `organisations.activation` (`en_attente` | `confirmee` | `refusee`)
   et ses traces (demandée le, décidée le, par, méthode, motif), identité de l'entreprise (RCCM, taille, adresse,
   ville), `justificatifs` (le document RCCM), `utilisateurs.email_verifie_le`, `codes_verification`. Les dossiers
   existants sont `confirmee`. `services/activation.py` : les capacités et `exiger`.
3. [ ] **Contrôles par capacité** sur toutes les routes concernées (tableau de la spécification §2.4), testés un à un.
4. [ ] **Inscription publique.** Codes téléphone et courriel (SMTP ou journal), création utilisateur + dossier +
   adhésion + session, RCCM obligatoire et unique, reprise de l'essai.
5. [ ] **File du courtier.** Liste des inscriptions (âge, échéance à 2 jours ouvrés, retard), confirmer (conseiller
   désigné, vérification tracée) ou refuser (motif) ; dépôt du RCCM par le client ; effacement à 30 jours (tâche
   `purge`) ; suppression par le client.
6. [ ] **Messages.** Fil par dossier, non lus, rail.
7. [ ] **Écran.** Page d'inscription, bandeau d'attente, actions grisées avec leur raison, filigrane et impression
   neutralisée pendant l'attente, file du courtier sur l'accueil de l'administrateur.
8. [ ] **Essai visiteur.** Routes `/essai/*` sans état (fichier, étude), limite de débit, 300 salariés ; page d'essai
   (personnel, fonds, régime, résultat) filigranée, sans impression ; reprise à l'inscription.
9. [ ] Guide, démonstration, captures ; suite complète verte, `tsc` propre.
