"""Enregistre les réponses de la VRAIE API sur une entreprise FICTIVE, pour la démonstration statique.

    python scripts/capturer_demo.py <url propriétaire d'une base JETABLE> <dossier de sortie>

La base est remise à zéro (schéma public détruit), migrée, puis remplie par
l'API elle-même : « Société Démo SA », Cameroun, 40 salariés inventés (tirage
fixe), un accord plus favorable pour les cadres, une étude émise, un brouillon,
un cahier des charges. Aucune donnée réelle : le cas AZITO n'est PAS utilisé.

Sortie : `donnees.json` (réponses par « MÉTHODE chemin ») et `documents.json`
(les PDF émis, rendus en images de pages).
"""
import base64
import json
import sys
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import openpyxl

import pymupdf
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from courtage.api import creer_app
from courtage.db.migrations import migrer
from courtage.demo import personnel_fictif as personnel

V1 = "/api/v1"
MOT_DE_PASSE = "demo-statique"


def _pages(pdf: bytes) -> list[str]:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return ["data:image/jpeg;base64," + base64.b64encode(p.get_pixmap(dpi=90).tobytes("jpeg", 80)).decode()
                for p in doc]


def main(url: str, sortie: Path) -> None:
    proprio = create_engine(url)
    with proprio.begin() as c:
        c.execute(text("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"))
        c.execute(text(f"""DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'courtage_app') THEN
              CREATE ROLE courtage_app LOGIN PASSWORD '{MOT_DE_PASSE}';
            ELSE ALTER ROLE courtage_app LOGIN PASSWORD '{MOT_DE_PASSE}'; END IF; END $$;"""))
    migrer(url)
    app = create_engine(make_url(url).set(username="courtage_app", password=MOT_DE_PASSE))
    client = TestClient(creer_app(moteur=app, authentification="entete_dev", url_publique="https://demo.courtage"))

    ids = {}
    with proprio.begin() as c:
        for cle, nom, admin in (("admin", "Plateforme (démo)", True),
                                ("conseiller", "Awa Nkoulou, actuaire conseil", False),
                                ("drh", "Direction RH, Société Démo", False)):
            ids[cle] = str(c.execute(text("INSERT INTO utilisateurs (email, nom_affiche, admin_plateforme) "
                                          "VALUES (:e, :n, :a) RETURNING id"),
                                     {"e": f"{cle}@demo.courtage", "n": nom, "a": admin}).scalar_one())
    h = lambda qui: {"X-Utilisateur": ids[qui]}  # noqa: E731

    def ok(r):
        assert r.status_code < 300, r.text
        return r.json() if r.content and r.headers.get("content-type", "").startswith("application/json") else r

    org = ok(client.post(f"{V1}/organisations", json={"nom": "Société Démo SA", "pays": "CM", "secteur": "Commerce"},
                         headers=h("admin")))["id"]
    for qui, role in (("conseiller", "conseiller"), ("drh", "admin_client")):
        ok(client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": ids[qui], "role": role},
                       headers=h("admin")))
    ok(client.post(f"{V1}/organisations/{org}/remuneration", headers=h("conseiller"), json={
        "en_vigueur_du": "2025-01-01", "mode": "mixte", "honoraires_etude_ifc": 900_000,
        "honoraires_par_salarie": 2_500, "commission_bps": 800}))
    # Avant le mandat, l'entreprise traitait seule avec son assureur : les départs d'avant 2025 relèvent de la comparaison.
    ok(client.post(f"{V1}/organisations/{org}/contrats", headers=h("conseiller"), json={
        "en_vigueur_du": "2020-01-01", "service": "comparaison", "assureur": "Assureur B (fictif)",
        "numero_police": "IFC-B-2020-17", "date_effet_police": "2020-01-01"}))
    ok(client.post(f"{V1}/organisations/{org}/contrats", headers=h("conseiller"), json={
        "en_vigueur_du": "2025-01-01", "service": "courtage", "assureur": "Assureur A (fictif)",
        "numero_police": "IFC-2025-0042", "date_effet_police": "2025-01-01",
        "mandat_reference": "Mandat de courtage du 12/12/2024"}))
    fichier = ok(client.post(f"{V1}/organisations/{org}/fichiers", headers=h("drh"),
                             files={"fichier": ("personnel-2025.xlsx", personnel())},
                             data={"date_donnees": "2025-12-31"}))

    commerce = [{"jusqu_a": 5, "mois_par_annee": 0.45}, {"jusqu_a": 10, "mois_par_annee": 0.50},
                {"jusqu_a": 15, "mois_par_annee": 0.65}, {"jusqu_a": 20, "mois_par_annee": 0.75},
                {"jusqu_a": None, "mois_par_annee": 0.80}]
    cadres = [{"jusqu_a": 5, "mois_par_annee": 0.60}, {"jusqu_a": 10, "mois_par_annee": 0.70},
              {"jusqu_a": 15, "mois_par_annee": 0.85}, {"jusqu_a": 20, "mois_par_annee": 1.00},
              {"jusqu_a": None, "mois_par_annee": 1.10}]
    regime = ok(client.post(f"{V1}/organisations/{org}/regimes", json={"nom": "Accord IFC Société Démo"}, headers=h("drh")))
    version = ok(client.post(f"{V1}/organisations/{org}/regimes/{regime['id']}/versions", headers=h("drh"), json={
        "en_vigueur_du": "2024-02-01", "fondement": "accord_entreprise",
        "document_reference": "Accord d'entreprise du 01/02/2024, article 9",
        "categories": [
            {"categorie": "Cadre", "convention_code": "CM_COMMERCE", "bareme": {"forme": "tranches_cumulatives", "tranches": cadres}},
            {"categorie": "*", "convention_code": "CM_COMMERCE", "bareme": {"forme": "tranches_cumulatives", "tranches": commerce},
             "base_salaire": "moyenne_12_mois"}]}))
    ok(client.post(f"{V1}/organisations/{org}/regimes/versions/{version['id']}/adoption", headers=h("drh"),
                   json={"accepte_non_conformite": False}))
    projet = ok(client.post(f"{V1}/organisations/{org}/regimes/{regime['id']}/versions", headers=h("conseiller"), json={
        "en_vigueur_du": "2026-07-01", "fondement": "accord_entreprise",
        "document_reference": "Projet d'avenant 2026 (en discussion)",
        "categories": [
            {"categorie": "Cadre", "convention_code": "CM_COMMERCE", "bareme": {"forme": "tranches_cumulatives", "tranches": [
                {"jusqu_a": None, "mois_par_annee": 1.5}]}},
            {"categorie": "*", "convention_code": "CM_COMMERCE", "bareme": {"forme": "tranches_cumulatives", "tranches": [
                {"jusqu_a": None, "mois_par_annee": 0.40}]}}]}))

    # Des départs passés, repris par tableur (inventés, comme le personnel).
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Matricule", "Date d'embauche", "Date de départ", "Motif", "Salaire mensuel de référence",
               "Montant versé", "Payé par le fonds", "Date de paiement"])
    for ligne in (("X101", date(1990, 3, 1), date(2021, 6, 30), "Retraite", 410_000, 7_700_000, 7_500_000, date(2021, 8, 20)),
                  ("X102", date(2012, 1, 1), date(2022, 2, 28), "Démission", 280_000, None, None, None),
                  ("X103", date(1994, 9, 1), date(2023, 12, 31), "Retraite", 520_000, 9_000_000, 8_970_000, date(2024, 2, 10)),
                  ("X104", date(2016, 4, 1), date(2024, 5, 31), "Licenciement", 350_000, None, None, None),
                  ("X105", date(1992, 1, 1), date(2025, 3, 31), "Retraite", 780_000, 10_500_000, None, None)):
        ws.append(list(ligne))
    tampon = BytesIO()
    wb.save(tampon)
    ok(client.post(f"{V1}/organisations/{org}/prestations/import", headers=h("conseiller"),
                   files={"fichier": ("departs-2021-2025.xlsx", tampon.getvalue())},
                   data={"convention_code": "CM_COMMERCE", "enregistrer": "true"}))
    # En courtage : un dossier de prise en charge, bénéficiaire FICTIF, vérifié et transmis à l'assureur.
    x105 = next(p for p in ok(client.get(f"{V1}/organisations/{org}/prestations", headers=h("drh")))["prestations"]
                if p["matricule"] == "X105")
    dossier = ok(client.post(f"{V1}/organisations/{org}/dossiers", headers=h("drh"), json={
        "prestation_id": x105["id"], "montant_demande": 10_500_000, "beneficiaire": {
            "qualite": "salarie", "nom": "FICTIF", "prenoms": "Bénéficiaire de démonstration", "piece_type": "cni",
            "piece_numero": "000000000", "moyen_paiement": "virement", "coordonnees_paiement": "CM00 0000 0000 0000"}}))
    ok(client.post(f"{V1}/organisations/{org}/dossiers/{dossier['id']}/verification", headers=h("conseiller"),
                   json={"conforme": True}))
    ok(client.post(f"{V1}/organisations/{org}/dossiers/{dossier['id']}/transmission", headers=h("conseiller"),
                   json={}))
    etude = ok(client.post(f"{V1}/organisations/{org}/etudes", headers=h("drh"), json={
        "fichier_id": fichier["id"], "date_evaluation": "2025-12-31", "regime_version_id": version["id"],
        "fonds_disponible": 45_000_000}))
    ok(client.post(f"{V1}/organisations/{org}/etudes/{etude['id']}/emission", headers=h("conseiller")))
    brouillon = ok(client.post(f"{V1}/organisations/{org}/etudes", headers=h("drh"), json={
        "fichier_id": fichier["id"], "date_evaluation": "2025-12-31", "convention_code": "CM_COMMERCE",
        "fonds_disponible": 45_000_000}))
    fiche = ok(client.post(f"{V1}/organisations/{org}/fiches", headers=h("conseiller"), json={
        "etude_id": etude["id"], "date_limite_reponse": (date.today() + timedelta(days=30)).isoformat(),
        "conditions": {"taux_garanti_minimum": 0.025, "participation_benefices_minimum": 0.85,
                       "frais_sur_cotisations_maximum": 0.03, "frais_sur_encours_maximum": 0.005,
                       "transfert_preavis_mois_maximum": 3, "transfert_penalite_maximum": 0.0,
                       "delai_paiement_jours_maximum": 30}}))

    reponses: dict[str, object] = {}

    def capter(chemin: str, qui="drh", methode="GET", corps=None, cle=None):
        r = client.request(methode, f"{V1}{chemin}", headers=h(qui), json=corps)
        assert r.status_code < 300, (chemin, r.text)
        reponses[cle or f"{methode} {chemin}"] = r.json()

    capter("/referentiel/conventions")
    capter("/dev/utilisateurs")
    reponses["GET /dev/utilisateurs"] = [u for u in reponses["GET /dev/utilisateurs"] if not u["admin_plateforme"]]
    for qui in ("drh", "conseiller"):
        capter("/moi", qui=qui, cle=f"GET /moi@{ids[qui]}")
    base = f"/organisations/{org}"
    for chemin in ("/fichiers", "/regimes", "/etudes", "/fiches", "/equipe", "/remuneration", "/contrats", "/prestations", "/dossiers", f"/dossiers/{dossier['id']}",
                   f"/etudes/{etude['id']}", f"/etudes/{brouillon['id']}", f"/fiches/{fiche['id']}"):
        capter(base + chemin)
    for v in (version["id"], projet["id"]):
        capter(f"{base}/regimes/versions/{v}/analyse")
        capter(f"{base}/regimes/versions/{v}/analyse?fichier_id={fichier['id']}")
    capter(f"{base}/simulations", methode="POST", cle=f"POST {base}/simulations", corps={
        "fichier_id": fichier["id"], "date_evaluation": "2025-12-31", "convention_code": "CM_COMMERCE",
        "fonds_disponible": 45_000_000, "variantes": [
            {"nom": "Accord IFC Société Démo, version 1", "regime_version_id": version["id"]},
            {"nom": "Accord IFC Société Démo, version 2", "regime_version_id": projet["id"]}]})
    # La référence du calcul de financement, pour vérifier la version TypeScript.
    capter(f"{base}/etudes/{etude['id']}/financement", methode="POST", cle="REFERENCE financement", corps={
        "horizon": 10, "amortissement_annees": 3, "offres": [
            {"nom": "Assureur A", "taux_garanti": 0.025, "participation_benefices": 0.85, "frais_sur_cotisations": 0.04},
            {"nom": "Assureur B", "taux_garanti": 0.02, "participation_benefices": 0.9, "frais_sur_cotisations": 0.02,
             "frais_sur_encours": 0.005}]})

    # L'orientation (comparaison) et la fiche de calcul scellée de chaque départ en retraite d'avant le mandat.
    fiches_de_calcul = []
    for p in reponses[f"GET {base}/prestations"]["prestations"]:
        if p["motif"] == "retraite" and p["service"] == "comparaison":
            capter(f"{base}/prestations/{p['id']}/orientation")
            fiches_de_calcul.append(f"{base}/prestations/{p['id']}/fiche-de-calcul")
    documents = {}
    rapport = reponses[f"GET {base}/etudes/{etude['id']}"]["rapport"]["numero"]
    for numero, chemin in ((rapport, f"{base}/etudes/{etude['id']}/rapport"),
                           (fiche["numero"], f"{base}/fiches/{fiche['id']}/document"),
                           (reponses[f"GET {base}/dossiers/{dossier['id']}"]["numero"],
                            f"{base}/dossiers/{dossier['id']}/document")):
        capter(f"/verifier/{numero}")
        pdf = client.get(f"{V1}{chemin}", headers=h("drh")).content
        documents[chemin] = _pages(pdf)
    for chemin in fiches_de_calcul:
        r = client.get(f"{V1}{chemin}", headers=h("drh"))
        documents[chemin] = _pages(r.content)
        capter(f"/verifier/{r.headers['x-numero-document']}")

    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "donnees.json").write_text(json.dumps({"organisation": org, "reponses": reponses}, ensure_ascii=False), "utf-8")
    (sortie / "documents.json").write_text(json.dumps(documents), "utf-8")
    print(f"{len(reponses)} réponses, {sum(len(v) for v in documents.values())} pages -> {sortie}")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
