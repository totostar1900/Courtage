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


RoleAdhesion = ENUM("admin_client", "contributeur_client", "lecteur_client", "conseiller", name="role_adhesion",
                    create_type=False)
StatutEtude = ENUM("brouillon", "emise", name="statut_etude", create_type=False)
Periodicite = ENUM("mensuel", "annuel", name="periodicite_salaire", create_type=False)
Fondement = ENUM("accord_entreprise", "contrat_travail", "usage", "decision_direction",
                 name="fondement_bareme", create_type=False)
StatutBareme = ENUM("propose", "valide", name="statut_bareme", create_type=False)
MotifDepart = ENUM("retraite", "demission", "licenciement", "deces", "autre", name="motif_depart", create_type=False)
EtapeDossier = ENUM("declare", "a_completer", "resoumis", "verifie", "transmis", "paye", "refuse",
                    "identite_effacee", name="etape_dossier", create_type=False)
ServiceContrat = ENUM("courtage", "comparaison", name="service_contrat", create_type=False)


class Organisation(Base):
    __tablename__ = "organisations"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    nom: Mapped[str] = mapped_column(Text)
    pays: Mapped[str] = mapped_column(Text)
    secteur: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    # Le cycle de vie : ouvert, suspendu, cloture, archive, supprime (histoire dans `etats_dossier`).
    etat: Mapped[str] = mapped_column(Text, server_default=FetchedValue())
    etat_depuis: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    # L'inscription en libre-service : en_attente jusqu'à la vérification du courtier (spec 2026-09-28).
    activation: Mapped[str] = mapped_column(Text, server_default=FetchedValue())
    rccm: Mapped[str | None] = mapped_column(Text)
    rccm_normalise: Mapped[str | None] = mapped_column(Text)
    taille: Mapped[str | None] = mapped_column(Text)
    adresse: Mapped[str | None] = mapped_column(Text)
    ville: Mapped[str | None] = mapped_column(Text)
    activation_demandee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activation_decidee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activation_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    activation_verification: Mapped[dict | None] = mapped_column(JSONB)
    activation_motif: Mapped[str | None] = mapped_column(Text)


class EtatDossier(Base):
    """Un changement d'état du dossier, motivé, daté, signé (`par` vide : l'archivage automatique)."""
    __tablename__ = "etats_dossier"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    etat: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    motif_code: Mapped[str | None] = mapped_column(Text)
    motif: Mapped[str | None] = mapped_column(Text)
    par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    telephone: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    admin_plateforme: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    nom_affiche: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    email_verifie_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    conditions_version: Mapped[str | None] = mapped_column(Text)
    conditions_acceptees_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avis_courriel: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    avis_whatsapp: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())


