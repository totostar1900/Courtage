"""Jeu de démonstration : `python -m courtage.demo <url propriétaire>`.

Crée trois personnes (une administratrice de plateforme, une conseillère, une
DRH ; téléphones +237 690 00 00 03, 02 et 01, pour se connecter par code), le
client AZITO avec ses conditions de rémunération, et dépose le fichier du
personnel d'AZITO (23 salariés, sans nom) comme la DRH l'aurait fait. Imprime
les identifiants. Tout passe par l'API sauf la création des trois personnes.

Les données du fichier viennent du cas de test AZITO : dépôt privé seulement. Là où
le cas n'est pas (l'image Docker ne porte pas les tests), le jeu sème à la place
« Société Démo SA » et 40 salariés inventés : une recette n'a jamais de données réelles.
"""
import io
import json
import sys
import uuid
from datetime import datetime
from importlib.resources import files
from pathlib import Path

import random
from datetime import date, timedelta
from io import BytesIO

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
    reel = _FIXTURE.is_file()
    fiche = ({"nom": "AZITO (démonstration)", "pays": "CI", "secteur": "Énergie"} if reel
             else {"nom": "Société Démo SA", "pays": "CM", "secteur": "Commerce"})
    org = client.post(f"{V1}/organisations", json=fiche, headers=h("admin")).json()["id"]
    for qui, role in (("conseiller", "conseiller"), ("drh", "admin_client")):
        client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": str(ids[qui]), "role": role},
                    headers=h("admin"))
    r = client.post(f"{V1}/organisations/{org}/fichiers", headers=h("drh"),
                    files={"fichier": ("azito-personnel-2019.xlsx", _fichier())} if reel
                    else {"fichier": ("personnel-2025.xlsx", personnel_fictif())},
                    data={"date_donnees": "2019-12-31" if reel else "2025-12-31"})
    r.raise_for_status()
    ids["organisation"] = uuid.UUID(org)
    return ids


NOM_DEMO = "Société Démo SA"


