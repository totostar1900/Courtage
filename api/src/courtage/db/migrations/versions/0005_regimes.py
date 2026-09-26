"""Le régime IFC de l'entreprise : versions et catégories (spec régime IFC §4, §10).

Un régime est ce que l'entreprise verse : un accord, un règlement, des
contrats, un usage, ou sa convention collective seule. Il vit en VERSIONS :
chacune a sa date d'effet et son document, est d'abord en `analyse`, puis
`adoptee` par l'entreprise d'un seul acte ; adoptée, elle ne bouge plus. La
version en vigueur à une date est la dernière adoptée dont la date d'effet la
précède : une nouvelle version prend la suite sans toucher l'ancienne.

Chaque version a une ou plusieurs catégories de personnel (« * » pour toutes
les autres), chacune avec sa convention plancher, son barème et ses
conditions. Un régime moins favorable que son plancher est ENREGISTRÉ tel quel
(décision du 2026-09-26) ; l'adoption demande que l'entreprise ait vu la
non-conformité, et le moteur retient toujours le plus favorable.

Les barèmes d'entreprise (0003) sont repris en régimes ; la table reste, en
lecture, pour les études qui les citent.

Revision ID: 0005_regimes
Revises: 0004_documents
"""
from alembic import op

revision = "0005_regimes"
down_revision = "0004_documents"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TYPE statut_version_regime AS ENUM ('analyse', 'adoptee');
CREATE TYPE base_salaire AS ENUM ('dernier', 'moyenne_12_mois');
CREATE TYPE arrondi_anciennete AS ENUM ('annees', 'mois');

