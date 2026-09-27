"""Base de données : isolation par organisation (RLS) et verrous d'immuabilité."""
import uuid

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from courtage.db import Base, contexte


@pytest.fixture
def proprio(bases):
    return bases[0]


@pytest.fixture
def app(bases):
    return bases[1]


@pytest.fixture
def deux_organisations(proprio):
    """Deux clients, chacun avec un fichier déposé et une étude en brouillon."""
    ids = {}
    with proprio.begin() as c:
        u = c.execute(text("INSERT INTO utilisateurs (telephone) VALUES (:t) RETURNING id"),
                      {"t": f"+2376{uuid.uuid4().int % 10**8:08d}"}).scalar_one()
        for nom in ("A", "B"):
            org = c.execute(text("INSERT INTO organisations (nom, pays) VALUES (:n, 'CM') RETURNING id"),
                            {"n": f"Client {nom}"}).scalar_one()
            c.execute(text("INSERT INTO adhesions (utilisateur_id, organisation_id, role) VALUES (:u, :o, 'admin_client')"),
                      {"u": u, "o": org})
            f = c.execute(text("""
                INSERT INTO fichiers_personnel (organisation_id, depose_par, nom_fichier, empreinte, date_donnees,
                                                periodicite, lignes, anomalies)
                VALUES (:o, :u, 'personnel.xlsx', repeat('a', 64), '2025-12-31', 'mensuel', '[]', '[]')
                RETURNING id"""), {"o": org, "u": u}).scalar_one()
            e = c.execute(text("""
                INSERT INTO etudes (organisation_id, fichier_id, referentiel_version, convention_code, convention_du,
                                    date_evaluation, hypotheses, fonds_disponible, version_moteur)
                VALUES (:o, :f, '2026-09-26', 'CM_COMMERCE', '2024-01-16', '2025-12-31', '{}', 0, 'ifc-1.0.0')
                RETURNING id"""), {"o": org, "f": f}).scalar_one()
            c.execute(text("INSERT INTO journal (organisation_id, utilisateur_id, action, cible) VALUES (:o, :u, 'test', :e)"),
                      {"o": org, "u": u, "e": str(e)})
            ids[nom] = {"org": org, "fichier": f, "etude": e, "utilisateur": u}
    return ids


def emettre(conn, etude_id, utilisateur_id):
    conn.execute(text("""
        UPDATE etudes SET statut = 'emise', resultats = '{"dette": 1}', empreinte = repeat('b', 64),
                          emise_par = :u, emise_le = now()
        WHERE id = :e"""), {"e": etude_id, "u": utilisateur_id})


# --- Schéma -------------------------------------------------------------------

def test_les_modeles_decrivent_le_schema_migre(proprio):
    """Les modèles SQLAlchemy et la migration écrite à la main disent la même chose."""
    inspecteur = inspect(proprio)
    for table in Base.metadata.sorted_tables:
        en_base = {c["name"] for c in inspecteur.get_columns(table.name)}
        assert en_base == {c.name for c in table.columns}, table.name


def test_le_role_applicatif_n_est_proprietaire_d_aucune_table(proprio):
    """Un propriétaire contourne la RLS : le rôle applicatif ne doit rien posséder."""
    with proprio.connect() as c:
        possedees = c.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner = 'courtage_app'")).all()
    assert possedees == []


def test_rls_active_sur_les_tables_des_clients(proprio):
    with proprio.connect() as c:
        actives = set(c.execute(text(
            "SELECT relname FROM pg_class WHERE relrowsecurity AND relnamespace = 'public'::regnamespace")).scalars())
    assert {"fichiers_personnel", "etudes", "journal", "contrats"} <= actives


# --- Isolation ----------------------------------------------------------------

def test_une_organisation_ne_voit_que_ses_donnees(app, deux_organisations):
    a, b = deux_organisations["A"], deux_organisations["B"]
    with app.begin() as c:
        contexte(c, a["org"])
        for table in ("fichiers_personnel", "etudes", "journal"):
            orgs = set(c.execute(text(f"SELECT organisation_id FROM {table}")).scalars())
            assert orgs == {a["org"]}, table
        assert c.execute(text("SELECT count(*) FROM etudes WHERE id = :e"), {"e": b["etude"]}).scalar_one() == 0


def test_sans_contexte_on_ne_voit_rien(app, deux_organisations):
    with app.begin() as c:
        assert c.execute(text("SELECT count(*) FROM etudes")).scalar_one() == 0


def test_le_contexte_ne_survit_pas_a_la_transaction(app, deux_organisations):
    with app.begin() as c:
        contexte(c, deux_organisations["A"]["org"])
    with app.begin() as c:
        assert c.execute(text("SELECT count(*) FROM etudes")).scalar_one() == 0


def test_on_n_ecrit_pas_chez_une_autre_organisation(app, deux_organisations):
    a, b = deux_organisations["A"], deux_organisations["B"]
    with pytest.raises(ProgrammingError, match="row-level security"):
        with app.begin() as c:
            contexte(c, a["org"])
            c.execute(text("INSERT INTO journal (organisation_id, action, cible) VALUES (:o, 'intrusion', 'x')"),
                      {"o": b["org"]})


