"""Les données de travail se suppriment ; ce qui les cite les retient.

Un fichier du personnel, des conditions de rémunération, un contrat se suppriment quand rien ne s'appuie dessus :
les clés étrangères (études, dossiers de prise en charge) les retiennent, et le service applique le reste (un contrat
dont la période couvre un départ enregistré reste). Un fichier cité par une étude émise ne se supprime pas : il
s'allège (ses lignes se vident, son empreinte reste), une fois.

Revision ID: 0019_suppressions
Revises: 0018_equipe
"""
from alembic import op

revision = "0019_suppressions"
down_revision = "0018_equipe"
branch_labels = None
depends_on = None

SCHEMA = """
GRANT DELETE ON fichiers_personnel, conditions_remuneration, contrats TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
