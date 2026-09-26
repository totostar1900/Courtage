"""Accès à la base.

Le schéma est défini par les migrations (`db/migrations/versions`) ; les modèles
ci-dessous le décrivent pour le code applicatif, et un test vérifie qu'ils
disent la même chose.

Toute lecture ou écriture de données d'un client se fait dans une transaction
ouverte par `contexte(connexion, organisation_id)` : la RLS ne montre que
cette organisation, et le réglage disparaît avec la transaction.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, BigInteger, Boolean, Date, LargeBinary, Numeric, DateTime, FetchedValue, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def contexte(connexion, organisation_id: uuid.UUID) -> None:
    """Place la transaction en cours dans le contexte d'une organisation."""
    connexion.execute(text("SELECT set_config('app.organisation_id', :o, true)"), {"o": str(organisation_id)})


RoleAdhesion = ENUM("admin_client", "lecteur_client", "conseiller", name="role_adhesion", create_type=False)
StatutEtude = ENUM("brouillon", "emise", name="statut_etude", create_type=False)
Periodicite = ENUM("mensuel", "annuel", name="periodicite_salaire", create_type=False)
Fondement = ENUM("accord_entreprise", "contrat_travail", "usage", "decision_direction",
                 name="fondement_bareme", create_type=False)
StatutBareme = ENUM("propose", "valide", name="statut_bareme", create_type=False)
ModeRemuneration = ENUM("honoraires", "commission", "mixte", name="mode_remuneration", create_type=False)


class Organisation(Base):
    __tablename__ = "organisations"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    nom: Mapped[str] = mapped_column(Text)
    pays: Mapped[str] = mapped_column(Text)
    secteur: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    telephone: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    admin_plateforme: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    nom_affiche: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Adhesion(Base):
    __tablename__ = "adhesions"
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), primary_key=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), primary_key=True)
    role: Mapped[str] = mapped_column(RoleAdhesion)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class FichierPersonnel(Base):
    __tablename__ = "fichiers_personnel"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    depose_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    depose_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    nom_fichier: Mapped[str] = mapped_column(Text)
    empreinte: Mapped[str] = mapped_column(Text)
    date_donnees: Mapped[date] = mapped_column(Date)
    periodicite: Mapped[str] = mapped_column(Periodicite)
    lignes: Mapped[list] = mapped_column(JSONB)
    anomalies: Mapped[list] = mapped_column(JSONB)


class Etude(Base):
    __tablename__ = "etudes"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    fichier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fichiers_personnel.id"))
    referentiel_version: Mapped[str] = mapped_column(Text)
    convention_code: Mapped[str] = mapped_column(Text)
    convention_du: Mapped[date] = mapped_column(Date)
    date_evaluation: Mapped[date] = mapped_column(Date)
    hypotheses: Mapped[dict] = mapped_column(JSONB)
    fonds_disponible: Mapped[int] = mapped_column(BigInteger)
    version_moteur: Mapped[str] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(StatutEtude, server_default=FetchedValue())
    resultats: Mapped[dict | None] = mapped_column(JSONB)
    empreinte: Mapped[str | None] = mapped_column(Text)
    emise_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    emise_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remplace_etude_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("etudes.id"))
    conditions_remuneration_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conditions_remuneration.id"))
    honoraires_ht: Mapped[int | None] = mapped_column(BigInteger)
    bareme_entreprise_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("baremes_entreprise.id"))
    regime_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regimes_versions.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class ConditionsRemuneration(Base):
    __tablename__ = "conditions_remuneration"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    en_vigueur_du: Mapped[date] = mapped_column(Date)
    mode: Mapped[str] = mapped_column(ModeRemuneration)
    honoraires_etude_ifc: Mapped[int] = mapped_column(BigInteger)
    honoraires_par_salarie: Mapped[int] = mapped_column(BigInteger)
    commission_bps: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class BaremeEntreprise(Base):
    __tablename__ = "baremes_entreprise"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    libelle: Mapped[str] = mapped_column(Text)
    fondement: Mapped[str] = mapped_column(Fondement)
    document_reference: Mapped[str] = mapped_column(Text)
    convention_code: Mapped[str] = mapped_column(Text)
    en_vigueur_du: Mapped[date] = mapped_column(Date)
    en_vigueur_au: Mapped[date | None] = mapped_column(Date)
    bareme: Mapped[dict] = mapped_column(JSONB)
    statut: Mapped[str] = mapped_column(StatutBareme, server_default=FetchedValue())
    propose_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    valide_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    valide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())

    def en_vigueur(self, jour: date) -> bool:
        return self.en_vigueur_du <= jour and (self.en_vigueur_au is None or jour <= self.en_vigueur_au)


