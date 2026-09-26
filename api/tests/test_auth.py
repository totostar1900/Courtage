"""Connexion par téléphone : un code à usage unique, puis une session."""
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from courtage.api import creer_app
from courtage.auth.telephone import normaliser
from courtage.messagerie import ExpediteurJournal
from tests.outils import V1, en_tant_que

CLE = b"cle-d-authentification-de-test-assez-longue"


@pytest.fixture
def boite():
    return ExpediteurJournal()


@pytest.fixture
def web(bases, boite):
    """Un navigateur : mode session, cookies gardés d'une requête à l'autre."""
    return TestClient(creer_app(moteur=bases[1], authentification="session", expediteur=boite, cle_auth=CLE))


@pytest.fixture
def abonne(bases):
    """Une personne connue, avec son téléphone et un dossier."""
    import uuid
    tel = f"+2376{uuid.uuid4().int % 10**8:08d}"
    with bases[0].begin() as c:
        u = c.execute(text("INSERT INTO utilisateurs (telephone, nom_affiche) VALUES (:t, 'Mme Test') RETURNING id"),
                      {"t": tel}).scalar_one()
        o = c.execute(text("INSERT INTO organisations (nom, pays) VALUES ('Client', 'CM') RETURNING id")).scalar_one()
        c.execute(text("INSERT INTO adhesions (utilisateur_id, organisation_id, role) VALUES (:u, :o, 'admin_client')"),
                  {"u": u, "o": o})
    return {"id": u, "telephone": tel, "org": o}


def code_recu(boite, telephone) -> str:
    message = next(m for m in reversed(boite.envoyes) if m.telephone == telephone)
    return re.search(r"\b(\d{6})\b", message.texte).group(1)


def se_connecter(web, boite, telephone):
    assert web.post(f"{V1}/auth/code", json={"telephone": telephone}).status_code == 200
    return web.post(f"{V1}/auth/verification", json={"telephone": telephone, "code": code_recu(boite, telephone)})


def ecrire(web, chemin, **kw):
    """Une écriture depuis la page : l'en-tête anti-CSRF que l'interface pose toujours."""
    return web.post(chemin, headers={"X-Courtage": "1"}, **kw)


# --- Numéros --------------------------------------------------------------------

@pytest.mark.parametrize("saisi,attendu", [
    ("+237 6 99 12 34 56", "+237699123456"),
    ("699123456", "+237699123456"),          # le Cameroun par défaut
    ("00237 699 12 34 56", "+237699123456"),
    ("+225 07 08 09 10 11", "+2250708091011"),
    ("233 12 34 56", "+237233123456"),       # un fixe camerounais
])
def test_normaliser_les_numeros(saisi, attendu):
    assert normaliser(saisi) == attendu


@pytest.mark.parametrize("saisi", ["12", "abc", "+237 12345", "6991234567890123"])
def test_numeros_invalides(saisi):
    with pytest.raises(ValueError):
        normaliser(saisi)


# --- Le code ----------------------------------------------------------------------

def test_se_connecter_par_code(web, boite, abonne):
    r = se_connecter(web, boite, abonne["telephone"])
    assert r.status_code == 200, r.text
    assert r.json()["utilisateur"]["id"] == str(abonne["id"])
    assert "jeton" not in r.json()              # un navigateur n'a que le cookie, illisible par la page
    cookie = r.headers["set-cookie"]
    assert "courtage_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    moi = web.get(f"{V1}/moi").json()
    assert [o["id"] for o in moi["organisations"]] == [str(abonne["org"])]


def test_le_message_dit_la_duree_et_de_ne_pas_partager(web, boite, abonne):
    web.post(f"{V1}/auth/code", json={"telephone": abonne["telephone"]})
    texte = boite.envoyes[-1].texte
    assert "10 minutes" in texte and "communiquez" in texte


def test_un_numero_inconnu_recoit_la_meme_reponse_et_rien_n_est_envoye(web, boite, abonne):
    connu = web.post(f"{V1}/auth/code", json={"telephone": abonne["telephone"]})
    avant = len(boite.envoyes)
    inconnu = web.post(f"{V1}/auth/code", json={"telephone": "+237 6 00 00 00 01"})
    assert inconnu.status_code == connu.status_code == 200
    assert inconnu.json() == connu.json()
    assert len(boite.envoyes) == avant


