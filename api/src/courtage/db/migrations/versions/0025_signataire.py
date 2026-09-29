"""Le mandat dit en quelle qualité il est signé : représentant légal, ou délégataire avec sa délégation.

- `mandats_courtage.signataire_qualite` : `representant_legal` | `delegataire`, posée à la signature.
- `mandats_courtage.delegation_id` : le justificatif de nature `delegation` que le délégataire a déposé ; un
  délégataire sans délégation est refusé par la base aussi.
- `justificatifs.nature` admet `delegation` à côté de `rccm`.

Conception : docs/specs/2026-09-29-plateforme-ouverte-p1-design.md §4.

Revision ID: 0025_signataire
Revises: 0024_conditions
"""
from alembic import op

revision = "0025_signataire"
down_revision = "0024_conditions"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE justificatifs DROP CONSTRAINT justificatifs_nature_check;
ALTER TABLE justificatifs ADD CONSTRAINT justificatifs_nature_check CHECK (nature IN ('rccm', 'delegation'));

ALTER TABLE mandats_courtage
  ADD COLUMN signataire_qualite text CHECK (signataire_qualite IN ('representant_legal', 'delegataire')),
  ADD COLUMN delegation_id uuid REFERENCES justificatifs(id),
  ADD CONSTRAINT delegation_du_delegataire
    CHECK (signataire_qualite IS DISTINCT FROM 'delegataire' OR delegation_id IS NOT NULL);
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
