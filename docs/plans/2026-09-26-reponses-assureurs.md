# Plan — Les réponses des assureurs au cahier des charges (placement)

Le cahier des charges (tâche 6) envoie une grille commune aux assureurs. Ce plan
reçoit leurs réponses, les confronte aux conditions demandées, les classe et
laisse l'entreprise choisir.

- [x] Migration 0013 : `reponses_fiche` (la grille remplie, l'offre en PDF facultative, date de réception ; une écriture : correction et retrait par une ligne `remplace_id`) et `choix_fiche` (un par cahier). RLS ; SELECT/INSERT seulement.
- [x] Conformité critère par critère contre `fiches_regime.conditions` : conforme, en écart (demandé / offert), ou non renseigné — qui n'est pas « conforme ». Réponse tardive signalée ; une date à venir ou antérieure au cahier refusée ; un assureur, une réponse active.
- [x] Classement par le coût net actualisé du scénario central (`services/financement`, provision interne en référence) ; la RECOMMANDÉE est la moins chère des conformes.
- [x] Choix par l'entreprise seule (`admin_client`), motivé s'il ne se porte pas sur la recommandée ; un cahier attribué est clos. Le conseiller enregistre ensuite le contrat (lien prérempli).
- [x] Écran « Réponses des assureurs » (cartes classées, écarts, saisie et correction de la grille, retrait, choix) ; guide ; démonstration avec trois réponses fictives.

Commit : `feat(placement): réponses des assureurs, conformité, classement, choix`
