"""Courtage : le dossier de prise en charge d'une prestation (spec prestations §3).

En courtage seulement, la plateforme porte la demande de paiement auprès de
l'assureur. Le dossier suit des étapes, chacune une ligne (`dossiers_evenements`) :
déclaré, à compléter, resoumis, vérifié, transmis, payé, refusé, identité effacée.

L'IDENTITÉ du bénéficiaire vit dans `beneficiaires`, et nulle part ailleurs ; les
pièces jointes et le PDF transmis, qui la contiennent aussi, dans
`pieces_dossier`. Ces deux tables sont les seules où le rôle applicatif peut
SUPPRIMER : l'identité est effacée douze mois après le paiement. Le sceau du
dossier (table publique `sceaux`) ne porte aucune identité ; il reste, et le
numéro PC-… se vérifie encore après l'effacement.

Revision ID: 0011_prise_en_charge
Revises: 0010_prestations
"""
from alembic import op

revision = "0011_prise_en_charge"
down_revision = "0010_prestations"
branch_labels = None
depends_on = None

SCHEMA = """
-- Un dossier de prise en charge a son propre préfixe : PC-…, à côté des rapports et cahiers RL-….
ALTER TABLE sceaux DROP CONSTRAINT sceaux_numero_check;
ALTER TABLE sceaux ADD CONSTRAINT sceaux_numero_check CHECK (numero ~ '^(RL|PC)-[A-Z0-9]{4}-[A-Z0-9]{4}$');

CREATE TYPE etape_dossier AS ENUM ('declare', 'a_completer', 'resoumis', 'verifie', 'transmis', 'paye', 'refuse',
                                   'identite_effacee');

CREATE TABLE dossiers_prise_en_charge (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id   uuid NOT NULL REFERENCES organisations(id),
  matricule         text NOT NULL,
  date_depart       date NOT NULL,
  prestation_id     uuid NOT NULL REFERENCES prestations(id),
  contrat_id        uuid NOT NULL REFERENCES contrats(id),
  montant_demande   bigint NOT NULL CHECK (montant_demande > 0),
  cree_par          uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organisation_id, matricule, date_depart)
);

CREATE TABLE dossiers_evenements (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id   uuid NOT NULL REFERENCES organisations(id),
  dossier_id        uuid NOT NULL REFERENCES dossiers_prise_en_charge(id),
  etape             etape_dossier NOT NULL,
  le                date NOT NULL,
  montant           bigint CHECK (montant >= 0),
  motif             text,
  numero            text REFERENCES sceaux(numero),
  par               uuid REFERENCES utilisateurs(id),
  cree_le           timestamptz NOT NULL DEFAULT clock_timestamp(),
  -- Seul l'effacement programmé agit sans personne.
  CONSTRAINT etape_signee CHECK (par IS NOT NULL OR etape = 'identite_effacee')
);
CREATE INDEX dossiers_evenements_dossier ON dossiers_evenements (dossier_id, cree_le);

CREATE TABLE beneficiaires (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id       uuid NOT NULL REFERENCES organisations(id),
  dossier_id            uuid NOT NULL UNIQUE REFERENCES dossiers_prise_en_charge(id),
  qualite               text NOT NULL CHECK (qualite IN ('salarie', 'ayant_droit')),
  nom                   text NOT NULL CHECK (length(trim(nom)) > 0),
  prenoms               text,
  date_naissance        date,
  piece_type            text NOT NULL CHECK (piece_type IN ('cni', 'passeport', 'carte_sejour', 'autre')),
  piece_numero          text NOT NULL CHECK (length(trim(piece_numero)) > 0),
  telephone             text,
  moyen_paiement        text NOT NULL CHECK (moyen_paiement IN ('virement', 'mobile_money', 'cheque')),
  coordonnees_paiement  text,
  cree_le               timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE pieces_dossier (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id   uuid NOT NULL REFERENCES organisations(id),
  dossier_id        uuid NOT NULL REFERENCES dossiers_prise_en_charge(id),
  nature            text NOT NULL CHECK (nature IN ('certificat_travail', 'attestation_depart', 'calcul_signe',
                                                    'piece_identite', 'rib', 'autre', 'dossier_scelle')),
  nom_fichier       text NOT NULL,
  type_contenu      text NOT NULL,
  contenu           bytea NOT NULL,
  empreinte         char(64) NOT NULL,
  cree_par          uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le           timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE dossiers_prise_en_charge ENABLE ROW LEVEL SECURITY;
CREATE POLICY dossiers_organisation ON dossiers_prise_en_charge USING (organisation_id = organisation_courante());
ALTER TABLE dossiers_evenements ENABLE ROW LEVEL SECURITY;
CREATE POLICY dossiers_evenements_organisation ON dossiers_evenements USING (organisation_id = organisation_courante());
ALTER TABLE beneficiaires ENABLE ROW LEVEL SECURITY;
CREATE POLICY beneficiaires_organisation ON beneficiaires USING (organisation_id = organisation_courante());
ALTER TABLE pieces_dossier ENABLE ROW LEVEL SECURITY;
CREATE POLICY pieces_dossier_organisation ON pieces_dossier USING (organisation_id = organisation_courante());

GRANT SELECT, INSERT ON dossiers_prise_en_charge, dossiers_evenements TO courtage_app;
GRANT SELECT, INSERT, DELETE ON beneficiaires, pieces_dossier TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
