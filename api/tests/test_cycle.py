"""Le cycle de vie d'un dossier : suspendre, clôturer, reprendre, archiver, supprimer (vide seulement)."""
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from courtage.services.cycle import archiver_echus_partout
from tests.outils import V1, deposer, en_tant_que, etude, fichier_azito


def changer(client, a, action, qui="conseiller", **corps):
    return client.post(f"{V1}/organisations/{a['org']}/cycle", json={"action": action, **corps},
                       headers=en_tant_que(a[qui]))


def test_le_conseiller_seul_change_l_etat_et_toujours_avec_un_motif(client, azito):
    assert changer(client, azito, "suspendre", qui="drh", motif_code="impaye").status_code == 403
    r = changer(client, azito, "suspendre")
    assert r.status_code == 422 and r.json()["code"] == "motif_requis"
    assert changer(client, azito, "suspendre", motif_code="autre").json()["code"] == "motif_requis"
    r = changer(client, azito, "suspendre", motif_code="impaye", motif="Honoraires 2025 impayés")
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["etat"] == "suspendu" and set(c["actions"]) == {"cloturer", "reprendre", "supprimer"}
    assert c["historique"][0]["motif_libelle"] == "Impayé" and c["historique"][0]["par"] == "Conseiller"
    # La DRH lit l'état ; « reprendre » demande une raison, écrite.
    assert client.get(f"{V1}/organisations/{azito['org']}/cycle", headers=en_tant_que(azito["drh"])).json()["etat"] == "suspendu"
    assert changer(client, azito, "reprendre").json()["code"] == "motif_requis"
    assert changer(client, azito, "reprendre", motif="Réglé le 12/10").json()["etat"] == "ouvert"
    assert changer(client, azito, "reprendre", motif="encore").json()["code"] == "transition_impossible"


def test_suspendu_tout_se_lit_rien_ne_s_emet(client, azito):
    e = etude(client, azito).json()
    changer(client, azito, "suspendre", motif_code="litige")
    h = en_tant_que(azito["conseiller"])
    assert client.get(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}", headers=h).status_code == 200
    r = client.post(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/emission", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "dossier_suspendu"
    # Préparer reste possible : un brouillon n'engage rien.
    assert etude(client, azito).status_code == 201
    alertes = client.get(f"{V1}/organisations/{azito['org']}/alertes", headers=h).json()
    assert alertes[0]["code"] == "dossier_suspendu" and "Litige" in alertes[0]["detail"]


def test_cloture_lecture_seule_mais_les_calculs_et_la_reprise_passent(client, azito):
    e = etude(client, azito).json()
    assert changer(client, azito, "cloturer", motif_code="changement_courtier").json()["etat"] == "cloture"
    h = en_tant_que(azito["drh"])
    r = client.post(f"{V1}/organisations/{azito['org']}/fichiers", headers=h,
                    files={"fichier": ("p.xlsx", fichier_azito(), "application/octet-stream")},
                    data={"date_donnees": "2019-12-31"})
    assert r.status_code == 409 and r.json()["code"] == "dossier_cloture"
    assert etude(client, azito).json()["code"] == "dossier_cloture"
    assert client.get(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/export", headers=h).status_code == 200
    r = client.post(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/financement", headers=h,
                    json={"horizon": 5, "amortissement_annees": 1, "offres": []})
    assert r.status_code == 200, r.text
    c = client.get(f"{V1}/organisations/{azito['org']}/cycle", headers=h).json()
    assert c["archivage_prevu"] == (date.today() + timedelta(days=90)).isoformat()
    [alerte] = client.get(f"{V1}/organisations/{azito['org']}/alertes", headers=h).json()
    assert alerte["code"] == "archivage_prevu"
    assert changer(client, azito, "reprendre", motif="Le client revient").json()["etat"] == "ouvert"
    assert etude(client, azito).status_code == 201


def test_seul_un_dossier_vide_se_supprime(client, azito, personnes):
    r = changer(client, azito, "supprimer", motif_code="ouvert_par_erreur")
    assert r.status_code == 409 and r.json()["code"] == "dossier_non_vide"
    admin = en_tant_que(personnes["admin"])
    org = client.post(f"{V1}/organisations", json={"nom": "Doublon SA", "pays": "CM", "suivre": True}, headers=admin).json()["id"]
    c = client.get(f"{V1}/organisations/{org}/cycle", headers=admin).json()
    assert c["supprimable"] is True
    r = client.post(f"{V1}/organisations/{org}/cycle", headers=admin, json={"action": "supprimer", "motif_code": "doublon"})
    assert r.status_code == 200 and r.json() == {"etat": "supprime"}
    assert org not in {d["id"] for d in client.get(f"{V1}/moi", headers=admin).json()["organisations"]}
    assert client.get(f"{V1}/organisations/{org}/cycle", headers=admin).status_code == 403   # plus membre


def test_l_archivage_vide_le_personnel_garde_les_documents_et_ferme_le_dossier(client, azito, bases):
    e = etude(client, azito).json()
    r = client.post(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/emission", headers=en_tant_que(azito["conseiller"]))
    numero = r.json()["rapport"]["numero"]
    changer(client, azito, "cloturer", motif_code="fin_mandat")
    proprio, app = bases
    assert archiver_echus_partout(app, date.today()) == 0                 # le délai court encore
    with proprio.begin() as c:
        c.execute(text("UPDATE organisations SET etat_depuis = now() - interval '91 days' WHERE id = :o"), {"o": azito["org"]})
    assert archiver_echus_partout(app, date.today()) == 1
    with proprio.connect() as c:
        lignes, vide_le = c.execute(text("SELECT lignes, vide_le FROM fichiers_personnel WHERE id = :f"),
                                    {"f": azito["fichier"]}).one()
        etat = c.execute(text("SELECT etat FROM organisations WHERE id = :o"), {"o": azito["org"]}).scalar()
    assert lignes == [] and vide_le is not None and etat == "archive"
    h = en_tant_que(azito["drh"])
    r = client.get(f"{V1}/organisations/{azito['org']}/etudes", headers=h)
    assert r.status_code == 410 and r.json()["code"] == "dossier_archive"
    assert azito["org"] not in {d["id"] for d in client.get(f"{V1}/moi", headers=h).json()["organisations"]}
    assert client.get(f"{V1}/verifier/{numero}").json()["authentique"] is True    # le document se vérifie toujours


def test_un_fichier_ne_peut_qu_etre_vide_une_fois(bases, azito):
    _, app = bases
    with app.begin() as c:
        c.execute(text("SELECT set_config('app.organisation_id', :o, true)"), {"o": azito["org"]})
        # Deux verrous : les droits (seules trois colonnes se modifient), puis le déclencheur (seulement pour vider).
        with pytest.raises(DBAPIError, match="permission denied"):
            with c.begin_nested():
                c.execute(text("UPDATE fichiers_personnel SET nom_fichier = 'x'"))
        with pytest.raises(DBAPIError, match="fichier_personnel_immuable"):
            with c.begin_nested():
                c.execute(text("UPDATE fichiers_personnel SET lignes = '[{\"a\": 1}]', vide_le = now()"))
        c.execute(text("UPDATE fichiers_personnel SET lignes = '[]', anomalies = '[]', vide_le = now()"))
        with pytest.raises(DBAPIError, match="fichier_personnel_immuable"):
            with c.begin_nested():
                c.execute(text("UPDATE fichiers_personnel SET lignes = '[]', anomalies = '[]', vide_le = now()"))