class CodeVerification(Base):
    """Un code à usage unique de l'inscription, pour un téléphone ou un courriel pas encore inscrits."""
    __tablename__ = "codes_verification"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    nature: Mapped[str] = mapped_column(Text)
    cible: Mapped[str] = mapped_column(Text)
    code_hash: Mapped[str] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tentatives: Mapped[int] = mapped_column(Integer, server_default=FetchedValue())
    utilise_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Justificatif(Base):
    __tablename__ = "justificatifs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    nature: Mapped[str] = mapped_column(Text)
    nom_fichier: Mapped[str] = mapped_column(Text)
    type_contenu: Mapped[str] = mapped_column(Text)
    contenu: Mapped[bytes] = mapped_column(LargeBinary)
    empreinte: Mapped[str] = mapped_column(Text)
    depose_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    depose_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class MessageDossier(Base):
    __tablename__ = "messages_dossier"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    auteur: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cote: Mapped[str] = mapped_column(Text)
    texte: Mapped[str] = mapped_column(Text)
    le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    lu_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Adhesion(Base):
    __tablename__ = "adhesions"
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), primary_key=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), primary_key=True)
    role: Mapped[str] = mapped_column(RoleAdhesion)
    fonction: Mapped[str | None] = mapped_column(Text)            # libre : DRH, DG, DAF…
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
    vide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))   # vidé à l'archivage du dossier


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
    bareme_entreprise_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("baremes_entreprise.id"))
    regime_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regimes_versions.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Contrat(Base):
    """Le service rendu au client à partir d'une date : courtage (mandat) ou comparaison."""
    __tablename__ = "contrats"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    en_vigueur_du: Mapped[date] = mapped_column(Date)
    service: Mapped[str] = mapped_column(ServiceContrat)
    assureur: Mapped[str | None] = mapped_column(Text)
    numero_police: Mapped[str | None] = mapped_column(Text)
    date_effet_police: Mapped[date | None] = mapped_column(Date)
    mandat_reference: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Prestation(Base):
    """Un départ, sans identité. Une écriture : corrigée par une nouvelle ligne (`remplace_id`), jamais modifiée."""
    __tablename__ = "prestations"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    matricule: Mapped[str] = mapped_column(Text)
    categorie: Mapped[str | None] = mapped_column(Text)
    motif: Mapped[str] = mapped_column(MotifDepart)
    date_naissance: Mapped[date | None] = mapped_column(Date)
    date_embauche: Mapped[date] = mapped_column(Date)
    date_depart: Mapped[date] = mapped_column(Date)
    salaire_mensuel_reference: Mapped[int] = mapped_column(BigInteger)
    du: Mapped[int] = mapped_column(BigInteger)
    calcul: Mapped[dict] = mapped_column(JSONB)
    verse: Mapped[int | None] = mapped_column(BigInteger)
    part_fonds_demandee: Mapped[int | None] = mapped_column(BigInteger)
    part_fonds_payee: Mapped[int | None] = mapped_column(BigInteger)
    payee_le: Mapped[date | None] = mapped_column(Date)
    soldee: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    origine: Mapped[str] = mapped_column(Text)
    import_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    note: Mapped[str | None] = mapped_column(Text)
    remplace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("prestations.id"))
    annulation: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    motif_correction: Mapped[str | None] = mapped_column(Text)
    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class DossierPriseEnCharge(Base):
    """Courtage : la demande de paiement d'une prestation à l'assureur. Ses étapes sont des lignes."""
    __tablename__ = "dossiers_prise_en_charge"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    matricule: Mapped[str] = mapped_column(Text)
    date_depart: Mapped[date] = mapped_column(Date)
    prestation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prestations.id"))
    contrat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contrats.id"))
    montant_demande: Mapped[int] = mapped_column(BigInteger)
    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class EvenementDossier(Base):
    __tablename__ = "dossiers_evenements"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    dossier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dossiers_prise_en_charge.id"))
    etape: Mapped[str] = mapped_column(EtapeDossier)
    le: Mapped[date] = mapped_column(Date)
    montant: Mapped[int | None] = mapped_column(BigInteger)
    motif: Mapped[str | None] = mapped_column(Text)
    numero: Mapped[str | None] = mapped_column(ForeignKey("sceaux.numero"))
    par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Beneficiaire(Base):
    """L'identité d'un bénéficiaire : en courtage seulement, ici seulement, effacée 12 mois après le paiement."""
    __tablename__ = "beneficiaires"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    dossier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dossiers_prise_en_charge.id"))
    qualite: Mapped[str] = mapped_column(Text)
    nom: Mapped[str] = mapped_column(Text)
    prenoms: Mapped[str | None] = mapped_column(Text)
    date_naissance: Mapped[date | None] = mapped_column(Date)
    piece_type: Mapped[str] = mapped_column(Text)
    piece_numero: Mapped[str] = mapped_column(Text)
    telephone: Mapped[str | None] = mapped_column(Text)
    moyen_paiement: Mapped[str] = mapped_column(Text)
    coordonnees_paiement: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class PieceDossier(Base):
    __tablename__ = "pieces_dossier"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    dossier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dossiers_prise_en_charge.id"))
    nature: Mapped[str] = mapped_column(Text)
    nom_fichier: Mapped[str] = mapped_column(Text)
    type_contenu: Mapped[str] = mapped_column(Text)
    contenu: Mapped[bytes] = mapped_column(LargeBinary)
    empreinte: Mapped[str] = mapped_column(Text)
    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class ReponseFiche(Base):
    """La réponse d'un assureur à un cahier des charges : une écriture, corrigée ou retirée par une ligne."""
    __tablename__ = "reponses_fiche"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    fiche_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fiches_regime.id"))
    assureur: Mapped[str] = mapped_column(Text)
    recue_le: Mapped[date] = mapped_column(Date)
    taux_garanti: Mapped[float] = mapped_column(Numeric(asdecimal=False))
    participation_benefices: Mapped[float] = mapped_column(Numeric(asdecimal=False))
    frais_sur_cotisations: Mapped[float] = mapped_column(Numeric(asdecimal=False))
    frais_sur_encours: Mapped[float] = mapped_column(Numeric(asdecimal=False))
    delai_paiement_jours: Mapped[int | None] = mapped_column(Integer)
    transfert_preavis_mois: Mapped[int | None] = mapped_column(Integer)
    transfert_penalite: Mapped[float | None] = mapped_column(Numeric(asdecimal=False))
    accepte_etude_plateforme: Mapped[bool | None] = mapped_column(Boolean)
    reporting_annuel: Mapped[bool | None] = mapped_column(Boolean)
    historique_participation: Mapped[str | None] = mapped_column(Text)
    commentaire: Mapped[str | None] = mapped_column(Text)
    offre_nom_fichier: Mapped[str | None] = mapped_column(Text)
    offre_contenu: Mapped[bytes | None] = mapped_column(LargeBinary)
    offre_empreinte: Mapped[str | None] = mapped_column(Text)
    remplace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reponses_fiche.id"))
    retrait: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    motif_correction: Mapped[str | None] = mapped_column(Text)
    saisie_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    consultation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consultations_assureurs.id"))
    pour_comparaison: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class ChoixFiche(Base):
    __tablename__ = "choix_fiche"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    fiche_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fiches_regime.id"))
    reponse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reponses_fiche.id"))
    motif: Mapped[str | None] = mapped_column(Text)
    choisi_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    choisi_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class ExtractionTexte(Base):
    """La trace d'une extraction assistée : l'empreinte du document, jamais le document."""
    __tablename__ = "extractions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    nom_fichier: Mapped[str] = mapped_column(Text)
    empreinte: Mapped[str] = mapped_column(Text)
    taille: Mapped[int] = mapped_column(Integer)
    moteur: Mapped[str] = mapped_column(Text)
    modele: Mapped[str | None] = mapped_column(Text)
    envoye_a_un_tiers: Mapped[bool] = mapped_column(Boolean)
    resultat: Mapped[dict] = mapped_column(JSONB)
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


