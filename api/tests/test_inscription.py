"""L'inscription en libre-service, la file du courtier, l'effacement à 30 jours."""
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from courtage.cabinet import CONDITIONS_VERSION
from courtage.services import activation
from tests.outils import V1, deposer, en_tant_que, etude, fichier_azito
from tests.test_prestations import DEPART


def code_envoye(client, nature):
    etat = client.app.state
    dernier = (etat.expediteur.envoyes if nature == "telephone" else etat.courriel.envoyes)[-1]
    return re.search(r"\b(\d{6})\b", dernier.texte).group(1)


def verifier(client, nature, cible):
    assert client.post(f"{V1}/inscription/code", json={"nature": nature, "cible": cible}).status_code == 200
    r = client.post(f"{V1}/inscription/verification", json={"nature": nature, "cible": cible,
                                                             "code": code_envoye(client, nature)})
    assert r.status_code == 200, r.text
    return r.json()["preuve"]


def inscrire(client, rccm=None, telephone=None, courriel=None, **autres):
    telephone = telephone or f"+2376{uuid.uuid4().int % 10**8:08d}"
    courriel = courriel or f"drh-{uuid.uuid4().hex[:8]}@exemple.cm"
    corps = {"telephone": telephone, "preuve_telephone": verifier(client, "telephone", telephone),
             "courriel": courriel, "preuve_courriel": verifier(client, "courriel", courriel),
             "nom": "Awa Kouassi", "fonction": "DRH",
             "entreprise": {"nom": "Brasseries du Littoral", "pays": "CM",
                            "rccm": rccm or f"RC/DLA/2024/B/{uuid.uuid4().int % 10**6}", "taille": "50_a_250",
                            "secteur": "Industrie", "ville": "Douala"}, "conditions": CONDITIONS_VERSION, **autres}
    r = client.post(f"{V1}/inscription", json=corps)
    if r.status_code == 201:
        assert "courtage_session" in r.headers.get("set-cookie", "")       # la session s'ouvre à l'inscription
    client.cookies.clear()      # la suite parle par en-tête (le cookie exigerait l'en-tête anti-CSRF du navigateur)
    return r


def test_s_inscrire_ouvre_un_dossier_en_attente(client):
    r = inscrire(client)
    assert r.status_code == 201, r.text
    corps = r.json()
    assert corps["activation"]["etat"] == "en_attente" and "echeance" in corps["activation"]
    moi = client.get(f"{V1}/moi", headers=en_tant_que(corps["utilisateur"]["id"])).json()
    [o] = moi["organisations"]
    assert (o["role"], o["activation"]) == ("admin_client", "en_attente")


def test_les_conditions_en_vigueur_s_acceptent_et_se_gardent(client):
    assert inscrire(client, conditions=None).json()["code"] == "conditions_requises"
    r = inscrire(client, conditions="conditions-1999")
    assert r.status_code == 422 and r.json()["details"]["version"] == CONDITIONS_VERSION
    corps = inscrire(client).json()
    p = client.get(f"{V1}/moi/profil", headers=en_tant_que(corps["utilisateur"]["id"])).json()
    assert p["conditions"]["version"] == CONDITIONS_VERSION and p["conditions"]["le"]


def test_sans_preuve_ou_avec_un_mauvais_code(client):
    r = client.post(f"{V1}/inscription/verification", json={"nature": "courriel", "cible": "x@y.cm", "code": "000000"})
    assert r.status_code == 401
    r = client.post(f"{V1}/inscription", json={
        "telephone": "+237699000001", "preuve_telephone": "1.faux", "courriel": "a@b.cm", "preuve_courriel": "1.faux",
        "nom": "Awa", "entreprise": {"nom": "X SA", "pays": "CM", "rccm": "RC123456", "taille": "moins_de_50"}})
    assert r.json()["code"] == "telephone_non_verifie"


def test_une_entreprise_un_dossier(client):
    rccm = f"RC/YAO/2020/B/{uuid.uuid4().int % 10**6}"
    assert inscrire(client, rccm=rccm).status_code == 201
    r = inscrire(client, rccm=rccm.lower().replace("/", " "))
    assert r.status_code == 409 and r.json()["code"] == "entreprise_deja_inscrite"


