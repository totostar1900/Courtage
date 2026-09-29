"""Le lien assureur : la consultation tracée (qui, quand, ouvert, répondu) et l'offre déposée par un lien personnel.

- `consultations_assureurs` (sous RLS) : un assureur consulté sur un cahier ; les dates d'envoi, d'ouverture, de
  réponse, de relance et d'annulation.
- `liens_assureurs` : l'empreinte du jeton → la consultation et son organisation. HORS RLS : le lien se lit AVANT
  qu'une organisation soit connue (l'assureur n'a pas de compte), comme `adhesions`. Le jeton lui-même n'est gardé
  nulle part.
- `reponses_fiche.consultation_id` : une réponse déposée par l'assureur ; `saisie_par` est alors vide.

Conception : docs/specs/2026-09-29-lien-assureur-design.md.

Revision ID: 0028_consultations
Revises: 0027_placement
"""
from alembic import op

revision = "0028_consultations"
down_revision = "0027_placement"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE consultations_assureurs (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id   uuid NOT NULL REFERENCES organisations(id),
  fiche_id          uuid NOT NULL REFERENCES fiches_regime(id),
  assureur          text NOT NULL,
  assureur_cle      text NOT NULL,
  contact_nom       text,
  contact_courriel  text NOT NULL,
  expire_le         date NOT NULL,
  envoyee_par       uuid NOT NULL REFERENCES utilisateurs(id),
  envoyee_le        timestamptz NOT NULL DEFAULT now(),
  relances          integer NOT NULL DEFAULT 0,
  relancee_le       timestamptz,
  ouverte_le        timestamptz,
  repondue_le       timestamptz,
  annulee_le        timestamptz
);
-- Un assureur, une consultation active par cahier.
CREATE UNIQUE INDEX consultations_une_active ON consultations_assureurs (fiche_id, assureur_cle) WHERE annulee_le IS NULL;
ALTER TABLE consultations_assureurs ENABLE ROW LEVEL SECURITY;
CREATE POLICY consultations_assureurs_organisation ON consultations_assureurs
  USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT, UPDATE (relances, relancee_le, ouverte_le, repondue_le, annulee_le)
  ON consultations_assureurs TO courtage_app;

CREATE TABLE liens_assureurs (
  jeton_hash        text PRIMARY KEY,
  consultation_id   uuid NOT NULL REFERENCES consultations_assureurs(id),
  organisation_id   uuid NOT NULL REFERENCES organisations(id),
  cree_le           timestamptz NOT NULL DEFAULT now(),
  revoque_le        timestamptz
);
GRANT SELECT, INSERT, UPDATE (revoque_le) ON liens_assureurs TO courtage_app;

ALTER TABLE reponses_fiche ADD COLUMN consultation_id uuid REFERENCES consultations_assureurs(id);
ALTER TABLE reponses_fiche ALTER COLUMN saisie_par DROP NOT NULL;
ALTER TABLE reponses_fiche ADD CONSTRAINT reponse_saisie_ou_deposee
  CHECK (saisie_par IS NOT NULL OR consultation_id IS NOT NULL);
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