def test_numero_mal_forme(web):
    r = web.post(f"{V1}/auth/code", json={"telephone": "12"})
    assert r.status_code == 422 and r.json()["code"] == "telephone_invalide"


def test_un_mauvais_code(web, boite, abonne):
    web.post(f"{V1}/auth/code", json={"telephone": abonne["telephone"]})
    r = web.post(f"{V1}/auth/verification", json={"telephone": abonne["telephone"], "code": "000000"})
    assert r.status_code == 401 and r.json()["code"] == "code_invalide"


def test_cinq_essais_puis_le_code_est_brule(web, boite, abonne):
    web.post(f"{V1}/auth/code", json={"telephone": abonne["telephone"]})
    bon = code_recu(boite, abonne["telephone"])
    faux = "999999" if bon != "999999" else "888888"
    for _ in range(5):
        web.post(f"{V1}/auth/verification", json={"telephone": abonne["telephone"], "code": faux})
    r = web.post(f"{V1}/auth/verification", json={"telephone": abonne["telephone"], "code": bon})
    assert r.status_code == 401


def test_un_code_ne_sert_qu_une_fois(web, boite, abonne):
    r = se_connecter(web, boite, abonne["telephone"])
    assert r.status_code == 200
    r = web.post(f"{V1}/auth/verification", json={"telephone": abonne["telephone"],
                                                 "code": code_recu(boite, abonne["telephone"])})
    assert r.status_code == 401


def test_un_code_expire(web, boite, abonne, bases):
    web.post(f"{V1}/auth/code", json={"telephone": abonne["telephone"]})
    with bases[0].begin() as c:
        c.execute(text("UPDATE codes_connexion SET expire_le = now() - interval '1 second' WHERE telephone = :t"),
                  {"t": abonne["telephone"]})
    r = web.post(f"{V1}/auth/verification", json={"telephone": abonne["telephone"],
                                                 "code": code_recu(boite, abonne["telephone"])})
    assert r.status_code == 401


def test_trois_demandes_par_quart_d_heure(web, abonne):
    for _ in range(3):
        assert web.post(f"{V1}/auth/code", json={"telephone": abonne["telephone"]}).status_code == 200
    r = web.post(f"{V1}/auth/code", json={"telephone": abonne["telephone"]})
    assert r.status_code == 429 and r.json()["code"] == "trop_de_demandes"


def test_le_code_n_est_jamais_stocke_en_clair(web, boite, abonne, bases):
    web.post(f"{V1}/auth/code", json={"telephone": abonne["telephone"]})
    code = code_recu(boite, abonne["telephone"])
    with bases[0].connect() as c:
        stocke = c.execute(text("SELECT code_hash FROM codes_connexion WHERE telephone = :t"),
                           {"t": abonne["telephone"]}).scalar_one()
    assert code not in stocke and len(stocke.strip()) == 64


# --- La session -------------------------------------------------------------------

def test_sans_session_401(web):
    assert web.get(f"{V1}/moi").status_code == 401


def test_deconnexion(web, boite, abonne):
    se_connecter(web, boite, abonne["telephone"])
    assert ecrire(web, f"{V1}/auth/deconnexion").status_code == 200
    assert web.get(f"{V1}/moi").status_code == 401


def test_une_session_expiree(web, boite, abonne, bases):
    se_connecter(web, boite, abonne["telephone"])
    with bases[0].begin() as c:
        c.execute(text("UPDATE sessions SET expire_le = now() - interval '1 second' WHERE utilisateur_id = :u"),
                  {"u": abonne["id"]})
    assert web.get(f"{V1}/moi").status_code == 401


