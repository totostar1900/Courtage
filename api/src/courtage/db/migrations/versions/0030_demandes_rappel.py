"""Les demandes de rappel déposées depuis la vitrine : un visiteur veut parler au courtier.

`demandes_rappel` est une table de plateforme, hors RLS (aucune organisation n'existe encore) : qui, quelle
entreprise, quel numéro, quel créneau, son accord ; puis le suivi du courtier (rappelée, sans suite, une note).
Effacée douze mois après sa réception par la tâche quotidienne.

Conception : docs/specs/2026-09-29-site-public-design.md §2.

Revision ID: 0030_demandes_rappel
Revises: 0029_rappels
"""
from alembic import op

revision = "0030_demandes_rappel"
down_revision = "0029_rappels"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE demandes_rappel (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nom           text NOT NULL,
  entreprise    text NOT NULL,
  telephone     text NOT NULL,
  courriel      text,
  creneau       text NOT NULL CHECK (creneau IN ('matin', 'apres_midi', 'indifferent')),
  message       text CHECK (length(message) <= 1000),
  accord        boolean NOT NULL CHECK (accord),
  recue_le      timestamptz NOT NULL DEFAULT now(),
  statut        text NOT NULL DEFAULT 'a_rappeler' CHECK (statut IN ('a_rappeler', 'rappelee', 'sans_suite')),
  traitee_par   uuid REFERENCES utilisateurs(id),
  traitee_le    timestamptz,
  note          text
);
CREATE INDEX demandes_rappel_recue ON demandes_rappel (recue_le);
GRANT SELECT, INSERT, UPDATE (statut, traitee_par, traitee_le, note), DELETE ON demandes_rappel TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
