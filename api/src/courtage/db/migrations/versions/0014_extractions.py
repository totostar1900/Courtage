"""Extraction assistée : la trace de chaque lecture d'un texte existant.

La plateforme ne garde pas le document : son empreinte, son nom, le moteur qui
l'a lu (et s'il l'a envoyé à un tiers, avec l'accord de la personne), et la
proposition rendue — les valeurs et les passages cités. Ce qui est ensuite
enregistré comme version de régime l'est par une personne, par la voie habituelle.

Revision ID: 0014_extractions
Revises: 0013_reponses_assureurs
"""
from alembic import op

revision = "0014_extractions"
down_revision = "0013_reponses_assureurs"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE extractions (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id     uuid NOT NULL REFERENCES organisations(id),
  nom_fichier         text NOT NULL,
  empreinte           char(64) NOT NULL,
  taille              integer NOT NULL CHECK (taille >= 0),
  moteur              text NOT NULL,
  modele              text,
  envoye_a_un_tiers   boolean NOT NULL,
  resultat            jsonb NOT NULL,
  cree_par            uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le             timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE extractions ENABLE ROW LEVEL SECURITY;
CREATE POLICY extractions_organisation ON extractions USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON extractions TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
