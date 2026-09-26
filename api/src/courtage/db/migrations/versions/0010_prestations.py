"""Prestations : un départ, sans identité (spec prestations §2, §4, §5).

Une ligne par départ — en retraite (il ouvre droit à l'IFC) ou non (il mesure
la rotation réelle) — dans les deux services, courtage ou comparaison. Aucune
colonne ne nomme une personne : le matricule relie la ligne au fichier du
personnel, et l'identité d'un bénéficiaire, en courtage seulement, aura sa
propre table (P3).

Le montant DÛ est recalculé par la plateforme avec la règle en vigueur au
départ, et la ligne garde le calcul (`calcul`) ; le montant VERSÉ est déclaré et
peut dépasser le dû. Une prestation est une ÉCRITURE : le rôle applicatif n'a
ni UPDATE ni DELETE ; une correction est une nouvelle ligne qui en remplace une
autre (`remplace_id`, une seule fois) et dit pourquoi, une annulation aussi.

Revision ID: 0010_prestations
Revises: 0009_contrats
"""
from alembic import op

revision = "0010_prestations"
down_revision = "0009_contrats"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TYPE motif_depart AS ENUM ('retraite', 'demission', 'licenciement', 'deces', 'autre');

CREATE TABLE prestations (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id             uuid NOT NULL REFERENCES organisations(id),
  matricule                   text NOT NULL CHECK (length(trim(matricule)) > 0),
  categorie                   text,
  motif                       motif_depart NOT NULL,
  date_naissance              date,
  date_embauche               date NOT NULL,
  date_depart                 date NOT NULL,
  salaire_mensuel_reference   bigint NOT NULL CHECK (salaire_mensuel_reference >= 0),
  du                          bigint NOT NULL CHECK (du >= 0),
  calcul                      jsonb NOT NULL,
  verse                       bigint CHECK (verse >= 0),
  part_fonds_demandee         bigint CHECK (part_fonds_demandee >= 0),
  part_fonds_payee            bigint CHECK (part_fonds_payee >= 0),
  payee_le                    date,
  soldee                      boolean NOT NULL DEFAULT false,
  origine                     text NOT NULL CHECK (origine IN ('saisie', 'import')),
  import_id                   uuid,
  note                        text,
  remplace_id                 uuid UNIQUE REFERENCES prestations(id),
  annulation                  boolean NOT NULL DEFAULT false,
  motif_correction            text,
  cree_par                    uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le                     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT depart_apres_embauche CHECK (date_depart >= date_embauche),
  CONSTRAINT naissance_avant_embauche CHECK (date_naissance IS NULL OR date_naissance < date_embauche),
  CONSTRAINT correction_motivee CHECK (remplace_id IS NULL OR length(trim(coalesce(motif_correction, ''))) > 0),
  CONSTRAINT annulation_d_une_ligne CHECK (NOT annulation OR remplace_id IS NOT NULL),
  CONSTRAINT paiement_date CHECK (part_fonds_payee IS NULL OR payee_le IS NOT NULL)
);
CREATE INDEX prestations_organisation_depart ON prestations (organisation_id, date_depart);

ALTER TABLE prestations ENABLE ROW LEVEL SECURITY;
CREATE POLICY prestations_organisation ON prestations USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON prestations TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
