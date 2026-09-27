"""L'équipe d'un dossier : des droits, et une fonction libre.

Les droits restent une liste courte et fermée (ce que la personne peut faire) : administrateur de l'entreprise,
contributeur (dépose et prépare, sans adopter), lecture seule, conseiller. La fonction est libre (ce que la
personne est) : DRH, DG, DAF, comptable… Elle vit sur l'adhésion : la même personne peut être DAF d'une entreprise
et administratrice d'une autre.

Revision ID: 0018_equipe
Revises: 0017_versions_et_notes
"""
from alembic import op

revision = "0018_equipe"
down_revision = "0017_versions_et_notes"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TYPE role_adhesion ADD VALUE IF NOT EXISTS 'contributeur_client';
ALTER TABLE adhesions ADD COLUMN fonction text CHECK (fonction IS NULL OR length(fonction) <= 80);
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