def test_la_file_du_courtier_puis_la_confirmation(client, personnes, azito):     # azito : le conseiller en suit déjà un
    corps = inscrire(client).json()
    org, drh = corps["organisation_id"], corps["utilisateur"]["id"]
    # Le client dépose son RCCM.
    r = client.post(f"{V1}/organisations/{org}/justificatifs", headers=en_tant_que(drh),
                    files={"fichier": ("rccm.pdf", b"%PDF-1.4 rccm", "application/pdf")})
    assert r.status_code == 201, r.text
    admin = en_tant_que(personnes["admin"])
    assert client.get(f"{V1}/inscriptions", headers=en_tant_que(drh)).status_code == 403
    [ligne] = [i for i in client.get(f"{V1}/inscriptions", headers=admin).json()["inscriptions"] if i["id"] == org]
    assert ligne["rccm_depose"] and ligne["demandeur"]["fonction"] == "DRH" and ligne["en_retard"] is False
    [piece] = ligne["justificatifs"]
    doc = client.get(f"{V1}/inscriptions/{org}/justificatifs/{piece['id']}", headers=admin)
    assert doc.status_code == 200 and doc.content == b"%PDF-1.4 rccm"
    # Refuser demande un motif ; confirmer désigne le conseiller.
    assert client.post(f"{V1}/inscriptions/{org}/decision", headers=admin,
                       json={"decision": "refuser"}).json()["code"] == "motif_requis"
    r = client.post(f"{V1}/inscriptions/{org}/decision", headers=admin, json={
        "decision": "confirmer", "conseiller_id": str(personnes["conseiller"]),
        "verification": {"rccm_recu": True, "appel_le": "2026-09-28", "habilitation": "DRH, délégation du DG"}})
    assert r.status_code == 200, r.text
    assert r.json()["etat"] == "confirmee" and r.json()["capacites"]["rapport_scelle"] is True
    equipe = client.get(f"{V1}/organisations/{org}/equipe", headers=en_tant_que(drh)).json()
    assert any(m["role"] == "conseiller" for m in equipe["membres"])
    assert client.post(f"{V1}/inscriptions/{org}/decision", headers=admin,
                       json={"decision": "confirmer"}).json()["code"] == "deja_decidee"


def test_le_client_retire_son_inscription(client, bases):
    corps = inscrire(client).json()
    org, drh = corps["organisation_id"], corps["utilisateur"]["id"]
    # Du travail déjà fait : le personnel, une étude, un message au courtier… tout part. (Un départ, non : les
    # départs attendent le contrat d'assurance.)
    f = deposer(client, org, drh, fichier_azito())
    assert etude(client, {"org": org, "fichier": f["id"], "drh": drh}).status_code == 201
    assert client.post(f"{V1}/organisations/{org}/prestations", headers=en_tant_que(drh),
                       json={**DEPART, "verse": 1}).json()["code"] == "inscription_non_confirmee"
    url = f"{V1}/organisations/{org}/inscription"
    assert client.delete(url, headers=en_tant_que(drh)).json()["code"] == "confirmation_requise"
    assert client.delete(url, params={"confirmation": "SUPPRIMER"}, headers=en_tant_que(drh)).status_code == 200
    with bases[0].connect() as c:
        assert c.execute(text("SELECT etat FROM organisations WHERE id = :o"), {"o": org}).scalar() == "supprime"
        for table in ("fichiers_personnel", "etudes", "prestations", "adhesions"):
            assert c.execute(text(f"SELECT count(*) FROM {table} WHERE organisation_id = :o"), {"o": org}).scalar() == 0


def test_trente_jours_sans_confirmation(client, bases):
    corps = inscrire(client).json()
    org = corps["organisation_id"]
    with bases[0].begin() as c:
        c.execute(text("UPDATE organisations SET activation_demandee_le = now() - interval '31 days' WHERE id = :o"),
                  {"o": org})
    assert activation.effacer_expirees_partout(bases[1], datetime.now(timezone.utc)) >= 1
    with bases[0].connect() as c:
        assert c.execute(text("SELECT etat FROM organisations WHERE id = :o"), {"o": org}).scalar() == "supprime"


def test_un_dossier_confirme_ne_s_efface_pas_ainsi(client, azito):
    r = client.delete(f"{V1}/organisations/{azito['org']}/inscription", params={"confirmation": "SUPPRIMER"},
                      headers=en_tant_que(azito["drh"]))
    assert r.status_code == 409 and r.json()["code"] == "inscription_confirmee"


