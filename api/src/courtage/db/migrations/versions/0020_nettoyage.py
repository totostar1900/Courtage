"""Nettoyer un dossier : une étude émise peut partir, son sceau reste.

Une étude émise ne se modifie jamais. Elle se supprime seulement par le nettoyage du dossier, que la plateforme
signale en posant `app.nettoyage = 'oui'` dans la transaction : un DELETE ordinaire reste refusé. Son rapport
(documents) part avec elle ; son sceau (public) reste, et son numéro se vérifie toujours.

Revision ID: 0020_nettoyage
Revises: 0019_suppressions
"""
from alembic import op

revision = "0020_nettoyage"
down_revision = "0019_suppressions"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE OR REPLACE FUNCTION etude_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.statut = 'emise' THEN
    IF TG_OP = 'DELETE' AND current_setting('app.nettoyage', true) = 'oui' THEN
      RETURN OLD;
    END IF;
    RAISE EXCEPTION 'etude_emise_immuable: l''étude % est émise ; créer une nouvelle étude qui la remplace', OLD.id;
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;

GRANT DELETE ON documents TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
