"""Jeu de démonstration : `python -m courtage.demo <url propriétaire>`.

Crée trois personnes (une administratrice de plateforme, une conseillère, une
DRH ; téléphones +237 690 00 00 03, 02 et 01, pour se connecter par code), le
client AZITO avec ses conditions de rémunération, et dépose le fichier du
personnel d'AZITO (23 salariés, sans nom) comme la DRH l'aurait fait. Imprime
les identifiants. Tout passe par l'API sauf la création des trois personnes.

Les données du fichier viennent du cas de test AZITO : dépôt privé seulement.
"""
import io
import json
import sys
import uuid
from datetime import datetime
from importlib.resources import files
from pathlib import Path

import openpyxl
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from courtage.api import creer_app

V1 = "/api/v1"
_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "azito_2019.json"


def semer(proprio: Engine, moteur_app: Engine | None = None) -> dict:
    suffixe = uuid.uuid4().hex[:6]
    ids = {}
    with proprio.begin() as c:
        for cle, nom, admin, tel in (("admin", "Admin plateforme", True, "+237690000003"),
                                     ("conseiller", "Awa Nkoulou, actuaire conseil", False, "+237690000002"),
                                     ("drh", "Direction RH AZITO", False, "+237690000001")):
            # Un numéro de démonstration, libéré s'il sert déjà (le jeu peut être semé plusieurs fois).
            c.execute(text("UPDATE utilisateurs SET telephone = NULL WHERE telephone = :t"), {"t": tel})
            ids[cle] = c.execute(text(
                "INSERT INTO utilisateurs (email, telephone, nom_affiche, admin_plateforme) "
                "VALUES (:e, :t, :n, :a) RETURNING id"),
                {"e": f"{cle}-{suffixe}@demo.courtage", "t": tel, "n": nom, "a": admin}).scalar_one()
        moteur_app = moteur_app or proprio

    client = TestClient(creer_app(moteur=moteur_app, authentification="entete_dev"))
    h = lambda qui: {"X-Utilisateur": str(ids[qui])}  # noqa: E731
    org = client.post(f"{V1}/organisations", json={"nom": "AZITO (démonstration)", "pays": "CI", "secteur": "Énergie"},
                      headers=h("admin")).json()["id"]
    for qui, role in (("conseiller", "conseiller"), ("drh", "admin_client")):
        client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": str(ids[qui]), "role": role},
                    headers=h("admin"))
    client.post(f"{V1}/organisations/{org}/remuneration", headers=h("conseiller"), json={
        "en_vigueur_du": "2019-01-01", "mode": "mixte", "honoraires_etude_ifc": 750_000,
        "honoraires_par_salarie": 2_000, "commission_bps": 1000})
    r = client.post(f"{V1}/organisations/{org}/fichiers", headers=h("drh"),
                    files={"fichier": ("azito-personnel-2019.xlsx", _fichier())}, data={"date_donnees": "2019-12-31"})
    r.raise_for_status()
    ids["organisation"] = uuid.UUID(org)
    return ids


def _fichier() -> bytes:
    donnees = json.loads(_FIXTURE.read_text("utf-8"))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["AZITO — état du personnel au 31/12/2019"])
    ws.append([])
    ws.append(["Matricule", "Date de naissance", "Date d'embauche", "Salaire brut annuel"])
    for s in donnees["salaries"]:
        ws.append([s["matricule"], datetime.fromisoformat(s["naissance"]), datetime.fromisoformat(s["embauche"]),
                   s["salaire_annuel"]])
    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


if __name__ == "__main__":
    url = sys.argv[1]
    url_app = sys.argv[2] if len(sys.argv) > 2 else None
    ids = semer(create_engine(url), create_engine(url_app) if url_app else None)
    for cle, valeur in ids.items():
        print(f"{cle:12} {valeur}")
