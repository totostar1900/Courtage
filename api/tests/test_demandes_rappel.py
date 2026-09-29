"""Être rappelé depuis la vitrine : la demande gardée, le courtier prévenu sans son contenu, le suivi, le champ piège,
l'effacement à douze mois."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from courtage.services import demandes_rappel
from tests.outils import V1, en_tant_que

DEMANDE = {"nom": "Paul Mbarga", "entreprise": "Brasseries du Littoral", "telephone": "699 12 34 56",
           "courriel": "p.mbarga@brasseries.cm", "creneau": "matin", "message": "Nous avons 180 salariés.", "accord": True}


def test_une_demande_de_rappel_est_gardee_et_le_courtier_prevenu(client, personnes):
    r = client.post(f"{V1}/public/rappel", json=DEMANDE)
    assert r.status_code == 201, r.text
    admin = en_tant_que(personnes["admin"])
    [d] = [x for x in client.get(f"{V1}/rappels", headers=admin).json() if x["nom"] == "Paul Mbarga"][-1:]
    assert d["telephone"].startswith("+237") and d["statut"] == "a_rappeler" and d["creneau"] == "matin"
    avis = [m.texte for m in client.app.state.courriel.envoyes if "demande à être rappelé" in m.texte]
    assert avis and all("180 salariés" not in x and "699" not in x for x in avis)     # rien du contenu dans le courriel
    # Le courtier seul la lit et la traite.
    assert client.get(f"{V1}/rappels", headers=en_tant_que(personnes["drh"])).status_code == 403
    t = client.put(f"{V1}/rappels/{d['id']}", headers=admin, json={"statut": "rappelee", "note": "RDV le 3/10."})
    assert t.json()["statut"] == "rappelee" and t.json()["traitee_par"] == "Admin"


def test_les_refus(client):
    assert client.post(f"{V1}/public/rappel", json={**DEMANDE, "accord": False}).json()["code"] == "accord_requis"
    assert client.post(f"{V1}/public/rappel", json={**DEMANDE, "telephone": "123"}).json()["code"] == "telephone_invalide"
    assert client.post(f"{V1}/public/rappel", json={**DEMANDE, "creneau": "nuit"}).json()["code"] == "creneau_inconnu"


def test_un_robot_qui_remplit_le_champ_cache_n_est_pas_garde(client, bases):
    with bases[0].connect() as c:
        avant = c.execute(text("SELECT count(*) FROM demandes_rappel")).scalar()
    r = client.post(f"{V1}/public/rappel", json={**DEMANDE, "site_web": "http://spam.example"})
    assert r.status_code == 201                                  # même réponse
    with bases[0].connect() as c:
        assert c.execute(text("SELECT count(*) FROM demandes_rappel")).scalar() == avant


def test_effacee_a_douze_mois(client, bases):
    client.post(f"{V1}/public/rappel", json={**DEMANDE, "nom": "Ancienne demande"})
    with bases[0].begin() as c:
        c.execute(text("UPDATE demandes_rappel SET recue_le = now() - interval '13 months' WHERE nom = 'Ancienne demande'"))
    assert demandes_rappel.effacer_anciennes(bases[1], datetime.now(timezone.utc)) >= 1
    with bases[0].connect() as c:
        assert c.execute(text("SELECT count(*) FROM demandes_rappel WHERE nom = 'Ancienne demande'")).scalar() == 0
    assert demandes_rappel.effacer_anciennes(bases[1], datetime.now(timezone.utc) - timedelta(days=1)) == 0
