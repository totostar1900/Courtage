# Plan — Clôture du placement

Spécification : `docs/specs/2026-09-29-cloture-du-placement-design.md`.

1. [x] **Socle.** Migration 0027 : `comptes_assureurs` (plateforme), `polices`, `pieces_police`, `appels_prime`
   (sous RLS) ; modèles ; contrôles du démarrage. — *Socle du placement : polices, appels, registre des comptes*
2. [x] **Registre des comptes d'assureurs.** Enregistrer (contre-appel exigé), remplacer, lire ; administrateur de la
   plateforme. — *Le registre des comptes bancaires des assureurs*
3. [x] **La police.** Création depuis le choix ou à la main, pièces, signature, statut calculé jusqu'à « en
   vigueur ». — *La police, de l'offre retenue à la mise en vigueur*
4. [x] **Les appels de prime.** Enregistrer avec confrontation au registre, contre-appel, déclaration du virement,
   confirmation par quittance ; retards ; alertes et avis. — *Appels de prime et virements déclarés*
5. [x] **Les relevés du fonds.** Dépôt avec montant, rapprochement avec les primes et l'étude. — *Relevés du fonds*
6. [x] **Écrans.** Page « Placement » (police, appels, relevés), registre sur l'accueil du courtier, rail. —
   *L'écran du placement*
7. [ ] Guide, démonstration, CLAUDE.md, carte du parcours ; suites vertes, `tsc` propre.
