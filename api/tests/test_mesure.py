"""La mesure d'audience sans témoin : un compteur par jour, événement et source ; les événements du serveur ; la
lecture du courtier ; rien d'autre n'est gardé."""
from datetime import date

from sqlalchemy import text

from courtage.services import mesure
from tests.outils import V1, en_tant_que


def total(bases, evenement):
    with bases[0].connect() as c:
        return c.execute(text("SELECT coalesce(sum(n), 0) FROM mesures WHERE evenement = :e AND jour = :j"),
                         {"e": evenement, "j": date.today()}).scalar()


def test_la_page_compte_une_visite_par_source(client, bases):
    avant = total(bases, "vitrine")
    assert client.post(f"{V1}/public/mesure", json={"evenement": "vitrine", "referent": "https://www.google.com/search?q=ifc"}).status_code == 204
    client.post(f"{V1}/public/mesure", json={"evenement": "vitrine", "referent": "https://l.facebook.com/x"})
    client.post(f"{V1}/public/mesure", json={"evenement": "vitrine"})
    assert total(bases, "vitrine") == avant + 3
    # Ce que compte le serveur ne se compte pas depuis la page ; un événement inconnu est refusé.
    avant_inscription = total(bases, "inscription_faite")
    client.post(f"{V1}/public/mesure", json={"evenement": "inscription_faite"})
    assert total(bases, "inscription_faite") == avant_inscription
    # Rien d'autre que le compteur : la table n'a ni adresse, ni référent, ni identifiant.
    with bases[0].connect() as c:
        colonnes = set(c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'mesures'")).scalars())
    assert colonnes == {"jour", "evenement", "source", "n"}


def test_les_sources():
    assert mesure.source(None, "courtage.cm") == "direct"
    assert mesure.source("https://courtage.cm/ifc", "courtage.cm") == "direct"
    assert mesure.source("https://www.google.cm/", "courtage.cm") == "recherche"
    assert mesure.source("https://www.linkedin.com/feed", "courtage.cm") == "reseau_social"
    assert mesure.source("https://t.co/abc", "courtage.cm") == "reseau_social"
    assert mesure.source("https://journal.cm/article", "courtage.cm") == "autre"


def test_le_courtier_lit_l_entonnoir(client, personnes):
    client.post(f"{V1}/public/mesure", json={"evenement": "essai_ouvert"})
    r = client.get(f"{V1}/mesures", headers=en_tant_que(personnes["admin"]))
    assert r.status_code == 200
    e = r.json()["entonnoir"]
    assert [x["evenement"] for x in e] == list(mesure.ENTONNOIR) and e[0]["taux"] is None
    assert client.get(f"{V1}/mesures", headers=en_tant_que(personnes["drh"])).status_code == 403


def test_l_inscription_se_compte_cote_serveur(client, bases):
    from tests.test_inscription import inscrire
    avant = total(bases, "inscription_faite")
    assert inscrire(client).status_code == 201
    assert total(bases, "inscription_faite") == avant + 1
