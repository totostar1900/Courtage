"""Une version de régime est un brouillon ou une version adoptée, rien d'autre ; l'adoption se communique.

- Brouillon (`analyse`) : se modifie, se duplique, se supprime (ses études en brouillon partent avec).
- Adoptée : figée, parce qu'elle a été communiquée. Elle se supprime tant que rien ne la cite ; une étude émise, un
  cahier des charges, un partage au catalogue ou une note émise la retiennent par clé étrangère.
- Les dates (s'applique depuis, à partir de, remplacée le) sont une information, pas un statut.
- L'adoption se communique par deux notes scellées, rangées dans `documents` : aux salariés et aux assureurs
  (préfixe NR-).

Les catégories suivent leur version à la suppression (ON DELETE CASCADE) ; un déclencheur refuse toujours de toucher
aux catégories d'une version adoptée qui reste.
Conception : docs/specs/2026-09-27-versions-de-regime-design.md.

Revision ID: 0017_versions_et_notes
Revises: 0016_cycle_de_vie
"""
from alembic import op

revision = "0017_versions_et_notes"
down_revision = "0016_cycle_de_vie"
branch_labels = None
depends_on = None

SCHEMA = """
-- Adoptée, une version ne se modifie plus ; elle se supprime si aucune clé étrangère ne la retient.
CREATE OR REPLACE FUNCTION version_regime_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  IF OLD.statut = 'adoptee' THEN
    RAISE EXCEPTION 'version_adoptee_immuable: la version % est adoptée ; la dupliquer en brouillon', OLD.id;
  END IF;
  RETURN NEW;
END $$;

-- Les catégories d'une version adoptée ne bougent pas, sauf quand leur version disparaît avec elles.
CREATE OR REPLACE FUNCTION categorie_regime_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  statut_version statut_version_regime;
BEGIN
  SELECT statut INTO statut_version FROM regimes_versions
   WHERE id = CASE WHEN TG_OP = 'INSERT' THEN NEW.version_id ELSE OLD.version_id END;
  IF statut_version = 'adoptee' THEN
    RAISE EXCEPTION 'version_adoptee_immuable: les catégories d''une version adoptée ne bougent plus';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;

ALTER TABLE regimes_categories DROP CONSTRAINT regimes_categories_version_id_fkey;
ALTER TABLE regimes_categories ADD CONSTRAINT regimes_categories_version_id_fkey
  FOREIGN KEY (version_id) REFERENCES regimes_versions(id) ON DELETE CASCADE;

GRANT DELETE ON regimes TO courtage_app;

-- Les notes d'une version adoptée : aux salariés, aux assureurs.
ALTER TABLE sceaux DROP CONSTRAINT sceaux_numero_check;
ALTER TABLE sceaux ADD CONSTRAINT sceaux_numero_check CHECK (numero ~ '^(RL|PC|FC|NR)-[A-Z0-9]{4}-[A-Z0-9]{4}$');
ALTER TABLE documents
  ADD COLUMN version_id uuid REFERENCES regimes_versions(id),
  DROP CONSTRAINT document_d_une_seule_chose;
ALTER TABLE documents
  ADD CONSTRAINT document_d_une_seule_chose CHECK (num_nonnulls(etude_id, fiche_id, prestation_id, version_id) = 1);
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
