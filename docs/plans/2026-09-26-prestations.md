# Plan — Prestations IFC (spec `2026-09-26-prestations-ifc-design.md`)

TDD, une tâche par commit, tests d'abord.

## P1 — Contrats suivis et service
- [ ] Migration 0009 `contrats` (assureur, police, date d'effet, service `courtage|comparaison`, référence du mandat), RLS, versions datées.
- [ ] `service_a_la_date(organisation, jour)` : comparaison par défaut sans contrat.
- [ ] Routes `GET/POST /organisations/{id}/contrats` (conseiller) ; écran « Contrat » ; signal commission sans courtage.
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
