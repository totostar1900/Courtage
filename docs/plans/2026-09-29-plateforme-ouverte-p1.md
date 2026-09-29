# Plan — Plateforme ouverte, lot P1

Spécification : `docs/specs/2026-09-29-plateforme-ouverte-p1-design.md`.

1. [x] **Vitrine et pages légales.** `GET /public/cabinet` (identité du cabinet, contact, version des conditions) ;
   `/` = vitrine sans session, accueil avec ; `/mentions-legales`, `/conditions`, `/confidentialite` ; pied de page
   commun. — *Vitrine publique et pages légales*
2. [x] **Acceptation des conditions.** Migration 0024 ; l'inscription exige la version en vigueur ; case à cocher sur
   le formulaire ; le profil l'affiche. — *Les conditions s'acceptent à l'inscription*
3. [ ] **Qualité du signataire.** Migration 0025 ; justificatif `delegation` ; signature avec qualité, délégation
   exigée du délégataire ; PDF et écran du conseiller. — *Le mandat dit en quelle qualité il est signé*
4. [ ] **Avis par courriel.** Migration 0026 ; `services/avis.py`, envoi après validation ; les événements du tableau
   §5 ; coupure dans le profil ; la file dit « accompagnement demandé ». — *Les événements préviennent par courriel*
5. [ ] **Exploitation et sécurité.** En-têtes, erreur 500 numérotée et alerte, vérification des sauvegardes,
   DEPLOY.md, `docs/securite.md`. — *En-têtes de sécurité, incidents, sauvegardes vérifiées*
6. [ ] Guide, démonstration, CLAUDE.md, carte du parcours ; suite complète verte, `tsc` propre.
