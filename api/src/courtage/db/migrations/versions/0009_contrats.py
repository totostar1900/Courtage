"""Contrats suivis : le service que la plateforme rend au client, courtage ou comparaison.

Décision du 2026-09-26 (spec prestations §1) : en courtage, la plateforme est
mandatée et porte les prestations auprès de l'assureur ; en comparaison, elle a
éclairé le choix et le client traite seul avec son assureur. Le service est un
fait DATÉ : un contrat ne se modifie pas, un nouveau s'ajoute avec sa date
d'effet, et une prestation relève du service en vigueur à sa date.

Un courtage exige l'assureur et la référence du mandat : sans mandat, pas de
courtage, et la plateforme ne collectera aucune identité.

Revision ID: 0009_contrats
Revises: 0008_sante
"""
from alembic import op

revision = "0009_contrats"
down_revision = "0008_sante"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TYPE service_contrat AS ENUM ('courtage', 'comparaison');

CREATE TABLE contrats (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id    uuid NOT NULL REFERENCES organisations(id),
  en_vigueur_du      date NOT NULL,
  service            service_contrat NOT NULL,
  assureur           text CHECK (assureur IS NULL OR length(trim(assureur)) > 0),
  numero_police      text,
  date_effet_police  date,
  mandat_reference   text,
  note               text,
  cree_par           uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le            timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organisation_id, en_vigueur_du),
  CONSTRAINT courtage_mandate CHECK (
    service = 'comparaison'
    OR (assureur IS NOT NULL AND mandat_reference IS NOT NULL AND length(trim(mandat_reference)) > 0)
  )
);

ALTER TABLE contrats ENABLE ROW LEVEL SECURITY;
CREATE POLICY contrats_organisation ON contrats USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON contrats TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
