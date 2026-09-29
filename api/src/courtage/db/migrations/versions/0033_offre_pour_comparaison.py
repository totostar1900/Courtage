"""Une offre ajoutée par l'entreprise, pour comparaison : un devis reçu directement, classé avec les autres, qui ne
se retient pas (pour la retenir, le conseiller consulte cet assureur).

Conception : docs/specs/2026-09-29-parcours-client-et-design-design.md §7.

Revision ID: 0033_offre_pour_comparaison
Revises: 0032_avis_whatsapp
"""
from alembic import op

revision = "0033_offre_pour_comparaison"
down_revision = "0032_avis_whatsapp"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE reponses_fiche ADD COLUMN pour_comparaison boolean NOT NULL DEFAULT false;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
