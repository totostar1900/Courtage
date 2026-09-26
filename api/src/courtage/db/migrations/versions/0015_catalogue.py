"""Le catalogue anonyme des régimes : une photographie publique, un lien gardé par l'entreprise.

`catalogue_regimes` est public (hors RLS, comme `sceaux`) et ne porte ni organisation, ni personne : le pays,
un secteur d'une liste fermée, une tranche de taille, la convention, l'année d'effet et les catégories. Une
empreinte compte les entreprises distinctes sans les nommer. `catalogue_retraits` retire pour l'avenir.
`partages_regime` (RLS) est le lien, du côté de l'entreprise seulement. Tout est append-only.
Conception : docs/specs/2026-09-26-catalogue-anonyme-design.md.

Revision ID: 0015_catalogue
Revises: 0014_extractions
"""
from alembic import op

revision = "0015_catalogue"
down_revision = "0014_extractions"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE catalogue_regimes (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empreinte           char(64) NOT NULL,
  pays                text NOT NULL CHECK (pays ~ '^[A-Z]{2}$'),
  secteur             text NOT NULL CHECK (secteur IN ('agriculture', 'banque_assurance', 'btp', 'commerce',
                        'energie_mines', 'industrie', 'services', 'telecoms', 'transport', 'administration_ong', 'autre')),
  taille              text NOT NULL CHECK (taille IN ('moins_de_50', '50_a_250', 'plus_de_250')),
  convention_code     text NOT NULL,
  annee               integer NOT NULL,
  categories          jsonb NOT NULL
);
GRANT SELECT, INSERT ON catalogue_regimes TO courtage_app;

CREATE TABLE catalogue_retraits (
  partage_id          uuid PRIMARY KEY REFERENCES catalogue_regimes(id),
  retire_le           timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT ON catalogue_retraits TO courtage_app;

CREATE TABLE partages_regime (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id     uuid NOT NULL REFERENCES organisations(id),
  version_id          uuid NOT NULL REFERENCES regimes_versions(id),
  partage_id          uuid NOT NULL UNIQUE REFERENCES catalogue_regimes(id),
  partage_par         uuid NOT NULL REFERENCES utilisateurs(id),
  partage_le          timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE partages_regime ENABLE ROW LEVEL SECURITY;
CREATE POLICY partages_regime_organisation ON partages_regime USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON partages_regime TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
