"""Connexion par téléphone : codes à usage unique et sessions.

Ni le code ni le jeton de session ne sont stockés en clair : le code est un
HMAC (clé de la plateforme, numéro et code), le jeton une empreinte SHA-256.
Une ligne de code est écrite pour TOUTE demande, numéro connu ou non, pour que
la limite de demandes se comporte de la même façon et ne révèle pas qui est
client. Tables d'identité : hors RLS, lues avant qu'une organisation soit connue.

Revision ID: 0007_connexion
Revises: 0006_fiches_regime
"""
from alembic import op

revision = "0007_connexion"
down_revision = "0006_fiches_regime"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE codes_connexion (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  telephone   text NOT NULL CHECK (telephone ~ '^\\+[0-9]{8,15}$'),
  code_hash   char(64) NOT NULL,
  canal       text NOT NULL,
  cree_le     timestamptz NOT NULL DEFAULT now(),
  expire_le   timestamptz NOT NULL,
  tentatives  integer NOT NULL DEFAULT 0 CHECK (tentatives >= 0),
  utilise_le  timestamptz
);
CREATE INDEX codes_connexion_telephone ON codes_connexion (telephone, cree_le DESC);

CREATE TABLE sessions (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  utilisateur_id     uuid NOT NULL REFERENCES utilisateurs(id),
  jeton_hash         char(64) NOT NULL UNIQUE,
  cree_le            timestamptz NOT NULL DEFAULT now(),
  expire_le          timestamptz NOT NULL,
  derniere_activite  timestamptz NOT NULL DEFAULT now(),
  revoquee_le        timestamptz,
  agent              text
);

GRANT SELECT, INSERT, UPDATE ON codes_connexion, sessions TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
