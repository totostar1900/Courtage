"""Ce qu'un visiteur lit sans session : le cabinet, depuis la configuration, et la version des conditions."""
from courtage import cabinet
from tests.outils import V1


def test_le_cabinet_se_lit_sans_session_et_dit_ce_qui_manque(client, monkeypatch):
    for v in ("NOM", "AGREMENT", "ADRESSE", "RCCM", "COURRIEL", "TELEPHONE"):
        monkeypatch.delenv(f"COURTAGE_COURTIER_{v}", raising=False)
    monkeypatch.setenv("COURTAGE_COURTIER_NOM", "Purpose Capital Courtage SARL")
    r = client.get(f"{V1}/public/cabinet")
    assert r.status_code == 200
    c = r.json()
    assert c["nom"] == "Purpose Capital Courtage SARL"
    assert c["agrement"] == "[numéro d'agrément]" and "agrement" in c["manquants"] and "nom" not in c["manquants"]
    assert c["conditions_version"] == cabinet.CONDITIONS_VERSION
    assert "Render" in c["hebergeur"]


def test_le_mandat_lit_la_meme_identite(monkeypatch):
    from courtage.services import mandats
    monkeypatch.setenv("COURTAGE_COURTIER_AGREMENT", "CIMA-CR-0042")
    assert mandats.courtier()["agrement"] == "CIMA-CR-0042"


def test_robots_et_plan_du_site(bases):
    from fastapi.testclient import TestClient
    from courtage.api import creer_app
    c = TestClient(creer_app(moteur=bases[1], authentification="entete_dev", url_publique="https://courtage.exemple.cm"))
    r = c.get("/robots.txt")
    assert r.status_code == 200 and "Disallow: /dossier/" in r.text and "Disallow: /offre/" in r.text
    assert "Sitemap: https://courtage.exemple.cm/sitemap.xml" in r.text
    s = c.get("/sitemap.xml")
    assert s.headers["content-type"].startswith("application/xml")
    assert "<loc>https://courtage.exemple.cm/</loc>" in s.text and "https://courtage.exemple.cm/essai" in s.text
    assert "/dossier" not in s.text


def test_la_page_porte_l_adresse_publique(bases, tmp_path):
    from fastapi.testclient import TestClient
    from courtage.api import creer_app
    (tmp_path / "index.html").write_text('<meta property="og:image" content="__URL_PUBLIQUE__/apercu.png">', "utf-8")
    c = TestClient(creer_app(moteur=bases[1], dossier_web=tmp_path, url_publique="https://courtage.exemple.cm"))
    for chemin in ("/", "/essai", "/index.html"):
        assert 'content="https://courtage.exemple.cm/apercu.png"' in c.get(chemin).text
