# Plan : extraction assistée des textes existants

Une entreprise a déjà son accord ; la plateforme a déjà des conventions à compléter.
Plutôt que de ressaisir un barème, la plateforme **lit le texte et propose**. Chaque
valeur proposée **cite son passage**, et la plateforme vérifie ce passage dans le texte.
Périmètre (décision du 26/09) : **les pays de la CEMAC seulement**.

- [x] Module `courtage/extraction` :
  - le schéma `Extraction` : catégories, tranches, citations, conditions, points à relire ;
  - `lire_document` : PDF lu localement par pypdf, ou texte brut ;
  - `citation_retrouvee` : casse, accents, espaces et césures ignorés ;
  - `proposer` : la version à préremplir, les vérifications, les constats ; hors CEMAC, rien n'est repris.
- [x] Deux moteurs interchangeables :
  - `ExtracteurRegles`, par défaut, sans appel externe : formulations courantes, sans distinction des catégories ;
  - `ExtracteurClaude` (`claude-opus-5`) : le document tel quel, une sortie structurée par schéma JSON, la pensée adaptative, un repli serveur en cas de refus (`fallbacks: "default"`), et une réponse revalidée localement.
- [x] Migration 0014 `extractions` : la trace (empreinte, taille, moteur, modèle, envoi à un tiers, proposition), **jamais le document**.
- [x] `POST /organisations/{id}/regimes/extraction` (entreprise, conseiller) :
  - dossier hors CEMAC : refusé ;
  - moteur qui envoie à un tiers : accord explicite exigé ;
  - formats : PDF ou texte brut, 10 Mo au plus.
- [x] `GET /extraction/mode`.
- [x] `POST /referentiel/extraction` (plateforme) : une convention collective CEMAC proposée au statut « à valider », au format du référentiel, à relire avant d'entrer dans `referentiel/donnees/`.
- [x] Écran : « Partir d'un texte existant » dans « Décrire un régime » et « Nouvelle version ».
  - L'accord est demandé quand le texte part chez un tiers.
  - Chaque valeur est montrée avec son passage : ✓, introuvable ou non vérifiable.
  - « Reprendre dans le formulaire » préremplit la version.
- [x] Guide, démonstration (accord fictif lu par le moteur à règles).
- [ ] Essai réel du moteur Claude : aucune clé d'API dans l'environnement de développement (voir DEPLOY.md).

Commit : `feat(extraction): lecture assistée des textes existants (CEMAC)`
