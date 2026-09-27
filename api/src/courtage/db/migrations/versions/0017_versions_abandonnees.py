"""Une version de régime qu'on n'adopte pas s'abandonne, ou se supprime si rien ne s'en est servi.

Le statut enregistré reste court (`analyse`, `adoptee`, `abandonnee`) ; ce qu'on affiche (projet, en vigueur,
à venir, remplacée, abandonnée) se déduit des dates, dans `services.regimes.etat_version`.

- Abandonnée : un projet que l'entreprise ne retient pas, avec son motif. Elle ne bouge plus, comme une adoptée.
- Supprimée : un projet qu'aucune étude n'a utilisé disparaît ; un régime resté sans version aussi.
  Une version adoptée ne se supprime jamais : des études et des rapports scellés la citent.

Revision ID: 0017_versions_abandonnees
Revises: 0016_cycle_de_vie
"""
from alembic import op

revision = "0017_versions_abandonnees"
down_revision = "0016_cycle_de_vie"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TYPE statut_version_regime ADD VALUE IF NOT EXISTS 'abandonnee';

ALTER TABLE regimes_versions
  ADD COLUMN abandonnee_par uuid REFERENCES utilisateurs(id),
  ADD COLUMN abandonnee_le timestamptz,
  ADD COLUMN motif_abandon text;

-- Chaque statut porte ce qui le prouve (comparé en texte : la valeur ajoutée ne s'emploie pas dans la même
-- transaction que son ajout).
ALTER TABLE regimes_versions DROP CONSTRAINT version_adoptee_complete;
ALTER TABLE regimes_versions ADD CONSTRAINT version_statut_complet CHECK (
  statut::text = 'analyse'
  OR (statut::text = 'adoptee' AND adoptee_par IS NOT NULL AND adoptee_le IS NOT NULL
      AND constats_a_l_adoption IS NOT NULL)
  OR (statut::text = 'abandonnee' AND abandonnee_par IS NOT NULL AND abandonnee_le IS NOT NULL
      AND motif_abandon IS NOT NULL)
);

-- Adoptée ou abandonnée, une version ne bouge plus, ni elle ni ses catégories.
CREATE OR REPLACE FUNCTION version_regime_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.statut::text IN ('adoptee', 'abandonnee') THEN
    RAISE EXCEPTION 'version_adoptee_immuable: la version % est adoptée ou abandonnée ; en créer une nouvelle', OLD.id;
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION categorie_regime_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  statut_version text;
BEGIN
  SELECT statut::text INTO statut_version FROM regimes_versions
   WHERE id = CASE WHEN TG_OP = 'INSERT' THEN NEW.version_id ELSE OLD.version_id END;
  IF statut_version IN ('adoptee', 'abandonnee') THEN
    RAISE EXCEPTION 'version_adoptee_immuable: les catégories d''une version adoptée ou abandonnée ne bougent plus';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;

GRANT DELETE ON regimes TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
