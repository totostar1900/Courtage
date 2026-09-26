# Modèles types de régime — conception

Statut : réalisée (26/09/2026). Première étape de « consulter des régimes pour s'inspirer et se comparer ».

## Le besoin, et pourquoi commencer ici

Une entreprise qui n'a pas de régime IFC veut partir de quelque chose plutôt que d'une page blanche ; une
entreprise établie veut se situer. La discussion du 26/09 a séparé trois étapes :

1. **Modèles types de la plateforme** — ce document.
2. Un catalogue anonyme de régimes réels, partagés volontairement (photographie figée, seuil de 5 régimes par
   case, attributs grossis, retrait possible).
3. Une comparaison chiffrée en percentiles, avec réciprocité, après avis juridique (droit de la concurrence :
   échange d'informations de rémunération entre concurrents).

Les modèles types ne portent aucune donnée d'entreprise : aucun risque d'anonymat, aucun consentement à
recueillir, et ils servent dès le premier client — un catalogue réel resterait vide des mois.

## Ce qu'est un modèle type

Un barème CALCULÉ à partir de celui d'une convention CEMAC en vigueur, jamais écrit à la main : quand la
convention change, les modèles suivent. Quatre, pour chaque convention :

| Modèle | Construction |
|---|---|
| **Minimum conventionnel** | le barème de la convention, une seule catégorie `*` |
| **Convention + 25 %** | chaque taux (et chaque palier) multiplié par 1,25 |
| **Cadres favorisés** | `Cadre` à 1,5 fois la convention ; `*` au minimum |
| **Barème unique** | un seul taux par année, le plus petit multiple de 0,05 qui ne passe jamais sous la convention |

Arrondis toujours VERS LE HAUT (au centième ; 0,05 pour le barème unique) et plafonnés aux bornes du
référentiel (3 mois par année, 36 mois par palier) : un modèle est **conforme par construction** — à aucune
ancienneté de 1 à 45 ans il ne donne moins que la convention. Un test le vérifie pour chaque modèle.

Un modèle est servi sous la forme d'une version proposée (`VersionProposee`, celle de l'extraction assistée) :
le formulaire existant le reprend, l'entreprise le relit, le corrige, l'enregistre ; l'analyse habituelle
suit, et elle seule adopte. Le document de référence est prérempli « Modèle type de la plateforme : … »,
pour que la provenance reste lisible tant que l'accord réel n'est pas écrit.

## Où

- `courtage/modeles.py` : pur, sans base.
- `GET /api/v1/referentiel/modeles?pays=CM` : public comme les conventions (rien d'un client). Un pays de la
  CEMAC sans convention préremplie rend une liste vide, dite comme telle.
- Interface : « Partir d'un modèle type » dans « Décrire un régime » et « Nouvelle version », à côté de
  l'extraction assistée ; chaque modèle montre ses mois d'indemnité à quelques anciennetés, face au minimum.
