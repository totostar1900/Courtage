"""Barème d'entreprise, et le nom affiché des utilisateurs.

Une entreprise peut verser plus que sa convention (accord, contrats, usage
constant), jamais moins. Quand elle le fait habituellement, sa dette réelle est
plus lourde que la dette conventionnelle : l'étude l'évalue avec SON barème,
qui s'appuie sur un document et que le conseiller valide. Validé, il ne bouge
plus ; un nouveau barème prend la suite avec sa date d'effet.

Le nom affiché sert au rapport : il nomme le conseiller qui émet.

Revision ID: 0003_bareme_entreprise
Revises: 0002_remuneration
"""
from alembic import op

revision = "0003_bareme_entreprise"
down_revision = "0002_remuneration"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE utilisateurs ADD COLUMN nom_affiche text;

CREATE TYPE fondement_bareme AS ENUM ('accord_entreprise', 'contrat_travail', 'usage', 'decision_direction');
CREATE TYPE statut_bareme AS ENUM ('propose', 'valide');

CREATE TABLE baremes_entreprise (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id     uuid NOT NULL REFERENCES organisations(id),
  libelle             text NOT NULL CHECK (length(trim(libelle)) > 0),
  fondement           fondement_bareme NOT NULL,
  document_reference  text NOT NULL CHECK (length(trim(document_reference)) > 0),
  convention_code     text NOT NULL,           -- la convention que ce barème améliore
  en_vigueur_du       date NOT NULL,
  en_vigueur_au       date CHECK (en_vigueur_au IS NULL OR en_vigueur_au >= en_vigueur_du),
  bareme              jsonb NOT NULL,
  statut              statut_bareme NOT NULL DEFAULT 'propose',
  propose_par         uuid NOT NULL REFERENCES utilisateurs(id),
  valide_par          uuid REFERENCES utilisateurs(id),
  valide_le           timestamptz,
  cree_le             timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT bareme_valide_complet CHECK (statut = 'propose' OR (valide_par IS NOT NULL AND valide_le IS NOT NULL))
);

CREATE FUNCTION bareme_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.statut = 'valide' THEN
    RAISE EXCEPTION 'bareme_valide_immuable: le barème % est validé ; en proposer un nouveau', OLD.id;
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER baremes_immuables BEFORE UPDATE OR DELETE ON baremes_entreprise
  FOR EACH ROW EXECUTE FUNCTION bareme_immuable();

ALTER TABLE baremes_entreprise ENABLE ROW LEVEL SECURITY;
CREATE POLICY baremes_entreprise_organisation ON baremes_entreprise
  USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT, UPDATE, DELETE ON baremes_entreprise TO courtage_app;

ALTER TABLE etudes ADD COLUMN bareme_entreprise_id uuid REFERENCES baremes_entreprise(id);
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
