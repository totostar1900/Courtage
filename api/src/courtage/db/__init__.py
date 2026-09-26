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

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Text, text
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


class Organisation(Base):
    __tablename__ = "organisations"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    nom: Mapped[str] = mapped_column(Text)
    pays: Mapped[str] = mapped_column(Text)
    secteur: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    telephone: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    admin_plateforme: Mapped[bool] = mapped_column(Boolean)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Adhesion(Base):
    __tablename__ = "adhesions"
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), primary_key=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), primary_key=True)
    role: Mapped[str] = mapped_column(RoleAdhesion)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FichierPersonnel(Base):
    __tablename__ = "fichiers_personnel"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    depose_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    depose_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    nom_fichier: Mapped[str] = mapped_column(Text)
    empreinte: Mapped[str] = mapped_column(Text)
    date_donnees: Mapped[date] = mapped_column(Date)
    periodicite: Mapped[str] = mapped_column(Periodicite)
    lignes: Mapped[list] = mapped_column(JSONB)
    anomalies: Mapped[list] = mapped_column(JSONB)


class Etude(Base):
    __tablename__ = "etudes"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    fichier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fichiers_personnel.id"))
    referentiel_version: Mapped[str] = mapped_column(Text)
    convention_code: Mapped[str] = mapped_column(Text)
    convention_du: Mapped[date] = mapped_column(Date)
    date_evaluation: Mapped[date] = mapped_column(Date)
    hypotheses: Mapped[dict] = mapped_column(JSONB)
    fonds_disponible: Mapped[int] = mapped_column(BigInteger)
    version_moteur: Mapped[str] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(StatutEtude)
    resultats: Mapped[dict | None] = mapped_column(JSONB)
    empreinte: Mapped[str | None] = mapped_column(Text)
    emise_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    emise_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remplace_etude_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("etudes.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EntreeJournal(Base):
    __tablename__ = "journal"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organisations.id"))
    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    action: Mapped[str] = mapped_column(Text)
    cible: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSONB)
    quand: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Sceau(Base):
    __tablename__ = "sceaux"
    numero: Mapped[str] = mapped_column(Text, primary_key=True)
    nature: Mapped[str] = mapped_column(Text)
    empreinte: Mapped[str] = mapped_column(Text)
    sceau: Mapped[str] = mapped_column(Text)
    resume: Mapped[dict] = mapped_column(JSONB)
    emis_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
