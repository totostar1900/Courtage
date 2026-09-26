# Plan — Prestations IFC (spec `2026-09-26-prestations-ifc-design.md`)

TDD, une tâche par commit, tests d'abord.

## P1 — Contrats suivis et service
- [x] Migration 0009 `contrats` (assureur, police, date d'effet, service `courtage|comparaison`, référence du mandat), RLS, SELECT/INSERT seulement pour le rôle applicatif ; un courtage sans assureur ni mandat est refusé (service `mandat_requis`, et contrainte en base).
- [x] `contrats.service_a_la_date(session, jour)` : comparaison par défaut sans contrat.
- [x] `GET /organisations/{id}/contrats` (tous) et `POST` (conseiller) ; écran « Contrat » ; constat `commission_sans_mandat` quand la rémunération prévoit une commission hors courtage.
- [x] Guide : chapitre « Courtage ou comparaison », trois mots au glossaire, une astuce ; la démonstration porte un courtage.
Commit : `feat(contrats): service de courtage ou de comparaison, daté`

## P2 — La prestation anonyme
- [x] Migration 0010 `prestations` (matricule, motif, dates, salaire mensuel de référence, dû recalculé et son calcul, versé, part du fonds demandée / payée et date, soldée, origine, lot d'import), RLS, SELECT/INSERT seulement ; correction = nouvelle ligne `remplace_id` (une seule fois, motivée), annulation idem.
- [x] Dû recalculé avec la règle en vigueur au départ : version adoptée du régime (catégorie, sinon « * »), sinon la convention nommée ou celle de la dernière étude ; hors retraite, 0 et la raison. Constats : versé sous / au-delà du dû, fonds au-delà du demandé ou du versé, matricule encore présent dans un fichier postérieur.
- [x] `POST /prestations` (+ `/apercu`, `/{id}/correction`, `/{id}/annulation`), `GET /prestations` (actives, totaux, service au jour du départ) ; `POST /prestations/import` : aperçu, puis tout ou rien.
- [x] Écran « Départs » (déclarer avec calcul du dû, reprendre l'historique, corriger, annuler) ; chapitre du guide ; la démonstration porte cinq départs.
Commit : `feat(prestations): enregistrer un départ, reprendre l'historique`

## P3 — Courtage : le dossier de prise en charge
- [x] Migration 0011 : `dossiers_prise_en_charge` (un par départ), `dossiers_evenements` (les étapes, des lignes), `beneficiaires` et `pieces_dossier` (les seules tables où le rôle applicatif peut SUPPRIMER) ; préfixe PC- admis par `sceaux`.
- [x] Déclaration DRH (identité + montant ≤ versé) → vérification conseiller (ou « à compléter » motivé → resoumis) → dossier scellé `PC-…` (PDF avec identité rangé dans `pieces_dossier` ; sceau public sans identité) → payé (inscrit sur la prestation par une ligne de correction) | refusé motivé → retransmis. Dates : passées permises, jamais à venir ni avant le départ, réponse après l'envoi.
- [x] Refus hors courtage (`pas_de_mandat`, aucune identité enregistrée) ; retard contre le délai du cahier des charges (30 jours sinon) ; une prestation portée par un dossier ne s'annule pas et garde sa clé.
- [x] Effacement douze mois après le paiement : à chaque lecture, au démarrage, et `python -m courtage.purge` chaque jour ; le numéro se vérifie encore.
- [x] Écran du dossier, « Demander la prise en charge » sur un départ ; guide ; démonstration avec un dossier fictif transmis.
Commit : `feat(prestations): dossier de prise en charge en courtage`

## P4 — Comparaison : l'orientation
- [ ] Écran « Un salarié part » : assureur, police, pièces habituelles, montant dû calculé ; déclaration anonyme facultative de ce que l'assureur a payé.
Commit : `feat(prestations): orientation vers l'assureur en comparaison`

## P5 — Les rapports lisent l'expérience
- [ ] Étude : attendu contre réel par année ; rotation observée proposée ; fonds réduit des paiements.
- [ ] Cahier des charges : historique agrégé (≥ 3 par ligne), délais constatés.
- [ ] Guide : chapitre « Un salarié part », leçon, astuces.
Commit : `feat(rapports): l'expérience réelle des prestations`