class MandatCourtage(Base):
    __tablename__ = "mandats_courtage"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    statut: Mapped[str] = mapped_column(Text, server_default=FetchedValue())
    besoins: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=FetchedValue())
    message: Mapped[str | None] = mapped_column(Text)
    demande_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    demande_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    perimetre: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    date_effet: Mapped[date | None] = mapped_column(Date)
    duree_mois: Mapped[int | None] = mapped_column(Integer)
    preavis_mois: Mapped[int | None] = mapped_column(Integer)
    exclusif: Mapped[bool | None] = mapped_column(Boolean)
    conditions: Mapped[str | None] = mapped_column(Text)
    propose_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    propose_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    empreinte_texte: Mapped[str | None] = mapped_column(Text)
    signe_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    signe_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signataire_nom: Mapped[str | None] = mapped_column(Text)
    signataire_fonction: Mapped[str | None] = mapped_column(Text)
    signataire_qualite: Mapped[str | None] = mapped_column(Text)
    delegation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("justificatifs.id"))
    motif: Mapped[str | None] = mapped_column(Text)
    contrat_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contrats.id"))


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    etude_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("etudes.id"))
    fiche_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fiches_regime.id"))
    prestation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("prestations.id"))
    version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regimes_versions.id"))   # une note de régime
    mandat_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mandats_courtage.id"))
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