def test_le_jeton_porteur_pour_un_client_d_api(bases, boite, abonne):
    """Une application mobile garde le jeton et l'envoie ; elle n'a pas besoin de l'en-tête anti-CSRF."""
    web = TestClient(creer_app(moteur=bases[1], authentification="session", expediteur=boite, cle_auth=CLE))
    web.post(f"{V1}/auth/code", json={"telephone": abonne["telephone"]})
    r = web.post(f"{V1}/auth/verification", json={"telephone": abonne["telephone"], "application": True,
                                                 "code": code_recu(boite, abonne["telephone"])})
    jeton = r.json()["jeton"]
    nu = TestClient(creer_app(moteur=bases[1], authentification="session", expediteur=boite, cle_auth=CLE))
    assert nu.get(f"{V1}/moi", headers={"Authorization": f"Bearer {jeton}"}).status_code == 200


def test_une_ecriture_par_cookie_demande_l_en_tete_anti_csrf(web, boite, abonne):
    """Un autre site peut faire envoyer le cookie, pas poser un en-tête : c'est la protection."""
    se_connecter(web, boite, abonne["telephone"])
    r = web.post(f"{V1}/organisations/{abonne['org']}/regimes", json={"nom": "R"})
    assert r.status_code == 403 and r.json()["code"] == "csrf"
    r = ecrire(web, f"{V1}/organisations/{abonne['org']}/regimes", json={"nom": "R"})
    assert r.status_code == 201


def test_l_en_tete_de_developpement_ne_marche_pas_en_mode_session(web, abonne):
    assert web.get(f"{V1}/moi", headers=en_tant_que(abonne["id"])).status_code == 401
    assert web.get(f"{V1}/dev/utilisateurs").status_code == 404


def test_le_mode_de_connexion_est_public(web):
    assert web.get(f"{V1}/auth/mode").json() == {"mode": "session"}


# --- Inscrire un membre par son numéro --------------------------------------------

def test_le_conseiller_inscrit_la_drh_par_son_numero(client, azito, bases, boite):
    r = client.post(f"{V1}/organisations/{azito['org']}/membres", headers=en_tant_que(azito["conseiller"]),
                    json={"telephone": "+237 6 77 11 22 33", "nom_affiche": "Mme Ngo, DRH", "role": "lecteur_client"})
    assert r.status_code == 201, r.text
    web = TestClient(creer_app(moteur=bases[1], authentification="session", expediteur=boite, cle_auth=CLE))
    assert se_connecter(web, boite, "+237677112233").status_code == 200
    assert [o["role"] for o in web.get(f"{V1}/moi").json()["organisations"]] == ["lecteur_client"]


def test_la_drh_n_inscrit_personne(client, azito):
    r = client.post(f"{V1}/organisations/{azito['org']}/membres", headers=en_tant_que(azito["drh"]),
                    json={"telephone": "+237 6 77 11 22 34", "nom_affiche": "X", "role": "admin_client"})
    assert r.status_code == 403


# --- Production ---------------------------------------------------------------------

def test_en_production_il_faut_une_cle_et_un_expediteur(bases, monkeypatch):
    monkeypatch.setenv("COURTAGE_ENV", "production")
    with pytest.raises(RuntimeError, match="authentification"):
        creer_app(moteur=bases[1], authentification="session", cle_sceau=b"x" * 32)


# --- Le journal de l'exploitant ----------------------------------------------------

def test_chaque_demande_dit_dans_le_journal_ce_qu_il_en_est(web, abonne, caplog):
    """L'exploitant, qui ne voit pas l'écran, lit dans le journal pourquoi un code n'est pas venu."""
    import logging
    caplog.set_level(logging.INFO, logger="courtage.connexion")
    tel = abonne["telephone"]
    web.post(f"{V1}/auth/code", json={"telephone": "+237 6 00 00 00 01"})
    for _ in range(4):
        web.post(f"{V1}/auth/code", json={"telephone": tel})
    web.post(f"{V1}/auth/verification", json={"telephone": tel, "code": "000000"})
    lignes = [r.getMessage() for r in caplog.records if r.name == "courtage.connexion"]
    assert any("numéro inconnu" in l and "001" in l for l in lignes)
    assert sum("code envoyé" in l for l in lignes) == 3
    assert any("limite" in l for l in lignes)
    assert any("code refusé" in l for l in lignes)
    assert all(tel not in l for l in lignes)                      # le numéro est masqué : des chiffres de fin
