# Plan — Le site public

Spécification : `docs/specs/2026-09-29-site-public-design.md`.

1. [x] **Être trouvé.** En-tête HTML (description, Open Graph, image, icône, `<noscript>`), titre par page publique,
   `/robots.txt` et `/sitemap.xml` servis par l'API. — *Le site se laisse trouver et partager*
2. [x] **Être rappelé.** Migration 0030 `demandes_rappel` ; `POST /public/rappel` (limité, champ piège) ; la liste et
   le suivi du courtier ; avis ; effacement à douze mois ; confidentialité (nouvelle version). — *Les demandes de
   rappel*
3. [ ] **Écrans.** Le formulaire sur la vitrine ; la liste sur l'accueil du courtier. — *Être rappelé, depuis la
   vitrine*
4. [ ] Guide, CLAUDE.md, DEPLOY.md ; suites vertes, `tsc` propre.
