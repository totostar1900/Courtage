# Plan — Contenus, mesure, portefeuille, WhatsApp, test d'intrusion

Spécification : `docs/specs/2026-09-29-contenu-mesure-portefeuille-whatsapp-design.md`.

1. [x] **Pages de contenu.** `/ifc` et `/ifc/cameroun` (barèmes lus dans le référentiel) ; plan du site, titres, liens.
   — *Deux pages de contenu : les IFC, et les IFC au Cameroun*
2. [ ] **Mesure d'audience.** Migration 0031 `mesures` ; `POST /public/mesure` (liste fermée, limité) ; événements
   serveur ; `GET /mesures` ; Do Not Track respecté ; l'entonnoir sur l'accueil du courtier ; confidentialité. —
   *Une mesure d'audience sans témoin*
3. [ ] **Portefeuille.** `services/portefeuille.py`, `GET /portefeuille`, page `/portefeuille`. — *Le pipeline et le
   portefeuille du courtier*
4. [ ] **WhatsApp.** Migration 0032 `avis_whatsapp` ; envoi par modèle Twilio ; le profil. — *Les avis sur WhatsApp*
5. [ ] **Test d'intrusion.** Le cahier ; les contrôles d'isolement, CSRF et fréquence en tests ; l'audit des
   dépendances. — *Préparer le test d'intrusion*
6. [ ] Guide, démonstration, CLAUDE.md, DEPLOY.md ; suites vertes, `tsc` propre.
