"""Le compte, l'accès et l'inscription parlent anglais quand l'écran le demande ; français sinon."""
from tests.outils import V1, en_tant_que
from tests.test_activation import mettre_en_attente, u

EN = {"X-Langue": "en"}


def test_un_acces_refuse_en_anglais(client, azito):
    h = en_tant_que(azito["etranger"])
    fr = client.get(u(azito, "/activation"), headers=h)
    en = client.get(u(azito, "/activation"), headers={**h, **EN})
    assert fr.status_code == en.status_code == 403
    assert fr.json()["code"] == en.json()["code"] == "acces_refuse"
    assert fr.json()["message"] == "Vous n'êtes pas membre de cette organisation."
    assert en.json()["message"] == "You are not a member of this organisation."


def test_les_libelles_de_l_activation_en_anglais(client, azito, bases):
    mettre_en_attente(bases, azito["org"])
    h = en_tant_que(azito["drh"])
    fr = client.get(u(azito, "/activation"), headers=h).json()
    en = client.get(u(azito, "/activation"), headers={**h, **EN}).json()
    assert fr["libelles"]["catalogue"] == "le catalogue anonyme"
    assert en["libelles"]["catalogue"] == "the anonymous catalogue"
    assert set(fr["libelles"]) == set(en["libelles"])
    refus = client.get(f"{V1}/catalogue/regimes", headers={**h, **EN}).json()
    assert refus["code"] == "inscription_non_confirmee" and refus["message"].startswith("The anonymous catalogue")
