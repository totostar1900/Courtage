"""Les avis sur WhatsApp : pour qui les a demandés, au numéro de son compte, par le modèle approuvé — le sujet et le
lien, rien du dossier. Sans modèle, rien ne part et le profil ne le propose pas (spec 2026-09-29 §4)."""
import uuid

import httpx
from sqlalchemy import text

from courtage.messagerie import ExpediteurJournal, ExpediteurTwilio, WhatsAppAvis, whatsapp_depuis_environnement
from tests.outils import V1, en_tant_que


def numero(bases, qui) -> str:
    tel = f"+2376{uuid.uuid4().int % 10**8:08d}"
    with bases[0].begin() as c:
        c.execute(text("UPDATE utilisateurs SET telephone = :t WHERE id = :i"), {"t": tel, "i": qui})
    return tel


def test_sans_modele_rien_ne_part_et_le_profil_ne_le_propose_pas(client, bases, azito):
    numero(bases, azito["conseiller"])
    p = client.get(f"{V1}/moi/profil", headers=en_tant_que(azito["conseiller"])).json()
    assert p["whatsapp_disponible"] is False and p["avis_whatsapp"] is False


def test_un_avis_part_aussi_sur_whatsapp_pour_qui_l_a_demande(client, bases, azito):
    wa = WhatsAppAvis(ExpediteurJournal(), "HX_modele")
    client.app.state.whatsapp = wa
    tel = numero(bases, azito["conseiller"])
    numero(bases, azito["drh"])
    # Désactivé par défaut : un message ne part que par courriel.
    client.post(f"{V1}/organisations/{azito['org']}/messages", json={"texte": "Effectif de mars."},
                headers=en_tant_que(azito["drh"]))
    assert wa.expediteur.envoyes == []
    r = client.patch(f"{V1}/moi/profil", json={"avis_whatsapp": True}, headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 200 and r.json()["avis_whatsapp"] is True and r.json()["whatsapp_disponible"] is True
    client.post(f"{V1}/organisations/{azito['org']}/messages", json={"texte": "Effectif de mars."},
                headers=en_tant_que(azito["drh"]))
    [m] = wa.expediteur.envoyes
    assert m.telephone == tel
    assert m.texte.startswith("Un message vous attend — ") and m.texte.endswith(f"/dossier/{azito['org']}/contact")
    assert "Effectif" not in m.texte and "AZITO" not in m.texte     # le sujet et le lien, rien du dossier
    # L'auteur n'est jamais prévenu de son propre acte, sur aucun canal.
    client.post(f"{V1}/organisations/{azito['org']}/messages", json={"texte": "Reçu."},
                headers=en_tant_que(azito["conseiller"]))
    assert len(wa.expediteur.envoyes) == 1


def test_sans_numero_le_profil_refuse(client, bases, azito):
    client.app.state.whatsapp = WhatsAppAvis(ExpediteurJournal(), "HX_modele")
    r = client.patch(f"{V1}/moi/profil", json={"avis_whatsapp": True}, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 422 and r.json()["code"] == "telephone_absent"


def test_la_configuration_exige_un_modele_et_un_emetteur_whatsapp():
    base = {"TWILIO_COMPTE": "AC1", "TWILIO_JETON": "j", "TWILIO_EMETTEUR": "+237600000000"}
    assert whatsapp_depuis_environnement(base) is None                                   # SMS seulement
    assert whatsapp_depuis_environnement({**base, "TWILIO_CANAL": "whatsapp"}) is None    # pas de modèle
    wa = whatsapp_depuis_environnement({**base, "TWILIO_WHATSAPP_EMETTEUR": "+237611111111",
                                        "TWILIO_WHATSAPP_MODELE": "HX1"})
    assert wa.modele == "HX1" and wa.expediteur.emetteur == "whatsapp:+237611111111"


def test_twilio_recoit_le_modele_et_ses_variables(monkeypatch):
    vu = {}

    def poster(url, data, auth, timeout):
        vu.update(url=url, data=data)
        return httpx.Response(201)
    monkeypatch.setattr(httpx, "post", poster)
    WhatsAppAvis(ExpediteurTwilio("AC1", "j", "whatsapp:+2376", "whatsapp"), "HX1").envoyer(
        "+237690000011", "Un message vous attend", "https://x.cm/dossier/1")
    assert vu["data"]["ContentSid"] == "HX1" and vu["data"]["To"] == "whatsapp:+237690000011"
    assert vu["data"]["ContentVariables"] == '{"1": "Un message vous attend", "2": "https://x.cm/dossier/1"}'
    assert "Body" not in vu["data"]


def test_le_sujet_est_rempli_avant_de_partir(bases, azito):
    """« Rappel : {etape} » partait tel quel : le sujet n'était pas rempli (le corps l'était)."""
    from sqlalchemy.orm import Session

    from courtage.services import avis
    wa = WhatsAppAvis(ExpediteurJournal(), "HX_modele")
    numero(bases, azito["drh"])
    with bases[0].begin() as c:
        c.execute(text("UPDATE utilisateurs SET avis_whatsapp = true WHERE id = :i"), {"i": azito["drh"]})
    with Session(bases[1]) as session:
        session.info.update(courriel=None, whatsapp=wa, url_publique="https://x.cm")
        with session.begin():
            avis.prevoir(session, "rappel_annuel", [azito["drh"]], auteur=None, org=azito["org"], entreprise="AZITO",
                         etape="Relevé du personnel", quand="est attendu", echeance="30/11/2026", lien="annee")
    [m] = wa.expediteur.envoyes
    assert m.texte == f"Rappel : Relevé du personnel — https://x.cm/dossier/{azito['org']}/annee"
