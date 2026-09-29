"""Les avis sur WhatsApp : chacun peut les demander dans son profil, au numéro vérifié de son compte ; désactivés par
défaut.

Conception : docs/specs/2026-09-29-contenu-mesure-portefeuille-whatsapp-design.md §4.

Revision ID: 0032_avis_whatsapp
Revises: 0031_mesures
"""
from alembic import op

revision = "0032_avis_whatsapp"
down_revision = "0031_mesures"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE utilisateurs ADD COLUMN avis_whatsapp boolean NOT NULL DEFAULT false;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
