"""L'en-tête X-Langue : l'écran reçoit sa langue ; sans lui, le français."""
from courtage import langue
from tests.outils import V1


def test_une_erreur_dans_la_langue_de_l_ecran(client):
    corps = {"telephone": "+237699000001", "preuve_telephone": "1.x", "courriel": "a@b.cm", "preuve_courriel": "1.x",
             "nom": "Awa", "entreprise": {"nom": "X SA", "pays": "CM", "rccm": "RC123456", "taille": "moins_de_50"}}
    fr = client.post(f"{V1}/inscription", json=corps).json()
    en = client.post(f"{V1}/inscription", json=corps, headers={"X-Langue": "en"}).json()
    assert fr["code"] == en["code"] == "telephone_non_verifie"
    assert fr["message"].startswith("Vérifiez") and en["message"].startswith("Verify")


def test_traduire_un_message_enregistre():
    langue.TRADUCTIONS["essai_code"] = [(r"(?P<n>\d+) salariés", "{n} employees")]
    jeton = langue.definir("en")
    try:
        assert langue.traduire("essai_code", "23 salariés") == "23 employees"
        assert langue.traduire("inconnu", "tel quel") == "tel quel"
    finally:
        langue._langue.reset(jeton)
        del langue.TRADUCTIONS["essai_code"]