def societe_demo(client, h) -> dict:
    """Le dossier fictif de la démonstration, rempli par l'API elle-même : 40 salariés inventés, un accord
    plus favorable pour les cadres (adopté) et un projet d'avenant, des départs passés, un dossier de prise
    en charge transmis, une étude émise et un brouillon, un cahier des charges et trois réponses d'assureurs
    FICTIFS. `h(qui)` rend les en-têtes de « admin », « conseiller » ou « drh ». Sert à la démonstration
    statique (scripts/capturer_demo.py) et au site en ligne (`--depuis-env`)."""
    def ok(r):
        assert r.status_code < 300, r.text
        return r.json() if r.content and r.headers.get("content-type", "").startswith("application/json") else r

    ids = {"conseiller": h("conseiller")["X-Utilisateur"], "drh": h("drh")["X-Utilisateur"]}
    org = ok(client.post(f"{V1}/organisations", json={"nom": NOM_DEMO, "pays": "CM", "secteur": "Commerce"},
                         headers=h("admin")))["id"]
    for qui, role in (("conseiller", "conseiller"), ("drh", "admin_client")):
        ok(client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": ids[qui], "role": role},
                       headers=h("admin")))
    # Avant le mandat de 2025, le dossier était sans mandat : les départs d'avant relèvent de l'entreprise seule.
    ok(client.post(f"{V1}/organisations/{org}/contrats", headers=h("conseiller"), json={
        "en_vigueur_du": "2025-01-01", "service": "courtage", "assureur": "Assureur A (fictif)",
        "numero_police": "IFC-2025-0042", "date_effet_police": "2025-01-01",
        "mandat_reference": "Mandat de courtage du 12/12/2024"}))
    fichier = ok(client.post(f"{V1}/organisations/{org}/fichiers", headers=h("drh"),
                             files={"fichier": ("personnel-2025.xlsx", personnel_fictif())},
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

    # Trois assureurs FICTIFS répondent le jour même : le moins cher impose une pénalité de transfert (non
    # conforme), le recommandé est conforme, le troisième est conforme et plus cher.
    for assureur, tg, pb, fc, fe, penalite, recue in (
            ("Assureur C (fictif)", 0.025, 0.85, 0.0, 0.0, 0.05, 0),
            ("Assureur A (fictif)", 0.03, 0.9, 0.02, 0.004, 0.0, 0)):
        ok(client.post(f"{V1}/organisations/{org}/fiches/{fiche['id']}/reponses", headers=h("conseiller"), data={
            "donnees": json.dumps({"assureur": assureur, "recue_le": (date.today() + timedelta(days=recue)).isoformat(),
                                   "taux_garanti": tg, "participation_benefices": pb, "frais_sur_cotisations": fc,
                                   "frais_sur_encours": fe, "delai_paiement_jours": 25, "transfert_preavis_mois": 3,
                                   "transfert_penalite": penalite, "accepte_etude_plateforme": True,
                                   "reporting_annuel": True})}))

    _consultations(client, h, ok, org, fiche)
    _placement(client, h, ok, org)
    return {"org": org, "fichier": fichier, "version": version, "projet": projet, "dossier": dossier,
            "etude": etude, "brouillon": brouillon, "fiche": fiche}


def _consultations(client, h, ok, org: str, fiche: dict) -> None:
    """Deux assureurs FICTIFS consultés depuis la plateforme : D ouvre son lien et dépose son offre lui-même (conforme,
    plus chère) ; B n'a pas encore ouvert le sien."""
    import re
    for nom, courriel in (("Assureur D (fictif)", "offres@assureur-d.demo"), ("Assureur B (fictif)", "devis@assureur-b.demo")):
        ok(client.post(f"{V1}/organisations/{org}/fiches/{fiche['id']}/consultations", headers=h("conseiller"),
                       json={"assureur": nom, "contact_nom": "Service entreprises (fictif)", "contact_courriel": courriel}))
    dernier = [m for m in client.app.state.courriel.envoyes if m.telephone == "offres@assureur-d.demo"][-1]
    jeton = re.search(r"/offre/([A-Za-z0-9_\-]+)", dernier.texte).group(1)
    ok(client.get(f"{V1}/offre/{jeton}"))
    ok(client.post(f"{V1}/offre/{jeton}", files={"offre": ("offre-assureur-d.pdf", b"%PDF-1.4\n% offre fictive\n%%EOF")},
                   data={"donnees": json.dumps({"taux_garanti": 0.025, "participation_benefices": 0.85,
                                                "frais_sur_cotisations": 0.03, "frais_sur_encours": 0.005,
                                                "delai_paiement_jours": 25, "transfert_preavis_mois": 3,
                                                "transfert_penalite": 0.0, "accepte_etude_plateforme": True,
                                                "reporting_annuel": True})}))


def _placement(client, h, ok, org: str) -> None:
    """La police en cours chez l'assureur fictif : reçue, signée, première prime virée puis encaissée sur quittance,
    un relevé ; et un appel de 2026 dont le compte n'est PAS celui du registre — « Ne pas payer » jusqu'au
    contre-appel du conseiller. Tout est fictif, y compris les coordonnées bancaires."""
    pdf = ("document-fictif.pdf", b"%PDF-1.4\n% document fictif de demonstration\n%%EOF", "application/pdf")
    client.post(f"{V1}/assureurs/comptes", headers=h("admin"), json={
        "assureur": "Assureur A (fictif)", "banque": "Banque fictive du Littoral", "titulaire": "Assureur A (fictif) SA",
        "iban": "CM00 00000 00000 0000000000 01", "verifie_aupres": "Service financier (fictif)",
        "verifie_telephone": "+237 600 00 00 00", "verifie_le": "2024-12-15"})
    base = f"{V1}/organisations/{org}"
    p = ok(client.post(f"{base}/polices", headers=h("conseiller"), json={
        "assureur": "Assureur A (fictif)", "numero_police": "IFC-2025-0042", "date_effet": "2025-01-01",
        "periodicite": "annuelle"}))
    ok(client.post(f"{base}/polices/{p['id']}/pieces", headers=h("conseiller"), data={"nature": "police"}, files={"fichier": pdf}))
    ok(client.post(f"{base}/polices/{p['id']}/signature", headers=h("drh"), json={"signee_le": "2024-12-20"}))
    a = ok(client.post(f"{base}/polices/{p['id']}/appels", headers=h("conseiller"), json={
        "reference": "AP-2025-01", "montant": 18_500_000, "echeance": "2025-01-31", "premiere": True,
        "banque": "Banque fictive du Littoral", "titulaire": "Assureur A (fictif) SA",
        "iban": "CM00 00000 00000 0000000000 01"}))
    ok(client.post(f"{base}/appels/{a['id']}/virement", headers=h("drh"), json={
        "vire_le": "2025-01-24", "montant": 18_500_000, "reference": "VIR-2025-0124"}))
    ok(client.post(f"{base}/polices/{p['id']}/pieces", headers=h("conseiller"), data={"nature": "quittance", "appel_id": a["id"]},
                   files={"fichier": pdf}))
    ok(client.post(f"{base}/appels/{a['id']}/encaissement", headers=h("conseiller"), json={"encaisse_le": "2025-01-29"}))
    ok(client.post(f"{base}/polices/{p['id']}/pieces", headers=h("conseiller"), files={"fichier": pdf},
                   data={"nature": "releve", "releve_le": "2025-12-31", "montant_fonds": "19240000"}))
    ok(client.post(f"{base}/polices/{p['id']}/appels", headers=h("conseiller"), json={
        "reference": "AP-2026-01", "montant": 19_800_000, "echeance": (date.today() + timedelta(days=21)).isoformat(),
        "banque": "Autre banque (fictive)", "titulaire": "Assureur A (fictif) SA",
        "iban": "CM00 99999 00000 0000000000 99"}))


def personnel_fictif(n: int = 40, graine: int = 2026) -> bytes:
    """Un personnel inventé (tirage fixe) : 8 cadres, 32 employés, dates et salaires tirés au sort."""
    hasard = random.Random(graine)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Société Démo SA — état du personnel au 31/12/2025"])
    ws.append([])
    ws.append(["Matricule", "Nom", "Date de naissance", "Date d'embauche", "Salaire brut mensuel", "Catégorie"])
    for i in range(n):
        cadre = i < 8
        naissance = date(1964, 1, 1) + timedelta(days=hasard.randint(0, 365 * 32))
        embauche_min = naissance.replace(year=naissance.year + 21)
        embauche = embauche_min + timedelta(days=hasard.randint(0, max((date(2025, 6, 30) - embauche_min).days, 1)))
        salaire = hasard.randint(900, 2600) * 1000 if cadre else hasard.randint(160, 620) * 1000
        ws.append([f"D{i + 1:03d}", "Nom fictif", naissance, embauche, salaire, "Cadre" if cadre else "Employé"])
    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


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


# La version de la démonstration : à monter quand le code sait montrer ce que les études déjà semées ne
# portent pas (elles sont figées). v2 : l'échéancier découpé par catégorie (26/09/2026). v3 : le placement — une police,
# ses primes, un appel aux coordonnées à confirmer (29/09/2026). v4 : deux assureurs consultés par lien, dont un
# qui dépose son offre lui-même (29/09/2026).
VERSION_DEMO = 4


def depuis_environnement(env, version: int = VERSION_DEMO) -> str | None:
    """`COURTAGE_DEMO=1` : sème la Société Démo SA au démarrage, une fois par version, et en fait suivre le
    dossier par les administrateurs de la plateforme. Une version plus récente sème un dossier neuf et retire
    l'ancien de leur liste (rien n'est effacé : le journal et les études restent). Jamais en production."""
    if (env.get("COURTAGE_DEMO") or "").strip().lower() not in ("1", "oui", "true"):
        return None
    if env.get("COURTAGE_ENV") == "production":
        return "démonstration refusée en production (retirer COURTAGE_DEMO)"
    from courtage.deploiement import _psycopg, url_applicative
    proprio = create_engine(_psycopg(env["COURTAGE_URL_PROPRIETAIRE"]))
    ids = {}
    with proprio.begin() as c:
        # La première démonstration a laissé une marque sans version : elle compte pour la version 1.
        en_place = c.execute(text("SELECT max(coalesce((details->>'version')::int, 1)) FROM journal "
                                  "WHERE action = 'demo.semee'")).scalar()
        if en_place is not None and en_place >= version:
            return f"{NOM_DEMO} déjà semée (version {en_place})"
        anciennes = [str(i) for i in c.execute(text("SELECT id FROM organisations WHERE nom = :n"), {"n": NOM_DEMO}).scalars()]
        # La marque d'abord : si la suite échoue, le redémarrage ne sème pas un second dossier.
        c.execute(text("INSERT INTO journal (action, cible, details) VALUES ('demo.semee', 'plateforme', "
                       "jsonb_build_object('version', CAST(:v AS int)))"), {"v": version})
        admins = [str(i) for i in c.execute(text(
            "SELECT id FROM utilisateurs WHERE admin_plateforme AND coalesce(email, '') NOT LIKE '%@demo.courtage' "
            "ORDER BY cree_le")).scalars()]
        suffixe = uuid.uuid4().hex[:6]
        for cle, nom, admin in (("admin", "Plateforme (démonstration)", True),
                                ("conseiller", "Awa Nkoulou, actuaire conseil (fictive)", False),
                                ("drh", "Direction RH, Société Démo (fictive)", False)):
            # Des personnes sans téléphone : personne ne se connecte sous leur nom.
            ids[cle] = str(c.execute(text("INSERT INTO utilisateurs (email, nom_affiche, admin_plateforme) "
                                          "VALUES (:e, :n, :a) RETURNING id"),
                                     {"e": f"{cle}-{suffixe}@demo.courtage", "n": nom, "a": admin}).scalar_one())
    cle_sceau = env.get("COURTAGE_CLE_SCEAU")
    client = TestClient(creer_app(moteur=create_engine(url_applicative(env)), authentification="entete_dev",
                                  cle_sceau=cle_sceau.encode("utf-8") if cle_sceau else None,
                                  url_publique=env.get("COURTAGE_URL_PUBLIQUE") or env.get("RENDER_EXTERNAL_URL")))
    h = lambda qui: {"X-Utilisateur": ids.get(qui, qui)}  # noqa: E731
    org = societe_demo(client, h)["org"]
    for admin in admins:
        r = client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": admin, "role": "conseiller"},
                        headers=h("admin"))
        assert r.status_code == 201, r.text
    if anciennes:
        # L'ancienne démonstration sort de la liste des administrateurs ; son dossier reste, intact.
        with proprio.begin() as c:
            c.execute(text("DELETE FROM adhesions WHERE organisation_id = ANY(CAST(:o AS uuid[])) "
                           "AND utilisateur_id = ANY(CAST(:u AS uuid[]))"), {"o": anciennes, "u": admins})
            c.execute(text("INSERT INTO journal (action, cible, details) VALUES ('demo.remplacee', :n, "
                           "jsonb_build_object('anciennes', CAST(:a AS jsonb)))"), {"n": org, "a": json.dumps(anciennes)})
    return (f"{NOM_DEMO} semée ({org}, version {version}), suivie par {len(admins)} administrateur(s)"
            + (f" ; {len(anciennes)} ancienne(s) retirée(s) de leur liste" if anciennes else ""))


if __name__ == "__main__":
    if sys.argv[1:] == ["--depuis-env"]:
        import os
        try:
            message = depuis_environnement(os.environ)
        except Exception as erreur:  # la démonstration ne doit jamais empêcher le site de démarrer
            message = f"échec du semis : {erreur!r}"
        if message:
            print(f"[demo] {message}")
        sys.exit(0)
    url = sys.argv[1]
    url_app = sys.argv[2] if len(sys.argv) > 2 else None
    ids = semer(create_engine(url), create_engine(url_app) if url_app else None)
    for cle, valeur in ids.items():
        print(f"{cle:12} {valeur}")
