"""Rémunération : les conditions de chaque client, et les honoraires de chaque étude.

Décision du 2026-09-26 : un modèle mixte, paramétrable client par client.
Des conditions ne se modifient pas : de nouvelles conditions s'ajoutent, avec
leur date d'effet, et une étude émise garde les conditions et le montant qui
s'appliquaient ce jour-là.

Revision ID: 0002_remuneration
Revises: 0001_socle
"""
from alembic import op

revision = "0002_remuneration"
down_revision = "0001_socle"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TYPE mode_remuneration AS ENUM ('honoraires', 'commission', 'mixte');

CREATE TABLE conditions_remuneration (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id         uuid NOT NULL REFERENCES organisations(id),
  en_vigueur_du           date NOT NULL,
  mode                    mode_remuneration NOT NULL,
  honoraires_etude_ifc    bigint NOT NULL DEFAULT 0 CHECK (honoraires_etude_ifc >= 0),   -- F CFA HT, par étude
  honoraires_par_salarie  bigint NOT NULL DEFAULT 0 CHECK (honoraires_par_salarie >= 0), -- F CFA HT, par salarié évalué
  commission_bps          integer NOT NULL DEFAULT 0 CHECK (commission_bps BETWEEN 0 AND 10000),
  note                    text,
  cree_par                uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le                 timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organisation_id, en_vigueur_du),
  -- Le mode dit ce qui est payé, et les montants le confirment.
  CONSTRAINT mode_coherent CHECK (
       (mode = 'honoraires' AND commission_bps = 0 AND honoraires_etude_ifc + honoraires_par_salarie > 0)
    OR (mode = 'commission' AND commission_bps > 0 AND honoraires_etude_ifc = 0 AND honoraires_par_salarie = 0)
    OR (mode = 'mixte'      AND commission_bps > 0 AND honoraires_etude_ifc + honoraires_par_salarie > 0)
  )
);

ALTER TABLE conditions_remuneration ENABLE ROW LEVEL SECURITY;
CREATE POLICY conditions_remuneration_organisation ON conditions_remuneration
  USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON conditions_remuneration TO courtage_app;

ALTER TABLE etudes
  ADD COLUMN conditions_remuneration_id uuid REFERENCES conditions_remuneration(id),
  ADD COLUMN honoraires_ht bigint CHECK (honoraires_ht >= 0);

ALTER TABLE etudes DROP CONSTRAINT etude_emise_complete;
ALTER TABLE etudes ADD CONSTRAINT etude_emise_complete CHECK (
  statut = 'brouillon'
  OR (resultats IS NOT NULL AND empreinte IS NOT NULL AND emise_par IS NOT NULL AND emise_le IS NOT NULL
      AND conditions_remuneration_id IS NOT NULL AND honoraires_ht IS NOT NULL)
);
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
