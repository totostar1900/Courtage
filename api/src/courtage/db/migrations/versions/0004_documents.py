"""Documents émis : le PDF d'une étude, généré une fois, conservé tel quel.

Le document est une donnée du client (RLS). Le sceau, lui, est public et ne
dit que ce que le papier montre (table `sceaux`, migration 0001).

Revision ID: 0004_documents
Revises: 0003_bareme_entreprise
"""
from alembic import op

revision = "0004_documents"
down_revision = "0003_bareme_entreprise"
branch_labels = None
depends_on = None

SCHEMA = """
-- Le sceau signe les faits de l'étude ; le PDF, rendu APRÈS (il imprime le sceau),
-- a sa propre empreinte et sa propre signature.
ALTER TABLE sceaux
  ADD COLUMN empreinte_document char(64),
  ADD COLUMN sceau_document char(64);

CREATE TABLE documents (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id     uuid NOT NULL REFERENCES organisations(id),
  etude_id            uuid NOT NULL UNIQUE REFERENCES etudes(id),
  numero              text NOT NULL UNIQUE REFERENCES sceaux(numero),
  type_contenu        text NOT NULL DEFAULT 'application/pdf',
  contenu             bytea NOT NULL,
  empreinte_document  char(64) NOT NULL,
  cree_le             timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY documents_organisation ON documents
  USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON documents TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