class EntreeCatalogue(Base):
    """Un régime partagé, tel que le catalogue le garde : aucune organisation, aucune personne (public)."""
    __tablename__ = "catalogue_regimes"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    empreinte: Mapped[str] = mapped_column(Text)
    pays: Mapped[str] = mapped_column(Text)
    secteur: Mapped[str] = mapped_column(Text)
    taille: Mapped[str] = mapped_column(Text)
    convention_code: Mapped[str] = mapped_column(Text)
    annee: Mapped[int] = mapped_column(Integer)
    categories: Mapped[list] = mapped_column(JSONB)


class RetraitCatalogue(Base):
    __tablename__ = "catalogue_retraits"
    partage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalogue_regimes.id"), primary_key=True)
    retire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class PartageRegime(Base):
    """Le lien, du côté de l'entreprise (RLS) : quelle version, sous quel numéro de catalogue."""
    __tablename__ = "partages_regime"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regimes_versions.id"))
    partage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalogue_regimes.id"))
    partage_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    partage_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


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


class CodeConnexion(Base):
    __tablename__ = "codes_connexion"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    telephone: Mapped[str] = mapped_column(Text)
    code_hash: Mapped[str] = mapped_column(Text)
    canal: Mapped[str] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tentatives: Mapped[int] = mapped_column(Integer, server_default=FetchedValue())
    utilise_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionUtilisateur(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    jeton_hash: Mapped[str] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    derniere_activite: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    revoquee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    agent: Mapped[str | None] = mapped_column(Text)


class CompteAssureur(Base):
    """Le compte bancaire d'un assureur, tenu par le courtier, avec son contre-appel. Une ligne remplace, jamais ne
    se modifie ; le compte en vigueur est celui qu'aucune autre ligne ne remplace."""
    __tablename__ = "comptes_assureurs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    assureur: Mapped[str] = mapped_column(Text)
    assureur_cle: Mapped[str] = mapped_column(Text)
    banque: Mapped[str] = mapped_column(Text)
    titulaire: Mapped[str] = mapped_column(Text)
    iban: Mapped[str] = mapped_column(Text)
    bic: Mapped[str | None] = mapped_column(Text)
    verifie_aupres: Mapped[str] = mapped_column(Text)
    verifie_telephone: Mapped[str] = mapped_column(Text)
    verifie_le: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
    remplace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("comptes_assureurs.id"))
    enregistre_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    enregistre_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Police(Base):
    """Le contrat placé chez l'assureur : son statut se calcule sur ses pièces, sa signature et ses appels."""
    __tablename__ = "polices"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    choix_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("choix_fiche.id"))
    assureur: Mapped[str] = mapped_column(Text)
    numero_police: Mapped[str | None] = mapped_column(Text)
    date_effet: Mapped[date] = mapped_column(Date)
    periodicite: Mapped[str] = mapped_column(Text)
    signee_le: Mapped[date | None] = mapped_column(Date)
    signee_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class AppelPrime(Base):
    """Un appel de prime et les coordonnées qu'il porte, confrontées au registre ; puis le virement déclaré et
    l'encaissement confirmé. La plateforme ne paie rien."""
    __tablename__ = "appels_prime"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    police_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("polices.id"))
    reference: Mapped[str] = mapped_column(Text)
    montant: Mapped[int] = mapped_column(BigInteger)
    echeance: Mapped[date] = mapped_column(Date)
    premiere: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    banque: Mapped[str] = mapped_column(Text)
    titulaire: Mapped[str] = mapped_column(Text)
    iban: Mapped[str] = mapped_column(Text)
    bic: Mapped[str | None] = mapped_column(Text)
    compte_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("comptes_assureurs.id"))
    controle: Mapped[str] = mapped_column(Text)
    contre_appel: Mapped[dict | None] = mapped_column(JSONB)
    contre_appel_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vire_le: Mapped[date | None] = mapped_column(Date)
    montant_vire: Mapped[int | None] = mapped_column(BigInteger)
    reference_virement: Mapped[str | None] = mapped_column(Text)
    declare_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    declare_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    encaisse_le: Mapped[date | None] = mapped_column(Date)
    confirme_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    confirme_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class PiecePolice(Base):
    """Un document du placement, en ajout seul. Un relevé porte sa date et le montant du fonds."""
    __tablename__ = "pieces_police"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    police_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("polices.id"))
    appel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appels_prime.id"))
    nature: Mapped[str] = mapped_column(Text)
    nom_fichier: Mapped[str] = mapped_column(Text)
    type_contenu: Mapped[str] = mapped_column(Text)
    contenu: Mapped[bytes] = mapped_column(LargeBinary)
    empreinte: Mapped[str] = mapped_column(Text)
    releve_le: Mapped[date | None] = mapped_column(Date)
    montant_fonds: Mapped[int | None] = mapped_column(BigInteger)
    depose_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    depose_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class ConsultationAssureur(Base):
    """Un assureur consulté sur un cahier des charges : envoyé, ouvert, répondu, relancé, annulé."""
    __tablename__ = "consultations_assureurs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    fiche_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fiches_regime.id"))
    assureur: Mapped[str] = mapped_column(Text)
    assureur_cle: Mapped[str] = mapped_column(Text)
    contact_nom: Mapped[str | None] = mapped_column(Text)
    contact_courriel: Mapped[str] = mapped_column(Text)
    expire_le: Mapped[date] = mapped_column(Date)
    envoyee_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"))
    envoyee_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    relances: Mapped[int] = mapped_column(Integer, server_default=FetchedValue())
    relancee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ouverte_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    repondue_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    annulee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LienAssureur(Base):
    """L'empreinte d'un lien personnel d'assureur ; lue hors RLS, avant qu'une organisation soit connue."""
    __tablename__ = "liens_assureurs"
    jeton_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations_assureurs.id"))
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    revoque_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RappelEnvoye(Base):
    """Un rappel du cycle annuel déjà envoyé : une étape de l'année, dans un état, une fois."""
    __tablename__ = "rappels_envoyes"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"))
    cle: Mapped[str] = mapped_column(Text)
    etat: Mapped[str] = mapped_column(Text)
    destinataires: Mapped[int] = mapped_column(Integer)
    envoye_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class DemandeRappel(Base):
    """Un visiteur de la vitrine demande à être rappelé ; le courtier suit la demande. Effacée à douze mois."""
    __tablename__ = "demandes_rappel"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=FetchedValue())
    nom: Mapped[str] = mapped_column(Text)
    entreprise: Mapped[str] = mapped_column(Text)
    telephone: Mapped[str] = mapped_column(Text)
    courriel: Mapped[str | None] = mapped_column(Text)
    creneau: Mapped[str] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    accord: Mapped[bool] = mapped_column(Boolean)
    recue_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    statut: Mapped[str] = mapped_column(Text, server_default=FetchedValue())
    traitee_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"))
    traitee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)


class Mesure(Base):
    """Un compteur d'audience : un jour, un événement, une source. Ni identifiant, ni adresse."""
    __tablename__ = "mesures"
    jour: Mapped[date] = mapped_column(Date, primary_key=True)
    evenement: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)
    n: Mapped[int] = mapped_column(Integer, server_default=FetchedValue())