class EntreeJournal(Base):
    """En ajout seul, écrit par `services.journaliser`. Sans RETURNING : une ligne
    de plateforme (sans organisation) ne passerait pas la politique de lecture."""
    __tablename__ = "journal"
    __table_args__ = {"implicit_returning": False}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organisations.id"))
    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    action: Mapped[str] = mapped_column(Text)
    cible: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSONB, server_default=FetchedValue())
    quand: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Sceau(Base):
    __tablename__ = "sceaux"
    numero: Mapped[str] = mapped_column(Text, primary_key=True)
    nature: Mapped[str] = mapped_column(Text)
    empreinte: Mapped[str] = mapped_column(Text)
    sceau: Mapped[str] = mapped_column(Text)
    resume: Mapped[dict] = mapped_column(JSONB)
    empreinte_document: Mapped[str | None] = mapped_column(Text)
    sceau_document: Mapped[str | None] = mapped_column(Text)
    emis_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    etude_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("etudes.id"))
    fiche_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fiches_regime.id"))
    numero: Mapped[str] = mapped_column(ForeignKey("sceaux.numero"))
    type_contenu: Mapped[str] = mapped_column(Text, server_default=FetchedValue())
    contenu: Mapped[bytes] = mapped_column(LargeBinary)
    empreinte_document: Mapped[str] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


StatutVersion = ENUM("analyse", "adoptee", name="statut_version_regime", create_type=False)
BaseSalaire = ENUM("dernier", "moyenne_12_mois", name="base_salaire", create_type=False)
Arrondi = ENUM("annees", "mois", name="arrondi_anciennete", create_type=False)


class Regime(Base):
    __tablename__ = "regimes"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    nom: Mapped[str] = mapped_column(Text)
    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class VersionRegime(Base):
    __tablename__ = "regimes_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    regime_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regimes.id"))
    numero: Mapped[int] = mapped_column(Integer)
    en_vigueur_du: Mapped[date] = mapped_column(Date)
    fondement: Mapped[str] = mapped_column(Fondement)
    document_reference: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(StatutVersion, server_default=FetchedValue())
    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    adoptee_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    adoptee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    non_conformite_acceptee: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    constats_a_l_adoption: Mapped[list | None] = mapped_column(JSONB)


class CategorieRegime(Base):
    __tablename__ = "regimes_categories"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regimes_versions.id"))
    categorie: Mapped[str] = mapped_column(Text)
    convention_code: Mapped[str] = mapped_column(Text)
    bareme: Mapped[dict] = mapped_column(JSONB)
    anciennete_minimale: Mapped[int] = mapped_column(Integer)
    plafond_mois: Mapped[float | None] = mapped_column(Numeric(asdecimal=False))
    arrondi: Mapped[str] = mapped_column(Arrondi)
    base_salaire: Mapped[str] = mapped_column(BaseSalaire)
    avec_primes: Mapped[bool] = mapped_column(Boolean)
    evenements: Mapped[list[str]] = mapped_column(ARRAY(Text))


class FicheRegime(Base):
    __tablename__ = "fiches_regime"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    etude_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("etudes.id"))
    regime_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regimes_versions.id"))
    date_limite_reponse: Mapped[date] = mapped_column(Date)
    conditions: Mapped[dict] = mapped_column(JSONB)
    contenu: Mapped[dict] = mapped_column(JSONB)
    empreinte: Mapped[str] = mapped_column(Text)
    emise_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    emise_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
