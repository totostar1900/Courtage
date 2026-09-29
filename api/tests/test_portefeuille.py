"""Le pipeline et le portefeuille du courtier : chaque dossier à son étape, les dossiers sous mandat avec ce qui les
attend ; tout pour l'administrateur, les siens pour un conseiller, rien pour un client."""
from tests.outils import V1, en_tant_que, sous_mandat
from tests.test_placement import police


def lire(client, qui):
    return client.get(f"{V1}/portefeuille", headers=en_tant_que(qui))


def test_chaque_dossier_a_son_etape_et_le_portefeuille_sous_mandat(client, azito):
    r = lire(client, azito["admin"])
    assert r.status_code == 200, r.text
    [ligne] = [d for d in r.json()["dossiers"] if d["id"] == azito["org"]]
    assert ligne["etape"] == "confirme" and ligne["conseillers"] == ["Conseiller"] and "portefeuille" not in ligne
    sous_mandat(client, azito)
    police(client, {**azito}, "Assureur Portefeuille")
    [ligne] = [d for d in lire(client, azito["admin"]).json()["dossiers"] if d["id"] == azito["org"]]
    assert ligne["etape"] == "sous_mandat"
    p = ligne["portefeuille"]
    assert p["polices"][0]["assureur"] == "Assureur Portefeuille" and p["primes_en_retard"] == 0
    comptes = {e["code"]: e["n"] for e in lire(client, azito["admin"]).json()["etapes"]}
    assert comptes["sous_mandat"] >= 1


def test_qui_voit_quoi(client, azito):
    # Le conseiller voit ses dossiers ; un client, rien.
    assert any(d["id"] == azito["org"] for d in lire(client, azito["conseiller"]).json()["dossiers"])
    assert lire(client, azito["drh"]).status_code == 403
    assert lire(client, azito["etranger"]).status_code == 403
