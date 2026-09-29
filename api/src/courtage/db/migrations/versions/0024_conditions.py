"""Les conditions d'utilisation acceptées à l'inscription : quelle version, et quand.

La version vient de `courtage.cabinet.CONDITIONS_VERSION` ; l'inscription l'exige. Les comptes d'avant n'en ont pas.

Conception : docs/specs/2026-09-29-plateforme-ouverte-p1-design.md §3.

Revision ID: 0024_conditions
Revises: 0023_activation
"""
from alembic import op

revision = "0024_conditions"
down_revision = "0023_activation"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE utilisateurs
  ADD COLUMN conditions_version text,
  ADD COLUMN conditions_acceptees_le timestamptz,
  ADD CONSTRAINT conditions_datees CHECK ((conditions_version IS NULL) = (conditions_acceptees_le IS NULL));
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
