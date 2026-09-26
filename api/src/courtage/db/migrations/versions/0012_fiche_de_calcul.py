"""Comparaison : la fiche de calcul d'un départ, scellée (spec prestations §3, comparaison).

Le client qui traite seul avec son assureur joint à sa demande le calcul de la
plateforme : l'ancienneté, la règle, les mois, le montant dû. Le document ne
porte aucune identité (un matricule), il se range donc avec les autres
documents conservés ; son sceau est public comme les autres (préfixe FC-).

Revision ID: 0012_fiche_de_calcul
Revises: 0011_prise_en_charge
"""
from alembic import op

revision = "0012_fiche_de_calcul"
down_revision = "0011_prise_en_charge"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE sceaux DROP CONSTRAINT sceaux_numero_check;
ALTER TABLE sceaux ADD CONSTRAINT sceaux_numero_check CHECK (numero ~ '^(RL|PC|FC)-[A-Z0-9]{4}-[A-Z0-9]{4}$');

ALTER TABLE documents
  ADD COLUMN prestation_id uuid UNIQUE REFERENCES prestations(id),
  DROP CONSTRAINT document_d_une_seule_chose;
ALTER TABLE documents
  ADD CONSTRAINT document_d_une_seule_chose CHECK (num_nonnulls(etude_id, fiche_id, prestation_id) = 1);
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
