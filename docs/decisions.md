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
| 2026-09-26 | Une image, une origine : l'API sert l'interface ; la base est PROUVÉE au démarrage (sept contrôles), pas supposée | un « migrations appliquées » ne dit rien de l'état réel ; un cookie sur un seul domaine |
| 2026-09-26 | Deux services : courtage (la plateforme porte les prestations) et comparaison (le client traite avec son assureur) ; le service est daté, sur un contrat suivi | qui collecte une identité dépend du mandat, pas de la rémunération |
| 2026-09-26 | Dossier de prise en charge en courtage : identité dans une table à part, effacée 12 mois après le paiement ; sceau public sans identité | le numéro reste vérifiable après l'effacement ; hors courtage, aucune identité n'est jamais recueillie |
| 2026-09-26 | L'expérience réelle entre dans l'étude (scellée) et le cahier des charges ; une rotation observée est proposée, jamais appliquée d'office | peu de départs ne prouvent rien (5 au moins) ; changer une hypothèse reste une décision justifiée |
| 2026-09-26 | Réponses des assureurs : confrontées aux conditions du cahier, classées par coût net actualisé ; la recommandée est la moins chère des conformes ; l'entreprise choisit, et motive un autre choix | la plateforme éclaire, elle ne décide pas ; une offre moins chère qui retient le client (pénalité, préavis) n'est pas recommandée |
| 2026-09-26 | Extraction assistée des textes existants : la plateforme propose, chaque valeur cite son passage, vérifié dans le texte ; CEMAC seulement ; un envoi à un tiers (Claude) exige l'accord de la personne ; seule l'empreinte du document est gardée | lire un accord sans le ressaisir, sans jamais laisser une valeur non sourcée entrer dans un régime |
| 2026-09-26 | Hébergement Render (Francfort) par un plan versionné, domaine courtage.purposecapital.africa ; démarrage en recette jusqu'au branchement de Twilio | la région la plus proche de l'Afrique centrale chez Render ; rien de saisi à la main hormis les secrets tiers |
| 2026-09-26 | Consulter des régimes en trois étapes : modèles types calculés, puis catalogue anonyme volontaire, puis comparaison chiffrée après avis juridique | commencer sans aucune donnée d'entreprise ; l'échange d'informations de rémunération entre concurrents doit être vérifié avant les percentiles |
| 2026-09-26 | Catalogue anonyme : photographie publique sans organisation ; groupes d'au moins 5 entreprises distinctes, découpés CEMAC → pays → secteur → taille seulement si tous les sous-groupes atteignent 5 ; partage par la DRH d'une version adoptée, un seul actif, retirable | dans un petit marché, retirer le nom ne suffit pas ; masquer l'attribut d'une seule entrée la désignerait par soustraction |
| 2026-09-27 | La rémunération du courtier quitte la plateforme : ni conditions, ni honoraires sur les études, ni motif d'émission | la plateforme aide à souscrire un service IFC ; ce que facture le courtier relève de son mandat, pas d'un calcul de la plateforme |
| 2026-09-27 | Une étude émise se supprime, par l'administrateur ou le conseiller, sur confirmation écrite (« SUPPRIMER »), si aucun cahier ne la cite ; son sceau reste | l'espace se libère sans qu'un clic distrait efface un document ; un numéro émis se vérifie toujours |
| 2026-09-27 | Le mandat de courtage se demande, se propose et se signe sur la plateforme ; le texte est construit une fois pour l'écran et le PDF, la signature porte sur son empreinte ; signé, il est scellé (MC-) et ouvre le contrat « courtage » à sa date | le client signe exactement ce qu'il a lu ; un courtage n'exige plus d'assureur, le mandat précède le placement |
| 2026-09-28 | Le mandat est gratuit pour le client : le courtier est rémunéré exclusivement par la commission de l'assureur retenu (texte `mandat-courtage-2`) | pour l'instant ; un accompagnement sans frais lève le premier frein, la commission reste communicable sur demande |
