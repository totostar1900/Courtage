"""Les avis par courriel : envoyés après la validation, à qui l'événement attend, jamais à son auteur, sans rien du
dossier dans le corps ; coupés depuis le profil."""
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from courtage.messagerie import CourrielJournal
from courtage.services import avis
from tests.outils import V1, en_tant_que


def adresse(bases, qui):
    with bases[0].connect() as c:
        return c.execute(text("SELECT email FROM utilisateurs WHERE id = :i"), {"i": qui}).scalar_one()


def recus(client, bases, qui):
    a = adresse(bases, qui)
    return [m.texte for m in client.app.state.courriel.envoyes if m.telephone == a]


def test_un_message_previent_l_autre_cote_sans_son_texte(client, bases, azito):
    r = client.post(f"{V1}/organisations/{azito['org']}/messages", json={"texte": "Notre effectif change en mars."},
                    headers=en_tant_que(azito["drh"]))
    assert r.status_code in (200, 201), r.text
    [avis_conseiller] = recus(client, bases, azito["conseiller"])
    assert "a écrit dans le fil du dossier AZITO" in avis_conseiller
    assert f"/dossier/{azito['org']}/contact" in avis_conseiller
    assert "effectif" not in avis_conseiller                  # le texte reste sur la plateforme
    assert recus(client, bases, azito["drh"]) == []           # l'auteur n'est pas prévenu de son propre acte
    client.post(f"{V1}/organisations/{azito['org']}/messages", json={"texte": "Bien reçu."},
                headers=en_tant_que(azito["conseiller"]))
    assert len(recus(client, bases, azito["drh"])) == 1


def test_le_mandat_previent_a_chaque_etape(client, bases, azito):
    url = f"{V1}/organisations/{azito['org']}/mandats"
    m = client.post(url, json={"besoins": ["placement"]}, headers=en_tant_que(azito["drh"])).json()
    assert any("demande un accompagnement" in x for x in recus(client, bases, azito["conseiller"]))
    p = client.put(f"{url}/{m['id']}/proposition", headers=en_tant_que(azito["conseiller"]), json={
        "perimetre": ["analyse"], "date_effet": (date.today() + timedelta(days=5)).isoformat(), "duree_mois": 12,
        "preavis_mois": 3, "exclusif": True}).json()
    assert any("mandat de courtage" in x and "signez-le" in x for x in recus(client, bases, azito["drh"]))
    client.post(f"{url}/{m['id']}/signature", headers=en_tant_que(azito["drh"]), json={
        "nom": "Awa Kouassi", "empreinte": p["proposition"]["empreinte"], "accepte": True,
        "qualite": "representant_legal"})
    assert any("a signé le mandat de courtage (N° MC-" in x for x in recus(client, bases, azito["conseiller"]))


def test_un_acte_refuse_ne_previent_personne(client, bases, azito):
    avant = len(client.app.state.courriel.envoyes)
    url = f"{V1}/organisations/{azito['org']}/mandats"
    m = client.post(url, json={"besoins": ["placement"]}, headers=en_tant_que(azito["drh"])).json()
    assert len(client.app.state.courriel.envoyes) > avant
    avant = len(client.app.state.courriel.envoyes)
    # Proposer dans le passé est refusé : rien ne part.
    r = client.put(f"{url}/{m['id']}/proposition", headers=en_tant_que(azito["conseiller"]), json={
        "perimetre": ["analyse"], "date_effet": "2020-01-01", "duree_mois": 12, "preavis_mois": 3, "exclusif": True})
    assert r.status_code == 422
    assert len(client.app.state.courriel.envoyes) == avant


def test_prevu_puis_annule_ne_part_pas(bases, azito):
    courriel = CourrielJournal()
    with Session(bases[1]) as session:
        session.info.update(courriel=courriel, url_publique="https://exemple.cm")
        with session.begin():
            n = avis.prevoir(session, "mandat_propose", [azito["drh"]], auteur=None, org=azito["org"], entreprise="AZITO")
            assert n == 1 and courriel.envoyes == []          # rien avant la validation
            session.rollback()
    assert courriel.envoyes == []


def test_couper_les_avis_depuis_le_profil(client, bases, azito):
    r = client.patch(f"{V1}/moi/profil", json={"avis_courriel": False}, headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 200 and r.json()["avis_courriel"] is False
    client.post(f"{V1}/organisations/{azito['org']}/messages", json={"texte": "Bonjour"}, headers=en_tant_que(azito["drh"]))
    assert recus(client, bases, azito["conseiller"]) == []
    # Le nom se change toujours seul.
    assert client.patch(f"{V1}/moi/profil", json={"nom_affiche": "Conseiller A"},
                        headers=en_tant_que(azito["conseiller"])).json()["avis_courriel"] is False


def test_l_inscription_previent_le_courtier_puis_le_client(client, bases, personnes):
    from tests.test_inscription import inscrire
    corps = inscrire(client).json()
    org, drh = corps["organisation_id"], corps["utilisateur"]["id"]
    assert any("Brasseries du Littoral vient de s'inscrire" in x for x in recus(client, bases, personnes["admin"]))
    # Le file dit aussi si l'entreprise a demandé un accompagnement.
    client.post(f"{V1}/organisations/{org}/mandats", json={"besoins": ["placement"]}, headers=en_tant_que(drh))
    [ligne] = [i for i in client.get(f"{V1}/inscriptions", headers=en_tant_que(personnes["admin"])).json()["inscriptions"]
               if i["id"] == org]
    assert ligne["accompagnement_demande"] is True
    client.post(f"{V1}/inscriptions/{org}/decision", headers=en_tant_que(personnes["admin"]),
                json={"decision": "refuser", "motif": "RCCM illisible."})
    [refus] = [x for x in recus(client, bases, drh) if "pas été confirmée" in x]
    assert "Motif : RCCM illisible." in refus