def test_les_adhesions_se_lisent_avant_de_connaitre_l_organisation(app, deux_organisations):
    """Il faut savoir à quelles organisations un utilisateur appartient pour choisir un contexte."""
    u = deux_organisations["A"]["utilisateur"]
    with app.begin() as c:
        orgs = c.execute(text("SELECT organisation_id FROM adhesions WHERE utilisateur_id = :u"), {"u": u}).scalars().all()
    assert len(orgs) == 2


# --- Immuabilité --------------------------------------------------------------

@pytest.mark.parametrize("instruction", [
    "UPDATE journal SET action = 'efface'",
    "DELETE FROM journal",
    "UPDATE fichiers_personnel SET nom_fichier = 'autre.xlsx'",
])
def test_journal_et_fichiers_sont_en_ajout_seul(app, deux_organisations, instruction):
    with pytest.raises(ProgrammingError, match="permission denied"):
        with app.begin() as c:
            contexte(c, deux_organisations["A"]["org"])
            c.execute(text(instruction))


def test_un_fichier_cite_par_une_etude_ne_se_supprime_pas(app, deux_organisations):
    """Un fichier se supprime (donnée de travail) ; une étude qui le cite le retient, par clé étrangère."""
    with pytest.raises(IntegrityError, match="etudes_fichier_id_fkey"):
        with app.begin() as c:
            contexte(c, deux_organisations["A"]["org"])
            c.execute(text("DELETE FROM fichiers_personnel"))


def test_un_brouillon_se_modifie_et_se_supprime(app, deux_organisations):
    a = deux_organisations["A"]
    with app.begin() as c:
        contexte(c, a["org"])
        c.execute(text("UPDATE etudes SET fonds_disponible = 1000 WHERE id = :e"), {"e": a["etude"]})
        assert c.execute(text("DELETE FROM etudes WHERE id = :e"), {"e": a["etude"]}).rowcount == 1


@pytest.mark.parametrize("instruction", [
    "UPDATE etudes SET fonds_disponible = 1 WHERE id = :e",
    "UPDATE etudes SET statut = 'brouillon' WHERE id = :e",
    "DELETE FROM etudes WHERE id = :e",
])
def test_une_etude_emise_est_immuable_meme_pour_le_proprietaire(proprio, app, deux_organisations, instruction):
    a = deux_organisations["A"]
    with app.begin() as c:
        contexte(c, a["org"])
        emettre(c, a["etude"], a["utilisateur"])
    with pytest.raises(DBAPIError, match="etude_emise_immuable"):
        with proprio.begin() as c:
            c.execute(text(instruction), {"e": a["etude"]})


def test_une_etude_emise_porte_son_emetteur_son_empreinte_et_ses_resultats(app, deux_organisations):
    a = deux_organisations["A"]
    with pytest.raises(IntegrityError, match="etude_emise_complete"):
        with app.begin() as c:
            contexte(c, a["org"])
            c.execute(text("UPDATE etudes SET statut = 'emise' WHERE id = :e"), {"e": a["etude"]})


def test_une_correction_cite_l_etude_qu_elle_remplace(app, deux_organisations):
    a = deux_organisations["A"]
    with app.begin() as c:
        contexte(c, a["org"])
        emettre(c, a["etude"], a["utilisateur"])
        nouvelle = c.execute(text("""
            INSERT INTO etudes (organisation_id, fichier_id, referentiel_version, convention_code, convention_du,
                                date_evaluation, hypotheses, fonds_disponible, version_moteur, remplace_etude_id)
            VALUES (:o, :f, '2026-09-26', 'CM_COMMERCE', '2024-01-16', '2025-12-31', '{}', 0, 'ifc-1.0.0', :e)
            RETURNING remplace_etude_id"""), {"o": a["org"], "f": a["fichier"], "e": a["etude"]}).scalar_one()
    assert nouvelle == a["etude"]


# --- Montants -----------------------------------------------------------------

def test_montants_en_entiers_et_positifs(app, deux_organisations):
    a = deux_organisations["A"]
    with pytest.raises(IntegrityError):
        with app.begin() as c:
            contexte(c, a["org"])
            c.execute(text("UPDATE etudes SET fonds_disponible = -1 WHERE id = :e"), {"e": a["etude"]})
    with app.begin() as c:
        contexte(c, a["org"])
        c.execute(text("UPDATE etudes SET fonds_disponible = 1234.6 WHERE id = :e"), {"e": a["etude"]})
        assert c.execute(text("SELECT fonds_disponible FROM etudes WHERE id = :e"), {"e": a["etude"]}).scalar_one() == 1235


def test_sceaux_hors_rls_en_ajout_seul(app):
    """La vérification publique lit un sceau sans connaître l'organisation."""
    with app.begin() as c:
        c.execute(text("""INSERT INTO sceaux (numero, nature, empreinte, sceau, resume)
                          VALUES ('RL-TEST-0001', 'etude_ifc', repeat('c', 64), repeat('d', 64), '{}')"""))
    with app.begin() as c:
        assert c.execute(text("SELECT nature FROM sceaux WHERE numero = 'RL-TEST-0001'")).scalar_one() == "etude_ifc"
    with pytest.raises(ProgrammingError, match="permission denied"):
        with app.begin() as c:
            c.execute(text("DELETE FROM sceaux"))
