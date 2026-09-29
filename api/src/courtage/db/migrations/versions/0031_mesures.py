"""La mesure d'audience, sans témoin : un compteur par jour, par événement et par source.

Aucun identifiant, aucune adresse IP, aucun tiers : `mesures(jour, evenement, source, n)`. Les événements et les
sources viennent de listes fermées. Conception : docs/specs/2026-09-29-contenu-mesure-portefeuille-whatsapp-design.md §2.

Revision ID: 0031_mesures
Revises: 0030_demandes_rappel
"""
from alembic import op

revision = "0031_mesures"
down_revision = "0030_demandes_rappel"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE mesures (
  jour       date NOT NULL,
  evenement  text NOT NULL CHECK (evenement IN ('vitrine', 'contenu_ifc', 'contenu_cameroun', 'essai_ouvert',
                                                'essai_calcule', 'inscription_ouverte', 'inscription_faite',
                                                'mandat_signe')),
  source     text NOT NULL CHECK (source IN ('direct', 'recherche', 'reseau_social', 'autre')),
  n          integer NOT NULL DEFAULT 1 CHECK (n > 0),
  PRIMARY KEY (jour, evenement, source)
);
GRANT SELECT, INSERT, UPDATE (n) ON mesures TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