CREATE TABLE regimes (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id  uuid NOT NULL REFERENCES organisations(id),
  nom              text NOT NULL CHECK (length(trim(nom)) > 0),
  cree_par         uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE regimes_versions (
  id                         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id            uuid NOT NULL REFERENCES organisations(id),
  regime_id                  uuid NOT NULL REFERENCES regimes(id),
  numero                     integer NOT NULL CHECK (numero > 0),
  en_vigueur_du              date NOT NULL,
  fondement                  fondement_bareme NOT NULL,
  document_reference         text NOT NULL CHECK (length(trim(document_reference)) > 0),
  note                       text,
  statut                     statut_version_regime NOT NULL DEFAULT 'analyse',
  cree_par                   uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le                    timestamptz NOT NULL DEFAULT now(),
  adoptee_par                uuid REFERENCES utilisateurs(id),
  adoptee_le                 timestamptz,
  non_conformite_acceptee    boolean NOT NULL DEFAULT false,
  constats_a_l_adoption      jsonb,
  UNIQUE (regime_id, numero),
  CONSTRAINT version_adoptee_complete CHECK (
    statut = 'analyse' OR (adoptee_par IS NOT NULL AND adoptee_le IS NOT NULL AND constats_a_l_adoption IS NOT NULL)
  )
);
-- Deux versions adoptées d'un même régime ne prennent pas effet le même jour.
CREATE UNIQUE INDEX regimes_versions_une_par_date ON regimes_versions (regime_id, en_vigueur_du) WHERE statut = 'adoptee';

CREATE TABLE regimes_categories (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id      uuid NOT NULL REFERENCES organisations(id),
  version_id           uuid NOT NULL REFERENCES regimes_versions(id),
  categorie            text NOT NULL CHECK (length(trim(categorie)) > 0),   -- « * » : toutes les autres
  convention_code      text NOT NULL,
  bareme               jsonb NOT NULL,
  anciennete_minimale  integer NOT NULL DEFAULT 0 CHECK (anciennete_minimale >= 0),
  plafond_mois         numeric CHECK (plafond_mois IS NULL OR plafond_mois > 0),
  arrondi              arrondi_anciennete NOT NULL DEFAULT 'annees',
  base_salaire         base_salaire NOT NULL DEFAULT 'dernier',
  avec_primes          boolean NOT NULL DEFAULT false,
  evenements           text[] NOT NULL DEFAULT ARRAY['retraite'],
  UNIQUE (version_id, categorie),
  CHECK ('retraite' = ANY (evenements)),
  CHECK (evenements <@ ARRAY['retraite', 'depart_anticipe', 'licenciement_economique', 'deces'])
);

-- Adoptée, une version ne bouge plus, ni elle ni ses catégories.
CREATE FUNCTION version_regime_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.statut = 'adoptee' THEN
    RAISE EXCEPTION 'version_adoptee_immuable: la version % est adoptée ; en créer une nouvelle', OLD.id;
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER regimes_versions_immuables BEFORE UPDATE OR DELETE ON regimes_versions
  FOR EACH ROW EXECUTE FUNCTION version_regime_immuable();

CREATE FUNCTION categorie_regime_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  statut_version statut_version_regime;
BEGIN
  SELECT statut INTO statut_version FROM regimes_versions
   WHERE id = CASE WHEN TG_OP = 'INSERT' THEN NEW.version_id ELSE OLD.version_id END;
  IF statut_version = 'adoptee' THEN
    RAISE EXCEPTION 'version_adoptee_immuable: les catégories d''une version adoptée ne bougent plus';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER regimes_categories_immuables BEFORE INSERT OR UPDATE OR DELETE ON regimes_categories
  FOR EACH ROW EXECUTE FUNCTION categorie_regime_immuable();

ALTER TABLE regimes ENABLE ROW LEVEL SECURITY;
CREATE POLICY regimes_organisation ON regimes USING (organisation_id = organisation_courante());
ALTER TABLE regimes_versions ENABLE ROW LEVEL SECURITY;
CREATE POLICY regimes_versions_organisation ON regimes_versions USING (organisation_id = organisation_courante());
ALTER TABLE regimes_categories ENABLE ROW LEVEL SECURITY;
CREATE POLICY regimes_categories_organisation ON regimes_categories USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT, UPDATE ON regimes TO courtage_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON regimes_versions, regimes_categories TO courtage_app;

ALTER TABLE etudes ADD COLUMN regime_version_id uuid REFERENCES regimes_versions(id);

-- Reprise : chaque barème d'entreprise devient un régime d'une version, d'une catégorie « * ».
INSERT INTO regimes (id, organisation_id, nom, cree_par, cree_le)
  SELECT id, organisation_id, libelle, propose_par, cree_le FROM baremes_entreprise;
INSERT INTO regimes_versions (organisation_id, regime_id, numero, en_vigueur_du, fondement, document_reference,
                              statut, cree_par, cree_le, adoptee_par, adoptee_le, constats_a_l_adoption)
  SELECT organisation_id, id, 1, en_vigueur_du, fondement, document_reference,
         CASE statut WHEN 'valide' THEN 'adoptee'::statut_version_regime ELSE 'analyse' END,
         propose_par, cree_le, valide_par, valide_le,
         CASE statut WHEN 'valide' THEN '[]'::jsonb END
    FROM baremes_entreprise;
"""

# Les catégories d'une version reprise adoptée ne peuvent être insérées qu'avant
# son adoption : on les insère d'abord en désactivant le seul déclencheur concerné.
REPRISE_CATEGORIES = """
ALTER TABLE regimes_categories DISABLE TRIGGER regimes_categories_immuables;
INSERT INTO regimes_categories (organisation_id, version_id, categorie, convention_code, bareme)
  SELECT v.organisation_id, v.id, '*', b.convention_code, b.bareme
    FROM baremes_entreprise b JOIN regimes_versions v ON v.regime_id = b.id;
ALTER TABLE regimes_categories ENABLE TRIGGER regimes_categories_immuables;

-- Les barèmes d'entreprise ne s'écrivent plus : ils restent lisibles pour les études qui les citent.
REVOKE INSERT, UPDATE, DELETE ON baremes_entreprise FROM courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)
    op.execute(REPRISE_CATEGORIES)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
