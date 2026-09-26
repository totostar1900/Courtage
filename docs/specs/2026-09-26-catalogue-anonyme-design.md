# Catalogue anonyme des régimes — conception

Statut : réalisée (26/09/2026). Deuxième étape de « consulter des régimes pour s'inspirer et se comparer »
(la première : les modèles types ; la troisième : la comparaison chiffrée, après avis juridique).

## Le besoin

Une entreprise qui écrit son régime veut voir ce que font les autres ; une entreprise établie veut savoir où
elle se situe. Les régimes réels des clients répondent mieux que des modèles calculés — à condition que
personne ne puisse reconnaître l'entreprise derrière un barème.

## Le risque : un petit marché

Retirer le nom ne suffit pas en CEMAC : « brasserie, Gabon, 400 salariés » désigne presque une seule
entreprise. Trois mécanismes, et chacun ferme une porte différente.

### 1. Une photographie, sans lien vers l'entreprise

`catalogue_regimes` est une table PUBLIQUE (hors RLS, comme `sceaux`) qui ne porte ni `organisation_id`, ni
personne, ni date exposée : le pays, un secteur choisi dans une liste fermée, une tranche de taille, la
convention, l'année d'effet (gardée, jamais servie) et les catégories — barème, base de salaire, ancienneté
minimale, plafond, arrondi, primes, événements. Jamais le document, la note, les dates précises.

Une empreinte `sha256("catalogue:" + organisation_id)` compte les entreprises DISTINCTES (une entreprise
qui partage deux régimes ne fait pas deux entreprises) sans les nommer ; elle n'est jamais servie, et un
identifiant d'organisation est un UUID aléatoire que personne d'autre ne connaît.

Le lien est du côté de l'entreprise : `partages_regime` (RLS) dit quelle version elle a partagée, sous quel
numéro de catalogue. L'exploitant de la plateforme peut relier les deux ; aucun autre client ne le peut.

Une copie figée plutôt qu'un lien vivant : un lien finirait par dire qui a modifié quoi, et quand.

### 2. Des groupes d'au moins cinq entreprises, sans fuite par soustraction

Le catalogue montre des GROUPES, jamais une entrée isolée. Le découpage descend CEMAC → pays → secteur →
taille, et ne descend d'un niveau que si TOUS les sous-groupes non vides comptent au moins cinq entreprises
distinctes ; sinon le groupe s'affiche en entier au niveau où il est. Sous cinq entreprises en tout, rien.

Pourquoi « tous » : si l'on masquait la taille d'une seule entrée parce que sa case est petite tout en
montrant celle des autres, le lecteur saurait que cette entrée appartient à une petite case — la
soustraction la désignerait. Les groupes affichés forment une partition, chacun d'au moins cinq.

Ce que le niveau cache, l'entrée le cache aussi : la convention d'une entrée n'est montrée que si son groupe
montre le secteur (elle dit le secteur) ; l'écart à sa convention est toujours montré, en pourcentage.

### 3. Rien de reconnaissable dans le contenu

Une catégorie au nom courant (Cadre, Employé, Ouvrier, Agent de maîtrise, Technicien, Non-cadre, Direction,
`*`) garde son nom ; un nom inhabituel (« Pilotes », « Navigants ») devient « Catégorie A », « B »… L'ordre
n'est pas celui du partage : le catalogue trie par générosité à vingt ans.

Limite assumée : un barème très particulier reste reconnaissable par qui le connaît déjà. Il n'apprend rien
qu'il ne sache, sinon que l'entreprise a partagé.

## Le consentement

- Partager est un acte de la DRH (`admin_client`) : le régime appartient à l'entreprise. Ni le conseiller ni
  la plateforme ne partagent pour elle.
- Seule une version ADOPTÉE se partage : un projet n'est le régime de personne.
- L'accord est explicite, sur un écran qui dit ce qui part et ce qui ne part pas.
- Une entreprise a au plus UN partage actif : en partager un nouveau retire le précédent.
- Le retrait est possible à tout moment, pour l'avenir (`catalogue_retraits`, append-only). Les copies déjà
  reprises par d'autres sont à eux : elles n'ont gardé aucun lien avec la source.
- Hors CEMAC, pas de partage (le périmètre servi).

## La consultation et la reprise

Toute personne connectée consulte (`GET /catalogue/regimes`) : DRH clientes et conseillers. Chaque entrée
montre ses mois d'indemnité à 10, 20 et 30 ans par catégorie et son écart à sa convention à vingt ans.
« Reprendre dans le formulaire » verse une version proposée, comme un modèle type : la convention est gardée
si elle est visible et du pays de l'entreprise, sinon remplacée par celle du pays ; la référence dit
« Inspiré d'un régime du catalogue anonyme ». L'analyse habituelle suit, et l'entreprise adopte.

## Hors de cette étape

La réciprocité (se comparer seulement si l'on partage) et les percentiles appartiennent à l'étape 3, la
comparaison chiffrée, qui attend un avis juridique sur l'échange d'informations de rémunération entre
concurrents.
