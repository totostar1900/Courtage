"""Les avis par courriel : chacun peut les couper dans son profil.

Conception : docs/specs/2026-09-29-plateforme-ouverte-p1-design.md §5.

Revision ID: 0026_avis
Revises: 0025_signataire
"""
from alembic import op

revision = "0026_avis"
down_revision = "0025_signataire"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE utilisateurs ADD COLUMN avis_courriel boolean NOT NULL DEFAULT true;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
