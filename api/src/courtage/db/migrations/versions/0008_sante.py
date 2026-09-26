"""La sonde de santé lit la révision du schéma avec le rôle applicatif.

`GET /api/v1/sante` compare la révision portée par la base à celle que le code
attend ; `courtage_app` doit donc pouvoir LIRE `alembic_version`, et rien de plus.

Revision ID: 0008_sante
Revises: 0007_connexion
"""
from alembic import op

revision = "0008_sante"
down_revision = "0007_connexion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT SELECT ON alembic_version TO courtage_app")


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
