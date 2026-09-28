"""L'inscription en libre-service et son activation par le courtier ; les messages du dossier.

- `organisations.activation` : `en_attente` (inscrit, pas encore vérifié), `confirmee`, `refusee`. Les dossiers
  ouverts par la plateforme, et tous ceux d'avant, sont `confirmee`. La décision est tracée : quand, par qui, ce qui a
  été vérifié (`activation_verification`), et le motif d'un refus.
- L'identité de l'entreprise : RCCM (tel que saisi, et normalisé pour l'unicité), taille, adresse, ville.
- `justificatifs` : le document RCCM, déposé par le client (sous RLS).
- `codes_verification` : les codes à usage unique de l'inscription, pour un téléphone ou un courriel encore inconnus
  (hors RLS : aucune organisation n'existe encore).
- `messages_dossier` : le fil entre l'entreprise et son conseiller (sous RLS, append-only).
- L'effacement d'une inscription jamais confirmée (30 jours, ou à la demande du client) : les départs, les lectures
  de textes et les demandes de mandat, qui ne s'effacent jamais d'ordinaire, s'effacent ALORS seulement — un
  déclencheur refuse tout effacement dans un dossier confirmé.

Conception : docs/specs/2026-09-28-inscription-et-courtage-seul-design.md.

Revision ID: 0023_activation
Revises: 0022_mandats
"""
from alembic import op

revision = "0023_activation"
down_revision = "0022_mandats"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE organisations
  ADD COLUMN activation text NOT NULL DEFAULT 'confirmee' CHECK (activation IN ('en_attente', 'confirmee', 'refusee')),
  ADD COLUMN rccm text,
  ADD COLUMN rccm_normalise text,
  ADD COLUMN taille text,
  ADD COLUMN adresse text,
  ADD COLUMN ville text,
  ADD COLUMN activation_demandee_le timestamptz,
  ADD COLUMN activation_decidee_le timestamptz,
  ADD COLUMN activation_par uuid REFERENCES utilisateurs(id),
  ADD COLUMN activation_verification jsonb,
  ADD COLUMN activation_motif text,
  ADD CONSTRAINT inscription_complete CHECK (activation <> 'en_attente' OR (rccm_normalise IS NOT NULL
                                                                        AND activation_demandee_le IS NOT NULL));
-- Une entreprise, un dossier vivant : un RCCM ne se réinscrit pas tant que son dossier existe.
CREATE UNIQUE INDEX organisations_rccm ON organisations (rccm_normalise)
  WHERE rccm_normalise IS NOT NULL AND etat <> 'supprime';

ALTER TABLE utilisateurs ADD COLUMN email_verifie_le timestamptz;

CREATE TABLE codes_verification (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nature       text NOT NULL CHECK (nature IN ('telephone', 'courriel')),
  cible        text NOT NULL,
  code_hash    text NOT NULL,
  cree_le      timestamptz NOT NULL DEFAULT now(),
  expire_le    timestamptz NOT NULL,
  tentatives   integer NOT NULL DEFAULT 0,
  utilise_le   timestamptz
);
CREATE INDEX codes_verification_cible ON codes_verification (nature, cible, cree_le DESC);
GRANT SELECT, INSERT, UPDATE (tentatives, utilise_le) ON codes_verification TO courtage_app;

CREATE TABLE justificatifs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id  uuid NOT NULL REFERENCES organisations(id),
  nature           text NOT NULL CHECK (nature IN ('rccm')),
  nom_fichier      text NOT NULL,
  type_contenu     text NOT NULL,
  contenu          bytea NOT NULL,
  empreinte        text NOT NULL,
  depose_par       uuid NOT NULL REFERENCES utilisateurs(id),
  depose_le        timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE justificatifs ENABLE ROW LEVEL SECURITY;
CREATE POLICY justificatifs_organisation ON justificatifs USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT, DELETE ON justificatifs TO courtage_app;

CREATE TABLE messages_dossier (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id  uuid NOT NULL REFERENCES organisations(id),
  auteur           uuid NOT NULL REFERENCES utilisateurs(id),
  cote             text NOT NULL CHECK (cote IN ('entreprise', 'courtier')),
  texte            text NOT NULL CHECK (length(texte) BETWEEN 1 AND 4000),
  le               timestamptz NOT NULL DEFAULT now(),
  lu_le            timestamptz
);
CREATE INDEX messages_dossier_organisation ON messages_dossier (organisation_id, le);
ALTER TABLE messages_dossier ENABLE ROW LEVEL SECURITY;
CREATE POLICY messages_dossier_organisation ON messages_dossier USING (organisation_id = organisation_courante());
-- Un message ne se modifie pas ; seul « lu le » se pose, par l'autre côté. Il part avec le dossier effacé.
GRANT SELECT, INSERT, UPDATE (lu_le), DELETE ON messages_dossier TO courtage_app;

CREATE FUNCTION effacement_d_inscription() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (SELECT activation FROM organisations WHERE id = OLD.organisation_id) = 'confirmee' THEN
    RAISE EXCEPTION 'effacement_refuse: % d''un dossier confirmé ne s''efface pas', TG_TABLE_NAME;
  END IF;
  RETURN OLD;
END $$;
GRANT DELETE ON prestations, extractions, mandats_courtage TO courtage_app;
CREATE TRIGGER prestations_effacement BEFORE DELETE ON prestations
  FOR EACH ROW EXECUTE FUNCTION effacement_d_inscription();
CREATE TRIGGER extractions_effacement BEFORE DELETE ON extractions
  FOR EACH ROW EXECUTE FUNCTION effacement_d_inscription();
CREATE TRIGGER mandats_courtage_effacement BEFORE DELETE ON mandats_courtage
  FOR EACH ROW EXECUTE FUNCTION effacement_d_inscription();
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
