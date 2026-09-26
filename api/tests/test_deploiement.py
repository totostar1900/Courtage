"""Tâche 9 : la base prouvée au démarrage, la sonde, l'interface servie, les limites publiques."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from courtage.api import creer_app
from courtage.api.limites import Limiteur
from courtage.db.migrations import revision_attendue
from courtage.deploiement import _psycopg, controler, ouvrir_role_applicatif
from tests.conftest import MOT_DE_PASSE_APP
from tests.outils import V1


# --- La base au démarrage -------------------------------------------------------

def test_une_base_bien_migree_passe_tous_les_controles(bases):
    controles = controler(bases[0])
    assert [c for c in controles if not c.ok] == []
    assert len(controles) == 7


def test_une_table_possedee_par_le_role_applicatif_est_signalee(bases):
    with bases[0].begin() as c:
        c.execute(text("CREATE TABLE piege (id int); ALTER TABLE piege OWNER TO courtage_app"))
    try:
        echec = [c for c in controler(bases[0]) if not c.ok]
        assert [c.nom for c in echec] == ["courtage_app ne possède aucune table"] and "piege" in echec[0].detail
    finally:
        with bases[0].begin() as c:
            c.execute(text("DROP TABLE piege"))


def test_un_declencheur_d_immuabilite_desactive_est_signale(bases):
    with bases[0].begin() as c:
        c.execute(text("ALTER TABLE etudes DISABLE TRIGGER etudes_immuables"))
    try:
        assert "etudes_immuables" in next(c for c in controler(bases[0]) if not c.ok).detail
    finally:
        with bases[0].begin() as c:
            c.execute(text("ALTER TABLE etudes ENABLE TRIGGER etudes_immuables"))


def test_ouvrir_le_role_applicatif(bases):
    url = make_url(str(bases[0].url.render_as_string(hide_password=False))).set(
        username="courtage_app", password=MOT_DE_PASSE_APP)
    ouvrir_role_applicatif(bases[0], url.render_as_string(hide_password=False))
    with create_engine(url).connect() as c:
        assert c.execute(text("SELECT current_user")).scalar() == "courtage_app"


def test_le_role_du_proprietaire_est_refuse_comme_role_applicatif(bases):
    with pytest.raises(RuntimeError, match="courtage_app"):
        ouvrir_role_applicatif(bases[0], "postgresql+psycopg://postgres:x@localhost/b")


@pytest.mark.parametrize("donnee,attendue", [
    ("postgres://u:p@h/b", "postgresql+psycopg://u:p@h/b"),
    ("postgresql://u:p@h/b", "postgresql+psycopg://u:p@h/b"),
    ("postgresql+psycopg://u:p@h/b", "postgresql+psycopg://u:p@h/b"),
])
def test_l_adresse_de_l_hebergeur(donnee, attendue):
    assert _psycopg(donnee) == attendue


# --- La sonde -------------------------------------------------------------------

def test_la_sonde_lit_la_revision_dans_la_base(bases):
    r = TestClient(creer_app(moteur=bases[1])).get(f"{V1}/sante")
    assert r.status_code == 200
    assert r.json()["statut"] == "ok" and r.json()["migration"] == revision_attendue() == "0008_sante"


def test_une_base_injoignable_repond_503():
    moteur = create_engine("postgresql+psycopg://x:y@127.0.0.1:1/rien")
    r = TestClient(creer_app(moteur=moteur)).get(f"{V1}/sante")
    assert r.status_code == 503 and r.json()["statut"] == "base_injoignable"


# --- L'interface servie ----------------------------------------------------------

@pytest.fixture
def interface(tmp_path, bases):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=racine></div>", "utf-8")
    (tmp_path / "assets" / "index-abc.js").write_text("console.log(1)", "utf-8")
    (tmp_path.parent / "secret.txt").write_text("non", "utf-8")
    return TestClient(creer_app(moteur=bases[1], dossier_web=tmp_path))


def test_une_adresse_de_la_page_rend_l_index(interface):
    for chemin in ("/", "/etudes/123", "/verifier/RL-0001-0001"):
        r = interface.get(chemin)
        assert r.status_code == 200 and "racine" in r.text and r.headers["cache-control"] == "no-cache"


def test_les_assets_se_gardent(interface):
    r = interface.get("/assets/index-abc.js")
    assert r.status_code == 200 and "immutable" in r.headers["cache-control"]


def test_une_route_d_api_inconnue_reste_un_404_json(interface):
    r = interface.get(f"{V1}/nulle-part")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")
    assert interface.get(f"{V1}/sante").status_code == 200


def test_on_ne_sort_pas_du_dossier(interface):
    r = interface.get("/../secret.txt")
    assert "non" != r.text
    r = interface.get("/%2e%2e/secret.txt")
    assert r.text != "non"


def test_un_dossier_sans_index_arrete_le_demarrage(tmp_path, bases):
    with pytest.raises(RuntimeError, match="index.html"):
        creer_app(moteur=bases[1], dossier_web=tmp_path)


# --- Les limites publiques --------------------------------------------------------

def test_le_limiteur_oublie_ce_qui_sort_de_la_fenetre():
    t = [0.0]
    limiteur = Limiteur(2, 60, horloge=lambda: t[0])
    assert limiteur.admettre("a") and limiteur.admettre("a") and not limiteur.admettre("a")
    assert limiteur.admettre("b")
    t[0] = 61
    assert limiteur.admettre("a")


def test_la_verification_publique_est_limitee_par_adresse(bases):
    web = TestClient(creer_app(moteur=bases[1]))
    codes = [web.get(f"{V1}/verifier/RL-0000-0000").status_code for _ in range(31)]
    assert 429 not in codes[:30] and codes[30] == 429
    assert web.get(f"{V1}/verifier/RL-0000-0000").json()["code"] == "trop_de_requetes"


def test_les_demandes_de_code_sont_limitees_par_adresse(bases):
    web = TestClient(creer_app(moteur=bases[1]))
    codes = [web.post(f"{V1}/auth/code", json={"telephone": f"+2376900{i:05d}"}).status_code for i in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429
