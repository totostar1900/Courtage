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