def test_le_fil_entre_l_entreprise_et_le_courtier(client, personnes):
    corps = inscrire(client).json()
    org, drh = corps["organisation_id"], corps["utilisateur"]["id"]
    admin = en_tant_que(personnes["admin"])
    r = client.post(f"{V1}/organisations/{org}/messages", json={"texte": "Bonjour, quand pouvez-vous m'appeler ?"},
                    headers=en_tant_que(drh))
    assert r.status_code == 201 and r.json()["messages"][0]["cote"] == "entreprise"
    [ligne] = [i for i in client.get(f"{V1}/inscriptions", headers=admin).json()["inscriptions"] if i["id"] == org]
    assert ligne["messages_non_lus"] == 1
    fil = client.get(f"{V1}/inscriptions/{org}/messages", headers=admin).json()
    assert fil["messages"][0]["lu_le"] is not None                            # lu par le courtier en l'ouvrant
    client.post(f"{V1}/inscriptions/{org}/messages", json={"texte": "Demain à 10 h."}, headers=admin)
    assert client.get(f"{V1}/organisations/{org}/messages/non-lus", headers=en_tant_que(drh)).json() == {"non_lus": 1}
    assert client.post(f"{V1}/organisations/{org}/messages", json={"texte": " "}, headers=en_tant_que(drh)).status_code == 422


def test_l_essai_se_reprend_dans_le_dossier(client):
    """Ce que fait l'écran après l'inscription : le fichier de l'essai, puis le modèle type en version à l'analyse."""
    corps = inscrire(client).json()
    org, h = corps["organisation_id"], en_tant_que(corps["utilisateur"]["id"])
    f = client.post(f"{V1}/organisations/{org}/fichiers", headers=h, data={"date_donnees": "2025-12-31"},
                    files={"fichier": ("personnel.xlsx", fichier_azito())})
    assert f.status_code == 201, f.text
    modele = client.get(f"{V1}/referentiel/modeles", params={"pays": "CM"}).json()["modeles"][0]
    r = client.post(f"{V1}/organisations/{org}/regimes", headers=h, json={"nom": modele["titre"]}).json()
    v = client.post(f"{V1}/organisations/{org}/regimes/{r['id']}/versions", headers=h,
                    json={**modele["version"], "en_vigueur_du": "2025-12-31"})
    assert v.status_code == 201, v.text



def test_le_courtier_confie_le_dossier_a_un_conseiller(client, personnes, azito):
    corps = inscrire(client).json()
    org, drh = corps["organisation_id"], corps["utilisateur"]["id"]
    admin = en_tant_que(personnes["admin"])
    assert client.get(f"{V1}/inscriptions/conseillers", headers=en_tant_que(drh)).status_code == 403
    liste = client.get(f"{V1}/inscriptions/conseillers", headers=admin).json()["conseillers"]
    ids = {c["id"] for c in liste}
    assert str(personnes["conseiller"]) in ids and str(personnes["admin"]) in ids and drh not in ids
    assert next(c for c in liste if c["id"] == str(personnes["admin"]))["moi"] is True
    # Un utilisateur qui n'est pas conseiller ne se voit pas confier un dossier.
    r = client.post(f"{V1}/inscriptions/{org}/decision", headers=admin,
                    json={"decision": "confirmer", "conseiller_id": drh})
    assert r.status_code == 422 and r.json()["code"] == "conseiller_inconnu"
    r = client.post(f"{V1}/inscriptions/{org}/decision", headers=admin,
                    json={"decision": "confirmer", "conseiller_id": str(personnes["conseiller"])})
    assert r.status_code == 200, r.text
    membres = client.get(f"{V1}/organisations/{org}/equipe", headers=en_tant_que(drh)).json()["membres"]
    assert [m["id"] for m in membres if m["role"] == "conseiller"] == [str(personnes["conseiller"])]


def test_l_accompagnement_se_demande_des_l_inscription(client, personnes):
    """La demande d'accompagnement est une des premières choses que l'entreprise dit : elle part avec l'inscription."""
    besoins = client.get(f"{V1}/public/besoins").json()["besoins"]
    assert {b["code"] for b in besoins} >= {"placement", "mise_en_concurrence"}
    r = inscrire(client, accompagnement={"besoins": ["placement", "prestations"], "message": "Contrat actuel échu en mars."})
    assert r.status_code == 201, r.text
    org, drh = r.json()["organisation_id"], r.json()["utilisateur"]["id"]
    m = client.get(f"{V1}/organisations/{org}/mandats", headers=en_tant_que(drh)).json()
    [courant] = [x for x in m["mandats"] if x["statut"] == "demande"]
    assert {b["code"] for b in courant["besoins"]} == {"placement", "prestations"}
    [ligne] = [i for i in client.get(f"{V1}/inscriptions", headers=en_tant_que(personnes["admin"])).json()["inscriptions"]
               if i["id"] == org]
    assert ligne["accompagnement_demande"] is True
    # Un besoin inconnu défait tout : pas de dossier à moitié créé.
    r = inscrire(client, accompagnement={"besoins": ["inconnu"]})
    assert r.status_code == 422 and r.json()["code"] == "besoins_requis"
