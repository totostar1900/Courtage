"""Les rappels du cycle annuel : au plus un courriel par étape, par état et par année.

`rappels_envoyes` (sous RLS) garde la clé de l'étape de l'année (`personnel:2026-12-31`…) et l'état rappelé
(`bientot`, `en_retard`) ; la tâche quotidienne ne rappelle pas deux fois la même chose.

Conception : docs/specs/2026-09-29-cycle-annuel-design.md §4.

Revision ID: 0029_rappels
Revises: 0028_consultations
"""
from alembic import op

revision = "0029_rappels"
down_revision = "0028_consultations"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE rappels_envoyes (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id  uuid NOT NULL REFERENCES organisations(id),
  cle              text NOT NULL,
  etat             text NOT NULL CHECK (etat IN ('bientot', 'en_retard')),
  destinataires    integer NOT NULL,
  envoye_le        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organisation_id, cle, etat)
);
ALTER TABLE rappels_envoyes ENABLE ROW LEVEL SECURITY;
CREATE POLICY rappels_envoyes_organisation ON rappels_envoyes USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON rappels_envoyes TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
