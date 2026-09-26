"""Fiche régime : le cahier des charges envoyé aux assureurs.

Elle part d'une étude ÉMISE, ne contient que des agrégats (`courtage.fiche`),
porte les conditions demandées et la date limite de réponse. Émise d'un seul
acte, scellée comme le rapport ; ensuite elle ne bouge plus (le rôle
applicatif n'a ni UPDATE ni DELETE). Son PDF rejoint la table `documents`,
qui accueille désormais un document d'étude OU de fiche.

Revision ID: 0006_fiches_regime
Revises: 0005_regimes
"""
from alembic import op

revision = "0006_fiches_regime"
down_revision = "0005_regimes"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE fiches_regime (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id       uuid NOT NULL REFERENCES organisations(id),
  etude_id              uuid NOT NULL REFERENCES etudes(id),
  regime_version_id     uuid REFERENCES regimes_versions(id),
  date_limite_reponse   date NOT NULL,
  conditions            jsonb NOT NULL,
  contenu               jsonb NOT NULL,
  empreinte             char(64) NOT NULL,
  emise_par             uuid NOT NULL REFERENCES utilisateurs(id),
  emise_le              timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE fiches_regime ENABLE ROW LEVEL SECURITY;
CREATE POLICY fiches_regime_organisation ON fiches_regime USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON fiches_regime TO courtage_app;

ALTER TABLE documents
  ALTER COLUMN etude_id DROP NOT NULL,
  ADD COLUMN fiche_id uuid UNIQUE REFERENCES fiches_regime(id),
  ADD CONSTRAINT document_d_une_seule_chose CHECK ((etude_id IS NULL) <> (fiche_id IS NULL));
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
