"""Socle : organisations, utilisateurs, fichiers, études, journal, sceaux.

Écrite à la main, en SQL : c'est la source de vérité du schéma, et elle porte ce
qu'un modèle SQLAlchemy ne dit pas (RLS, droits, déclencheurs).

Revision ID: 0001_socle
Revises:
"""
from alembic import op

revision = "0001_socle"
down_revision = None
branch_labels = None
depends_on = None

ROLE_APP = "courtage_app"

SCHEMA = f"""
-- Le rôle applicatif : connecté, jamais propriétaire (un propriétaire contourne la RLS).
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE_APP}') THEN
    CREATE ROLE {ROLE_APP} NOLOGIN;
  END IF;
END $$;

CREATE TYPE role_adhesion AS ENUM ('admin_client', 'lecteur_client', 'conseiller');
CREATE TYPE statut_etude AS ENUM ('brouillon', 'emise');
CREATE TYPE periodicite_salaire AS ENUM ('mensuel', 'annuel');

-- L'organisation dont la transaction s'occupe ; NULL hors contexte.
CREATE FUNCTION organisation_courante() RETURNS uuid
  LANGUAGE sql STABLE AS
  $$ SELECT NULLIF(current_setting('app.organisation_id', true), '')::uuid $$;

-- Tables d'identité : lues avant qu'une organisation soit choisie, donc hors RLS.
CREATE TABLE organisations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nom         text NOT NULL CHECK (length(trim(nom)) > 0),
  pays        char(2) NOT NULL CHECK (pays ~ '^[A-Z]{{2}}$'),
  secteur     text,
  cree_le     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE utilisateurs (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  telephone         text UNIQUE,
  email             text UNIQUE,
  admin_plateforme  boolean NOT NULL DEFAULT false,
  cree_le           timestamptz NOT NULL DEFAULT now(),
  CHECK (telephone IS NOT NULL OR email IS NOT NULL)
);

CREATE TABLE adhesions (
  utilisateur_id   uuid NOT NULL REFERENCES utilisateurs(id),
  organisation_id  uuid NOT NULL REFERENCES organisations(id),
  role             role_adhesion NOT NULL,
  cree_le          timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (utilisateur_id, organisation_id)
);

-- Un fichier déposé est un fait : gardé tel que lu, jamais modifié.
CREATE TABLE fichiers_personnel (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id  uuid NOT NULL REFERENCES organisations(id),
  depose_par       uuid NOT NULL REFERENCES utilisateurs(id),
  depose_le        timestamptz NOT NULL DEFAULT now(),
  nom_fichier      text NOT NULL,
  empreinte        char(64) NOT NULL,
  date_donnees     date NOT NULL,
  periodicite      periodicite_salaire NOT NULL,
  lignes           jsonb NOT NULL,
  anomalies        jsonb NOT NULL
);
CREATE INDEX fichiers_personnel_organisation ON fichiers_personnel (organisation_id, depose_le DESC);

CREATE TABLE etudes (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id      uuid NOT NULL REFERENCES organisations(id),
  fichier_id           uuid NOT NULL REFERENCES fichiers_personnel(id),
  referentiel_version  text NOT NULL,
  convention_code      text NOT NULL,
  convention_du        date NOT NULL,          -- la version du barème, par sa date d'effet
  date_evaluation      date NOT NULL,
  hypotheses           jsonb NOT NULL,
  fonds_disponible     bigint NOT NULL CHECK (fonds_disponible >= 0),
  version_moteur       text NOT NULL,
  statut               statut_etude NOT NULL DEFAULT 'brouillon',
  resultats            jsonb,
  empreinte            char(64),
  emise_par            uuid REFERENCES utilisateurs(id),
  emise_le             timestamptz,
  remplace_etude_id    uuid REFERENCES etudes(id),
  cree_le              timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT etude_emise_complete CHECK (
    statut = 'brouillon'
    OR (resultats IS NOT NULL AND empreinte IS NOT NULL AND emise_par IS NOT NULL AND emise_le IS NOT NULL)
  )
);
CREATE INDEX etudes_organisation ON etudes (organisation_id, date_evaluation DESC);

-- Une étude émise ne bouge plus, quel que soit le rôle : une correction est une nouvelle étude.
CREATE FUNCTION etude_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.statut = 'emise' THEN
    RAISE EXCEPTION 'etude_emise_immuable: l''étude % est émise ; créer une nouvelle étude qui la remplace', OLD.id;
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER etudes_immuables BEFORE UPDATE OR DELETE ON etudes
  FOR EACH ROW EXECUTE FUNCTION etude_immuable();

-- Le journal : qui a fait quoi, en ajout seul. Une action de plateforme n'a pas d'organisation.
CREATE TABLE journal (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  organisation_id  uuid REFERENCES organisations(id),
  utilisateur_id   uuid REFERENCES utilisateurs(id),
  action           text NOT NULL,
  cible            text NOT NULL,
  details          jsonb NOT NULL DEFAULT '{{}}',
  quand            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX journal_organisation ON journal (organisation_id, quand DESC);

-- Un sceau ne dit que ce que le papier montre ; lu par la vérification publique,
-- sans organisation, donc hors RLS.
CREATE TABLE sceaux (
  numero     text PRIMARY KEY CHECK (numero ~ '^RL-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}$'),
  nature     text NOT NULL,
  empreinte  char(64) NOT NULL,
  sceau      char(64) NOT NULL,
  resume     jsonb NOT NULL,
  emis_le    timestamptz NOT NULL DEFAULT now()
);

-- Isolation par organisation.
ALTER TABLE fichiers_personnel ENABLE ROW LEVEL SECURITY;
CREATE POLICY fichiers_personnel_organisation ON fichiers_personnel
  USING (organisation_id = organisation_courante());

ALTER TABLE etudes ENABLE ROW LEVEL SECURITY;
CREATE POLICY etudes_organisation ON etudes
  USING (organisation_id = organisation_courante());

ALTER TABLE journal ENABLE ROW LEVEL SECURITY;
CREATE POLICY journal_lecture ON journal FOR SELECT
  USING (organisation_id = organisation_courante());
CREATE POLICY journal_ecriture ON journal FOR INSERT
  WITH CHECK (organisation_id IS NULL OR organisation_id = organisation_courante());

-- Droits du rôle applicatif : le strict nécessaire.
GRANT USAGE ON SCHEMA public TO {ROLE_APP};
GRANT SELECT, INSERT, UPDATE ON organisations, utilisateurs TO {ROLE_APP};
GRANT SELECT, INSERT, UPDATE, DELETE ON adhesions TO {ROLE_APP};
GRANT SELECT, INSERT ON fichiers_personnel, journal, sceaux TO {ROLE_APP};
GRANT SELECT, INSERT, UPDATE, DELETE ON etudes TO {ROLE_APP};
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement : une migration corrective remplace un retour arrière.")
