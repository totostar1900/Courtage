"""Le cycle de vie d'un dossier : ouvert, suspendu, clôturé, archivé ; supprimé s'il était vide.

`organisations.etat` dit où en est le dossier, pour le lire d'un coup d'œil (avant même qu'une organisation soit
choisie : « Vos dossiers »). `etats_dossier` en garde l'histoire, motivée, datée et signée : append-only, sous RLS.

À l'archivage, le personnel déposé est vidé : `fichiers_personnel` reste (les études le référencent, et son empreinte
prouve ce qui a été évalué), ses lignes partent. Le rôle applicatif ne peut que VIDER un fichier, une seule fois :
un déclencheur refuse toute autre modification.
Conception : docs/specs/2026-09-27-cycle-de-vie-des-dossiers-design.md.

Revision ID: 0016_cycle_de_vie
Revises: 0015_catalogue
"""
from alembic import op

revision = "0016_cycle_de_vie"
down_revision = "0015_catalogue"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE organisations
  ADD COLUMN etat text NOT NULL DEFAULT 'ouvert'
    CHECK (etat IN ('ouvert', 'suspendu', 'cloture', 'archive', 'supprime')),
  ADD COLUMN etat_depuis timestamptz NOT NULL DEFAULT now();

CREATE TABLE etats_dossier (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id     uuid NOT NULL REFERENCES organisations(id),
  etat                text NOT NULL CHECK (etat IN ('ouvert', 'suspendu', 'cloture', 'archive', 'supprime')),
  action              text NOT NULL CHECK (action IN ('suspendre', 'cloturer', 'reprendre', 'archiver', 'supprimer')),
  motif_code          text,
  motif               text,
  par                 uuid REFERENCES utilisateurs(id),       -- NULL : l'archivage automatique
  le                  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX etats_dossier_organisation ON etats_dossier (organisation_id, le);
ALTER TABLE etats_dossier ENABLE ROW LEVEL SECURITY;
CREATE POLICY etats_dossier_organisation ON etats_dossier USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON etats_dossier TO courtage_app;

ALTER TABLE fichiers_personnel ADD COLUMN vide_le timestamptz;
GRANT UPDATE (lignes, anomalies, vide_le) ON fichiers_personnel TO courtage_app;

CREATE FUNCTION fichier_vidage_seulement() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.vide_le IS NOT NULL OR NEW.vide_le IS NULL
     OR NEW.lignes <> '[]'::jsonb OR NEW.anomalies <> '[]'::jsonb
     OR NEW.id <> OLD.id OR NEW.organisation_id <> OLD.organisation_id OR NEW.empreinte <> OLD.empreinte
     OR NEW.date_donnees <> OLD.date_donnees OR NEW.nom_fichier <> OLD.nom_fichier THEN
    RAISE EXCEPTION 'fichier_personnel_immuable: le fichier % ne peut qu''être vidé, une fois, à l''archivage', OLD.id;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER fichiers_personnel_vidage BEFORE UPDATE ON fichiers_personnel
  FOR EACH ROW EXECUTE FUNCTION fichier_vidage_seulement();
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
