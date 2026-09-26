"""Les points d'attention d'un dossier : calculés à la lecture, disparus quand leur cause l'est."""
from datetime import date

from sqlalchemy.orm import Session

from courtage.db import Organisation, contexte
from courtage.services import alertes
from tests.outils import V1, en_tant_que, etude
from tests.test_dossiers import depart  # noqa: F401  (fixture)
from tests.test_rapport import emettre
from tests.test_reponses import cahier  # noqa: F401  (fixture)


def calculer(bases, org_id, le):
    with Session(bases[1]) as session, session.begin():
        contexte(session.connection(), org_id)
        return alertes.du_dossier(session, session.get(Organisation, org_id), le)


def codes(liste):
    return {a["code"]: a["niveau"] for a in liste}


def test_une_etude_ancienne_et_des_donnees_anciennes(client, azito, bases):
    emettre(client, azito)                                   # étude et données au 31/12/2019
    assert codes(calculer(bases, azito["org"], date(2020, 6, 30))) == {}
    un_an = codes(calculer(bases, azito["org"], date(2021, 1, 31)))
    assert un_an == {"etude_a_renouveler": "attention", "donnees_anciennes": "attention"}
    assert codes(calculer(bases, azito["org"], date(2022, 6, 30)))["etude_a_renouveler"] == "grave"


def test_sans_etude_emise_le_dossier_le_dit(client, azito, bases):
    etude(client, azito)                                      # un brouillon seulement
    liste = calculer(bases, azito["org"], date(2020, 1, 15))
    assert codes(liste) == {"aucune_etude": "info"}
    assert liste[0]["lien"] == "etudes" and liste[0]["pour"] == "entreprise"
    tard = codes(calculer(bases, azito["org"], date.today() + __import__("datetime").timedelta(days=45)))
    assert tard.get("brouillon_en_attente") == "info"


def test_les_routes(client, azito):
    emettre(client, azito)
    liste = client.get(f"{V1}/organisations/{azito['org']}/alertes", headers=en_tant_que(azito["drh"])).json()
    assert [a["code"] for a in liste][:1] == ["etude_a_renouveler"] and liste[0]["niveau"] == "grave"
    assert {"titre", "detail", "lien", "pour"} <= set(liste[0])
    decompte = client.get(f"{V1}/alertes", headers=en_tant_que(azito["drh"])).json()
    assert decompte[azito["org"]]["grave"] >= 1
    assert client.get(f"{V1}/organisations/{azito['org']}/alertes", headers=en_tant_que(azito["etranger"])).status_code == 403
    assert azito["org"] not in client.get(f"{V1}/alertes", headers=en_tant_que(azito["etranger"])).json()


def test_les_prises_en_charge_qui_n_avancent_plus(client, depart, bases):  # noqa: F811
    from datetime import timedelta
    from tests.test_dossiers import etape, jusqu_a_transmis
    t = jusqu_a_transmis(client, depart, le=(date.today() - timedelta(days=60)).isoformat())
    liste = calculer(bases, depart["org"], date.today())
    retard = next(a for a in liste if a["code"] == "retard_assureur")
    assert retard["niveau"] == "grave" and retard["lien"] == f"dossiers/{t['id']}" and "Relancer l'assureur" in retard["detail"]
    etape(client, depart, t["id"], "reponse", paye=False, motif="Pièce illisible", le=date.today().isoformat())
    liste = codes(calculer(bases, depart["org"], date.today()))
    assert "retard_assureur" not in liste and liste["prise_en_charge_refusee"] == "attention"


def test_un_cahier_echu(client, cahier, bases):  # noqa: F811
    from datetime import timedelta
    from tests.test_reponses import repondre
    limite = date.fromisoformat(cahier["fiche"]["date_limite_reponse"])
    assert codes(calculer(bases, cahier["org"], limite + timedelta(days=1)))["aucune_reponse"] == "attention"
    repondre(client, cahier)
    assert codes(calculer(bases, cahier["org"], limite + timedelta(days=1)))["assureur_a_choisir"] == "attention"
