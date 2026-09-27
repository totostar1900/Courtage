"""Le mandat de courtage : demandé par le client, proposé par le conseiller, signé par le client.

`mandats_courtage` suit un mandat de la demande à la signature : `demande` (le client demande un accompagnement),
`propose` (le conseiller a fixé le périmètre, la date d'effet, la durée, le préavis), puis `signe`, `refuse` ou
`retire`. Le texte proposé est figé par son empreinte : la signature porte sur ce texte-là. Signé, le mandat est
scellé (préfixe MC-, rangé dans `documents`) et ne se modifie plus : un déclencheur le refuse. Un contrat
« courtage » n'exige plus d'assureur : le mandat précède le placement.

Revision ID: 0022_mandats
Revises: 0021_sans_remuneration
"""
from alembic import op

revision = "0022_mandats"
down_revision = "0021_sans_remuneration"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE mandats_courtage (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id     uuid NOT NULL REFERENCES organisations(id),
  statut              text NOT NULL DEFAULT 'demande'
                        CHECK (statut IN ('demande', 'propose', 'signe', 'refuse', 'retire')),
  besoins             text[] NOT NULL DEFAULT '{}',
  message             text,
  demande_par         uuid NOT NULL REFERENCES utilisateurs(id),
  demande_le          timestamptz NOT NULL DEFAULT now(),
  perimetre           text[],
  date_effet          date,
  duree_mois          integer CHECK (duree_mois BETWEEN 1 AND 60),
  preavis_mois        integer CHECK (preavis_mois BETWEEN 1 AND 12),
  exclusif            boolean,
  conditions          text,
  propose_par         uuid REFERENCES utilisateurs(id),
  propose_le          timestamptz,
  empreinte_texte     text,
  signe_par           uuid REFERENCES utilisateurs(id),
  signe_le            timestamptz,
  signataire_nom      text,
  signataire_fonction text,
  motif               text,
  contrat_id          uuid REFERENCES contrats(id),
  CONSTRAINT mandat_propose_complet CHECK (
    statut IN ('demande', 'retire')
    OR (perimetre IS NOT NULL AND date_effet IS NOT NULL AND duree_mois IS NOT NULL AND preavis_mois IS NOT NULL
        AND exclusif IS NOT NULL AND propose_par IS NOT NULL AND propose_le IS NOT NULL AND empreinte_texte IS NOT NULL)),
  CONSTRAINT mandat_signe_complet CHECK (
    statut <> 'signe' OR (signe_par IS NOT NULL AND signe_le IS NOT NULL AND signataire_nom IS NOT NULL))
);
CREATE INDEX mandats_courtage_organisation ON mandats_courtage (organisation_id, demande_le DESC);
-- Une seule demande en cours (demandée ou proposée) par dossier.
CREATE UNIQUE INDEX mandats_courtage_un_en_cours ON mandats_courtage (organisation_id)
  WHERE statut IN ('demande', 'propose');
ALTER TABLE mandats_courtage ENABLE ROW LEVEL SECURITY;
CREATE POLICY mandats_courtage_organisation ON mandats_courtage USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT, UPDATE ON mandats_courtage TO courtage_app;

CREATE FUNCTION mandat_signe_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.statut IN ('signe', 'refuse', 'retire') THEN
    RAISE EXCEPTION 'mandat_immuable: le mandat % est %, il ne se modifie plus', OLD.id, OLD.statut;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER mandats_courtage_immuables BEFORE UPDATE ON mandats_courtage
  FOR EACH ROW EXECUTE FUNCTION mandat_signe_immuable();

-- Un courtage suppose un mandat ; l'assureur vient une fois le contrat placé.
ALTER TABLE contrats DROP CONSTRAINT courtage_mandate;
ALTER TABLE contrats ADD CONSTRAINT courtage_mandate CHECK (
  service = 'comparaison' OR (mandat_reference IS NOT NULL AND length(trim(mandat_reference)) > 0));

ALTER TABLE sceaux DROP CONSTRAINT sceaux_numero_check;
ALTER TABLE sceaux ADD CONSTRAINT sceaux_numero_check CHECK (numero ~ '^(RL|PC|FC|NR|MC)-[A-Z0-9]{4}-[A-Z0-9]{4}$');

ALTER TABLE documents
  ADD COLUMN mandat_id uuid REFERENCES mandats_courtage(id),
  DROP CONSTRAINT document_d_une_seule_chose;
ALTER TABLE documents
  ADD CONSTRAINT document_d_une_seule_chose
    CHECK (num_nonnulls(etude_id, fiche_id, prestation_id, version_id, mandat_id) = 1);
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
