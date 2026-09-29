"""La consultation des assureurs : le cahier part depuis la plateforme, avec un lien personnel ; l'assureur dépose son
offre sans compte ; elle est classée avec les autres, marquée déposée par l'assureur."""
import json
import re
from datetime import date

from sqlalchemy import text

from tests.outils import V1, en_tant_que
from tests.test_reponses import CONFORME, PDF, cahier, u  # noqa: F401 — `cahier` est une fixture

GRILLE = {k: v for k, v in CONFORME.items() if k not in ("assureur", "recue_le")}


def consulter(client, a, assureur="Assureur Lien", courriel="offres@assureur-lien.cm"):
    return client.post(u(a, "/consultations"), headers=en_tant_que(a["conseiller"]),
                       json={"assureur": assureur, "contact_nom": "Mme Tchoua", "contact_courriel": courriel})


def lien_envoye(client, courriel="offres@assureur-lien.cm") -> str:
    [dernier] = [m for m in client.app.state.courriel.envoyes if m.telephone == courriel][-1:]
    return re.search(r"/offre/([A-Za-z0-9_\-]+)", dernier.texte).group(1)


def deposer(client, jeton, offre=PDF, **grille):
    fichiers = {"offre": ("offre.pdf", offre)} if offre else None
    return client.post(f"{V1}/offre/{jeton}", data={"donnees": json.dumps({**GRILLE, **grille})}, files=fichiers)


def test_consulter_puis_l_assureur_depose_son_offre(client, bases, cahier):  # noqa: F811
    assert consulter(client, cahier).status_code == 201
    # Le courriel porte le lien ; le jeton n'est gardé nulle part en clair.
    [courriel] = [m for m in client.app.state.courriel.envoyes if m.telephone == "offres@assureur-lien.cm"]
    assert "AZITO" in courriel.texte and "Cahier des charges N° " in courriel.texte
    jeton = lien_envoye(client)
    with bases[0].connect() as c:
        assert c.execute(text("SELECT count(*) FROM liens_assureurs WHERE jeton_hash = :j"), {"j": jeton}).scalar() == 0
    # L'assureur lit sans compte : le client, le cahier, la date limite, les conditions.
    vue = client.get(f"{V1}/offre/{jeton}")
    assert vue.status_code == 200, vue.text
    v = vue.json()
    assert v["client"] == "AZITO" and v["assureur"] == "Assureur Lien" and v["etat"] == "ouverte"   # la lecture marque l'ouverture
    assert any(x["cle"] == "taux_garanti_minimum" for x in v["conditions"])
    assert client.get(f"{V1}/offre/{jeton}/cahier").headers["content-type"] == "application/pdf"
    [ligne] = client.get(u(cahier, "/consultations"), headers=en_tant_que(cahier["drh"])).json()
    assert ligne["ouverte_le"] and ligne["etat"] == "ouverte"
    # L'offre PDF est obligatoire ; déposée, elle est classée avec les autres.
    assert deposer(client, jeton, offre=None).json()["code"] == "offre_requise"
    r = deposer(client, jeton)
    assert r.status_code == 201 and r.json()["etat"] == "repondue"
    tout = client.get(u(cahier, "/reponses"), headers=en_tant_que(cahier["drh"])).json()
    [rep] = [x for x in tout["reponses"] if x["assureur"] == "Assureur Lien"]
    assert rep["deposee_par_assureur"] is True and rep["recue_le"] == date.today().isoformat() and rep["offre"]
    # Une seule réponse par lien ; le conseiller est prévenu.
    assert deposer(client, jeton).json()["code"] == "deja_repondu"
    assert any("Assureur Lien a déposé son offre" in m.texte for m in client.app.state.courriel.envoyes)


def test_relancer_emet_un_lien_neuf_et_annuler_le_ferme(client, cahier):  # noqa: F811
    c = consulter(client, cahier, "Assureur Relance", "contact@relance.cm").json()
    ancien = lien_envoye(client, "contact@relance.cm")
    assert consulter(client, cahier, "ASSUREUR  relance", "autre@relance.cm").json()["code"] == "consultation_existante"
    r = client.post(f"{V1}/organisations/{cahier['org']}/consultations/{c['id']}/relance", headers=en_tant_que(cahier["conseiller"]))
    assert r.json()["relances"] == 1
    neuf = lien_envoye(client, "contact@relance.cm")
    assert neuf != ancien
    assert client.get(f"{V1}/offre/{ancien}").json()["code"] == "lien_inconnu"
    assert client.get(f"{V1}/offre/{neuf}").status_code == 200
    client.post(f"{V1}/organisations/{cahier['org']}/consultations/{c['id']}/annulation", headers=en_tant_que(cahier["conseiller"]))
    assert client.get(f"{V1}/offre/{neuf}").json()["code"] == "lien_inconnu"


def test_seul_le_conseiller_consulte_et_un_cahier_attribue_ferme_le_lien(client, cahier):  # noqa: F811
    assert client.post(u(cahier, "/consultations"), headers=en_tant_que(cahier["drh"]),
                       json={"assureur": "X", "contact_courriel": "x@y.cm"}).status_code == 403
    consulter(client, cahier, "Assureur Tard", "tard@assureur.cm")
    jeton = lien_envoye(client, "tard@assureur.cm")
    # Une autre offre, saisie par le conseiller, est choisie : la consultation se ferme.
    r = client.post(u(cahier, "/reponses"), headers=en_tant_que(cahier["conseiller"]),
                    data={"donnees": json.dumps(CONFORME)})
    client.post(u(cahier, "/choix"), json={"reponse_id": r.json()["id"]}, headers=en_tant_que(cahier["drh"]))
    assert client.get(f"{V1}/offre/{jeton}").json()["etat"] == "close"
    assert deposer(client, jeton).json()["code"] == "consultation_close"


def test_un_lien_inconnu(client):
    assert client.get(f"{V1}/offre/inexistant").status_code == 404
