"""Les réponses des assureurs au cahier des charges, et le choix de l'entreprise.

Une réponse reprend la grille du cahier (taux garanti, participation, frais,
délai de paiement, transfert…), l'offre de l'assureur en PDF si elle est jointe,
et la date de réception. Elle est une ÉCRITURE : corrigée ou retirée par une
nouvelle ligne (`remplace_id`), jamais modifiée. Le choix est un acte de
l'entreprise, un par cahier, motivé quand il ne se porte pas sur l'offre
conforme la moins chère.

Revision ID: 0013_reponses_assureurs
Revises: 0012_fiche_de_calcul
"""
from alembic import op

revision = "0013_reponses_assureurs"
down_revision = "0012_fiche_de_calcul"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE reponses_fiche (
  id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id           uuid NOT NULL REFERENCES organisations(id),
  fiche_id                  uuid NOT NULL REFERENCES fiches_regime(id),
  assureur                  text NOT NULL CHECK (length(trim(assureur)) > 0),
  recue_le                  date NOT NULL,
  taux_garanti              numeric NOT NULL CHECK (taux_garanti BETWEEN -0.05 AND 0.2),
  participation_benefices   numeric NOT NULL CHECK (participation_benefices BETWEEN 0 AND 1),
  frais_sur_cotisations     numeric NOT NULL CHECK (frais_sur_cotisations BETWEEN 0 AND 0.2),
  frais_sur_encours         numeric NOT NULL CHECK (frais_sur_encours BETWEEN 0 AND 0.2),
  delai_paiement_jours      integer CHECK (delai_paiement_jours BETWEEN 1 AND 365),
  transfert_preavis_mois    integer CHECK (transfert_preavis_mois BETWEEN 0 AND 60),
  transfert_penalite        numeric CHECK (transfert_penalite BETWEEN 0 AND 1),
  accepte_etude_plateforme  boolean,
  reporting_annuel          boolean,
  historique_participation  text,
  commentaire               text,
  offre_nom_fichier         text,
  offre_contenu             bytea,
  offre_empreinte           char(64),
  remplace_id               uuid UNIQUE REFERENCES reponses_fiche(id),
  retrait                   boolean NOT NULL DEFAULT false,
  motif_correction          text,
  saisie_par                uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le                   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT correction_motivee CHECK (remplace_id IS NULL OR length(trim(coalesce(motif_correction, ''))) > 0),
  CONSTRAINT retrait_d_une_ligne CHECK (NOT retrait OR remplace_id IS NOT NULL)
);

CREATE TABLE choix_fiche (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id   uuid NOT NULL REFERENCES organisations(id),
  fiche_id          uuid NOT NULL UNIQUE REFERENCES fiches_regime(id),
  reponse_id        uuid NOT NULL REFERENCES reponses_fiche(id),
  motif             text,
  choisi_par        uuid NOT NULL REFERENCES utilisateurs(id),
  choisi_le         timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE reponses_fiche ENABLE ROW LEVEL SECURITY;
CREATE POLICY reponses_fiche_organisation ON reponses_fiche USING (organisation_id = organisation_courante());
ALTER TABLE choix_fiche ENABLE ROW LEVEL SECURITY;
CREATE POLICY choix_fiche_organisation ON choix_fiche USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON reponses_fiche, choix_fiche TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
