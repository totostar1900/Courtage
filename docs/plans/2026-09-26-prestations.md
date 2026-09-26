# Plan — Prestations IFC (spec `2026-09-26-prestations-ifc-design.md`)

TDD, une tâche par commit, tests d'abord.

## P1 — Contrats suivis et service
- [x] Migration 0009 `contrats` (assureur, police, date d'effet, service `courtage|comparaison`, référence du mandat), RLS, SELECT/INSERT seulement pour le rôle applicatif ; un courtage sans assureur ni mandat est refusé (service `mandat_requis`, et contrainte en base).
- [x] `contrats.service_a_la_date(session, jour)` : comparaison par défaut sans contrat.
- [x] `GET /organisations/{id}/contrats` (tous) et `POST` (conseiller) ; écran « Contrat » ; constat `commission_sans_mandat` quand la rémunération prévoit une commission hors courtage.
- [x] Guide : chapitre « Courtage ou comparaison », trois mots au glossaire, une astuce ; la démonstration porte un courtage.
Commit : `feat(contrats): service de courtage ou de comparaison, daté`

## P2 — La prestation anonyme
- [ ] Migration 0010 `prestations` (matricule, départ, motif, ancienneté, salaire, dû recalculé, versé, part fonds demandée/payée, état), écritures seulement, annulation par ligne.
- [ ] Dû recalculé avec le régime en vigueur au départ ; écart signalé.
- [ ] Saisie une à une, et import d'un tableur (contrôles bloquants / avertissements).
Commit : `feat(prestations): enregistrer un départ, reprendre l'historique`

## P3 — Courtage : le dossier de prise en charge
- [ ] Migration 0011 `beneficiaires` (table à part, RLS, effacement programmé) et pièces jointes.
- [ ] Déclaration DRH → vérification conseiller → dossier scellé `PC-…` → suivi transmise / payée / refusée ; retard contre le délai du cahier des charges.
- [ ] Refus de collecter une identité hors courtage (service lu à la date du départ).
Commit : `feat(prestations): dossier de prise en charge en courtage`

## P4 — Comparaison : l'orientation
- [ ] Écran « Un salarié part » : assureur, police, pièces habituelles, montant dû calculé ; déclaration anonyme facultative de ce que l'assureur a payé.
Commit : `feat(prestations): orientation vers l'assureur en comparaison`

## P5 — Les rapports lisent l'expérience
- [ ] Étude : attendu contre réel par année ; rotation observée proposée ; fonds réduit des paiements.
- [ ] Cahier des charges : historique agrégé (≥ 3 par ligne), délais constatés.
- [ ] Guide : chapitre « Un salarié part », leçon, astuces.
Commit : `feat(rapports): l'expérience réelle des prestations`
