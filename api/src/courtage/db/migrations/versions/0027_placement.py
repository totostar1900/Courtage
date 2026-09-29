"""La clôture du placement : la police, ses pièces, les appels de prime et les virements déclarés ; le registre des
comptes bancaires des assureurs.

- `comptes_assureurs` (plateforme, sans organisation, hors RLS) : le compte en vigueur de chaque assureur, tenu par le
  courtier ; chaque ligne porte son contre-appel. Un changement ajoute une ligne (`remplace_id`) ; rien ne se modifie.
- `polices` : le contrat placé chez l'assureur ; seuls le numéro et la signature se posent après coup.
- `pieces_police` : les documents (police, copie signée, avenant, appel, avis de virement, quittance, relevé), en
  ajout seul. Un relevé porte sa date et le montant du fonds.
- `appels_prime` : l'appel de l'assureur et les coordonnées bancaires qu'il porte, confrontées au registre
  (`controle`) ; puis le contre-appel, la déclaration du virement, la confirmation de l'encaissement.

La plateforme ne paie rien : elle trace. Conception : docs/specs/2026-09-29-cloture-du-placement-design.md.

Revision ID: 0027_placement
Revises: 0026_avis
"""
from alembic import op

revision = "0027_placement"
down_revision = "0026_avis"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE comptes_assureurs (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assureur            text NOT NULL,
  assureur_cle        text NOT NULL,
  banque              text NOT NULL,
  titulaire           text NOT NULL,
  iban                text NOT NULL,
  bic                 text,
  verifie_aupres      text NOT NULL,
  verifie_telephone   text NOT NULL,
  verifie_le          date NOT NULL,
  note                text,
  remplace_id         uuid UNIQUE REFERENCES comptes_assureurs(id),
  enregistre_par      uuid NOT NULL REFERENCES utilisateurs(id),
  enregistre_le       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX comptes_assureurs_cle ON comptes_assureurs (assureur_cle, enregistre_le DESC);
GRANT SELECT, INSERT ON comptes_assureurs TO courtage_app;

CREATE TABLE polices (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id  uuid NOT NULL REFERENCES organisations(id),
  choix_id         uuid UNIQUE REFERENCES choix_fiche(id),
  assureur         text NOT NULL,
  numero_police    text,
  date_effet       date NOT NULL,
  periodicite      text NOT NULL CHECK (periodicite IN ('annuelle', 'semestrielle', 'trimestrielle', 'mensuelle', 'unique')),
  signee_le        date,
  signee_par       uuid REFERENCES utilisateurs(id),
  cree_par         uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le          timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE polices ENABLE ROW LEVEL SECURITY;
CREATE POLICY polices_organisation ON polices USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT, UPDATE (numero_police, signee_le, signee_par) ON polices TO courtage_app;

CREATE TABLE appels_prime (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id      uuid NOT NULL REFERENCES organisations(id),
  police_id            uuid NOT NULL REFERENCES polices(id),
  reference            text NOT NULL,
  montant              bigint NOT NULL CHECK (montant > 0),
  echeance             date NOT NULL,
  premiere             boolean NOT NULL DEFAULT false,
  banque               text NOT NULL,
  titulaire            text NOT NULL,
  iban                 text NOT NULL,
  bic                  text,
  compte_id            uuid REFERENCES comptes_assureurs(id),
  controle             text NOT NULL CHECK (controle IN ('conforme', 'modifie', 'non_enregistre')),
  contre_appel         jsonb,
  contre_appel_le      timestamptz,
  vire_le              date,
  montant_vire         bigint CHECK (montant_vire > 0),
  reference_virement   text,
  declare_par          uuid REFERENCES utilisateurs(id),
  declare_le           timestamptz,
  encaisse_le          date,
  confirme_par         uuid REFERENCES utilisateurs(id),
  confirme_le          timestamptz,
  cree_par             uuid NOT NULL REFERENCES utilisateurs(id),
  cree_le              timestamptz NOT NULL DEFAULT now(),
  UNIQUE (police_id, reference),
  CONSTRAINT appel_confirme_apres_controle CHECK (controle = 'conforme' OR confirme_le IS NULL OR contre_appel IS NOT NULL)
);
CREATE UNIQUE INDEX appels_prime_une_premiere ON appels_prime (police_id) WHERE premiere;
ALTER TABLE appels_prime ENABLE ROW LEVEL SECURITY;
CREATE POLICY appels_prime_organisation ON appels_prime USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT, UPDATE (contre_appel, contre_appel_le, vire_le, montant_vire, reference_virement, declare_par,
                              declare_le, encaisse_le, confirme_par, confirme_le) ON appels_prime TO courtage_app;

CREATE TABLE pieces_police (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id  uuid NOT NULL REFERENCES organisations(id),
  police_id        uuid NOT NULL REFERENCES polices(id),
  appel_id         uuid REFERENCES appels_prime(id),
  nature           text NOT NULL CHECK (nature IN ('police', 'police_signee', 'avenant', 'appel', 'avis_virement',
                                                   'quittance', 'releve')),
  nom_fichier      text NOT NULL,
  type_contenu     text NOT NULL,
  contenu          bytea NOT NULL,
  empreinte        char(64) NOT NULL,
  releve_le        date,
  montant_fonds    bigint,
  depose_par       uuid NOT NULL REFERENCES utilisateurs(id),
  depose_le        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT releve_complet CHECK (nature <> 'releve' OR (releve_le IS NOT NULL AND montant_fonds IS NOT NULL))
);
ALTER TABLE pieces_police ENABLE ROW LEVEL SECURITY;
CREATE POLICY pieces_police_organisation ON pieces_police USING (organisation_id = organisation_courante());
GRANT SELECT, INSERT ON pieces_police TO courtage_app;
"""


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("L'historique avance seulement.")
