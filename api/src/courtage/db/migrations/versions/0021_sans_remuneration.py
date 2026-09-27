"""La plateforme ne porte plus la rémunération du courtier.

Elle aide une entreprise à souscrire un service IFC ; ce que le courtier facture relève de son mandat, signé à part,
pas d'un calcul de la plateforme. Les conditions de rémunération, leur type, et les honoraires inscrits sur les
études émises partent. L'empreinte d'une étude ne les a jamais comptés : chaque sceau reste vérifiable.

Revision ID: 0021_sans_remuneration
Revises: 0020_nettoyage
"""
from alembic import op

revision = "0021_sans_remuneration"
down_revision = "0020_nettoyage"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE etudes DROP CONSTRAINT etude_emise_complete;
ALTER TABLE etudes ADD CONSTRAINT etude_emise_complete CHECK (
  statut = 'brouillon'
  OR (resultats IS NOT NULL AND empreinte IS NOT NULL AND emise_par IS NOT NULL AND emise_le IS NOT NULL)
);
ALTER TABLE etudes DROP COLUMN conditions_remuneration_id, DROP COLUMN honoraires_ht;
DROP TABLE conditions_remuneration;
DROP TYPE mode_remuneration;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
