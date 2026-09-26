# Décisions

Registre des décisions de produit. Une décision change par une nouvelle ligne,
jamais en réécrivant l'ancienne.

| Date | Décision | Conséquence |
|---|---|---|
| 2026-09-26 | Dépôt dédié `courtage`, repartir de zéro (aucun code repris de MyChama) | pile propre au produit |
| 2026-09-26 | Pile : Python (FastAPI, SQLAlchemy, PostgreSQL) + React/TypeScript | moteur actuariel lisible par un actuaire |
| 2026-09-26 | Premier produit : l'étude IFC en ligne | vendable avant l'agrément |
| 2026-09-26 | Demander l'agrément de courtier (MINFI) ; vendre du conseil en honoraires pendant l'instruction | le produit doit pouvoir facturer des honoraires dès la première étude |
| 2026-09-26 | Rémunération : modèle mixte paramétrable (honoraires client et/ou commission assureur publiée, par client) | la tarification est une donnée par organisation, pas une constante |
| 2026-09-26 | Premier produit d'entreprise : IFC, santé groupe ensuite | ordre des spécifications |
| 2026-09-26 | La diaspora est ciblée dès la première année | parcours particulier en ligne, paiement hors zone à prévoir |
| 2026-09-26 | Nom et marque : plus tard | nom de travail `courtage` |
| 2026-09-26 | Barèmes camerounais depuis des sources en ligne, et non le barème ivoirien (écart de 67 % mesuré) | voir spec §10.1 |
| 2026-09-26 | Au contrat IFC, souscripteur, assuré et bénéficiaire = l'entreprise ; le salarié est créancier de l'employeur | aucune identité de salarié avant un sinistre (spec §2.9) |
| 2026-09-26 | Barème d'entreprise quand l'entreprise verse plus que sa convention | l'obligation implicite est évaluée (spec §7 bis) |
| 2026-09-26 | La « convention » construite par le souscripteur est son régime IFC ; la convention collective en est le plancher | spec régime IFC §1 |
| 2026-09-26 | L'entreprise adopte son régime d'un seul acte ; pas d'approbation interne à plusieurs signataires | spec régime IFC §1.3 |
| 2026-09-26 | Catégories de personnel dès la première version du régime | colonne catégorie dans le fichier |
| 2026-09-26 | Pas de juriste partenaire pour l'instant : le contenu juridique reste `a_valider` et sourcé | la plateforme informe, elle ne donne pas d'avis juridique |
| 2026-09-26 | Valeur propre de l'assureur : rendement, sinistres (et, aujourd'hui, actuariat et reporting) ; la plateforme accompagne tout le processus IFC et prend les régimes existants tels quels | spec régime IFC §2 |
| 2026-09-26 | Connexion par code reçu au téléphone, intégrée (pas de service géré) ; fournisseur d'envoi interchangeable | WhatsApp/SMS au Cameroun ; identité dans notre base |
