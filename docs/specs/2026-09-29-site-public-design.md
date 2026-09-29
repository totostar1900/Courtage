# Le site public — être trouvé, être rappelé

Date : 2026-09-29. Suite du lot P1 (la vitrine) : ce qu'il faut avant toute promotion.

## 1. Être trouvé

L'application est une page unique servie en JavaScript ; un moteur de recherche ou un aperçu de lien (WhatsApp,
LinkedIn) n'y lit rien d'autre que l'en-tête HTML. Donc :

- **L'en-tête** (`web/index.html`) : description, Open Graph et carte Twitter (titre, description, image 1200×630),
  couleur, icône. Un contenu `<noscript>` dit l'offre et donne les liens publics, pour qui lit sans JavaScript.
- **Un titre par page publique** (vitrine, essai, inscription, connexion, guide, pages légales, vérification) ; les
  pages d'un dossier restent « Courtage ».
- **`/robots.txt`** : les pages publiques s'indexent ; les dossiers, le profil, les liens d'assureurs (`/offre/`) et
  l'API non. **`/sitemap.xml`** : les pages publiques, sur l'adresse publique (`COURTAGE_URL_PUBLIQUE`). Servis par
  l'API, qui connaît cette adresse.

## 2. Être rappelé

Beaucoup d'entreprises veulent parler à quelqu'un avant d'essayer. La vitrine offre « Être rappelé » : nom, entreprise,
téléphone (vérifié au format), courriel facultatif, un créneau (matin, après-midi, indifférent), un message court, et
l'accord pour être contacté.

- La demande est gardée (`demandes_rappel`, plateforme, hors RLS : aucune organisation n'existe) et le courtier est
  prévenu par courriel — sans le contenu : « une demande de rappel vous attend », et le lien.
- Le courtier les voit sur son accueil, les plus anciennes d'abord, et les passe « rappelée » ou « sans suite », avec
  une note.
- Limité en fréquence ; un champ piège écarte les robots sans rien leur dire.
- **Effacée douze mois après** (la tâche quotidienne) ; la politique de confidentialité le dit, et sa version change.
