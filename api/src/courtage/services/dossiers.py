"""Courtage : le dossier de prise en charge (spec prestations §3).

La plateforme, mandatée, demande à l'assureur de payer une prestation. Le
dossier passe par des étapes, chacune une ligne :

    déclaré (DRH) ─▶ vérifié (conseiller) ─▶ transmis ─▶ payé | refusé ─▶ transmis…
          └─▶ à compléter ─▶ resoumis (DRH) ─▶ vérifié…

L'identité du bénéficiaire n'est recueillie QUE si le service en vigueur au jour
du départ est le courtage ; elle vit dans `beneficiaires`, les pièces et le PDF
transmis dans `pieces_dossier`, et tout cela est effacé douze mois après le
paiement. Le sceau du PDF est public et ne porte aucune identité : le numéro
PC-… se vérifie encore après l'effacement.

La plateforme ne transmet rien par elle-même et ne touche jamais l'argent :
« transmis » est la date à laquelle le conseiller a envoyé le PDF scellé, « payé »
le paiement constaté, qui s'écrit alors sur la prestation.
"""
import hashlib
import json
import uuid
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import delete, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from courtage.db import (Beneficiaire, Contrat, DossierPriseEnCharge, EvenementDossier, FicheRegime, Organisation,
                         PieceDossier, Prestation, Utilisateur, contexte)
from courtage.erreurs import ErreurMetier, Introuvable

from . import contrats, journaliser, prestations, rapport

CONSERVATION = relativedelta(months=12)
DELAI_PAR_DEFAUT = 30
TAILLE_MAX = 5 * 1024 * 1024
NATURES = {"certificat_travail": "Certificat de travail", "attestation_depart": "Attestation de départ",
           "calcul_signe": "Calcul de l'indemnité signé", "piece_identite": "Pièce d'identité",
           "rib": "Relevé d'identité bancaire", "autre": "Autre pièce"}
_TYPES = ((b"%PDF", "application/pdf"), (b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG", "image/png"))
# Étape courante → étapes permises ensuite.
_SUITES = {"declare": {"verifie", "a_completer"}, "resoumis": {"verifie", "a_completer"},
           "a_completer": {"resoumis"}, "verifie": {"transmis"}, "transmis": {"paye", "refuse"},
           "refuse": {"transmis"}, "paye": set()}


# --- Ouvrir -----------------------------------------------------------------------------

def ouvrir(session: Session, org: Organisation, auteur: uuid.UUID, *, prestation_id: uuid.UUID,
           montant_demande: int, beneficiaire: dict, aujourd_hui: date) -> DossierPriseEnCharge:
    p = session.get(Prestation, prestation_id)
    if p is None or p.annulation:
        raise Introuvable("Prestation")
    prestations._active(session, p.id)
    service = contrats.service_a_la_date(session, p.date_depart)
    if service.service != "courtage":
        assureur = f" ({service.contrat.assureur})" if service.contrat and service.contrat.assureur else ""
        raise ErreurMetier("pas_de_mandat", "Au jour de ce départ, la plateforme n'était pas mandatée : la prise en "
                           f"charge se demande directement à votre assureur{assureur}. Aucune identité n'est "
                           "recueillie ici.", 409)
    if p.motif != "retraite":
        raise ErreurMetier("pas_d_ifc", "Seul un départ en retraite ouvre droit à l'IFC.", 409)
    plafond = p.verse if p.verse is not None else p.du
    if montant_demande > plafond:
        raise ErreurMetier("demande_au_dela_du_verse", f"La demande ({montant_demande:,} F) dépasse ce qui a été "
                           f"{'versé' if p.verse is not None else 'dû'} ({plafond:,} F).".replace(",", " "), 422)
    if session.scalar(select(DossierPriseEnCharge.id).where(DossierPriseEnCharge.matricule == p.matricule,
                                                            DossierPriseEnCharge.date_depart == p.date_depart)):
        raise ErreurMetier("dossier_existant", "Un dossier existe déjà pour ce départ.", 409)
    d = DossierPriseEnCharge(organisation_id=org.id, matricule=p.matricule, date_depart=p.date_depart,
                             prestation_id=p.id, contrat_id=service.contrat.id, montant_demande=montant_demande,
                             cree_par=auteur)
    session.add(d)
    session.flush()
    session.add(Beneficiaire(organisation_id=org.id, dossier_id=d.id, **beneficiaire))
    _etape(session, d, "declare", auteur, aujourd_hui)
    journaliser(session, org.id, auteur, "dossier.ouvert", d.id, {"montant_demande": montant_demande})
    return d


# --- Pièces -----------------------------------------------------------------------------

def ajouter_piece(session: Session, org: Organisation, auteur: uuid.UUID, d: DossierPriseEnCharge, *, nature: str,
                  nom_fichier: str, contenu: bytes) -> PieceDossier:
    if nature not in NATURES:
        raise ErreurMetier("nature_inconnue", f"Nature de pièce inconnue : {nature}.", 422)
    if statut(session, d) == "paye" or _efface(session, d):
        raise ErreurMetier("dossier_clos", "Le dossier est payé : il ne reçoit plus de pièce.", 409)
    if len(contenu) > TAILLE_MAX:
        raise ErreurMetier("piece_trop_lourde", "Une pièce pèse 5 Mo au plus.", 422)
    type_contenu = next((t for signature, t in _TYPES if contenu.startswith(signature)), None)
    if type_contenu is None:
        raise ErreurMetier("type_de_piece", "Une pièce est un PDF, un JPEG ou un PNG.", 422)
    piece = PieceDossier(organisation_id=org.id, dossier_id=d.id, nature=nature, nom_fichier=nom_fichier[:200],
                         type_contenu=type_contenu, contenu=contenu, empreinte=hashlib.sha256(contenu).hexdigest(),
                         cree_par=auteur)
    session.add(piece)
    session.flush()
    journaliser(session, org.id, auteur, "dossier.piece_ajoutee", d.id, {"nature": nature})
    return piece


def piece(session: Session, d: DossierPriseEnCharge, piece_id: uuid.UUID) -> PieceDossier:
    p = session.get(PieceDossier, piece_id)
    if p is None or p.dossier_id != d.id:
        raise Introuvable("Pièce")
    return p


def document(session: Session, d: DossierPriseEnCharge) -> PieceDossier:
    p = session.scalars(select(PieceDossier).where(PieceDossier.dossier_id == d.id,
                                                   PieceDossier.nature == "dossier_scelle")
                        .order_by(PieceDossier.cree_le.desc()).limit(1)).first()
    if p is None:
        raise ErreurMetier("document_indisponible", "Le dossier scellé existe une fois transmis, et jusqu'à "
                           "l'effacement de l'identité.", 404)
    return p


# --- Étapes -----------------------------------------------------------------------------

def verifier(session: Session, org: Organisation, auteur: uuid.UUID, d: DossierPriseEnCharge, *, conforme: bool,
             motif: str | None, aujourd_hui: date) -> None:
    if not conforme and not (motif or "").strip():
        raise ErreurMetier("motif_requis", "Dites à l'entreprise ce qui manque.", 422)
    _avancer(session, d, "verifie" if conforme else "a_completer", auteur, aujourd_hui, motif=motif)
    journaliser(session, org.id, auteur, "dossier.verifie" if conforme else "dossier.a_completer", d.id)


def resoumettre(session: Session, org: Organisation, auteur: uuid.UUID, d: DossierPriseEnCharge,
                aujourd_hui: date) -> None:
    _avancer(session, d, "resoumis", auteur, aujourd_hui)
    journaliser(session, org.id, auteur, "dossier.resoumis", d.id)


def transmettre(session: Session, org: Organisation, auteur: uuid.UUID, d: DossierPriseEnCharge, *, le: date,
                config: rapport.ConfigSceau, aujourd_hui: date) -> str:
    """Scelle le dossier (le PDF porte l'identité, le sceau public non) et note la date d'envoi."""
    _exiger(session, d, "transmis")
    _dater(session, d, "transmis", le)
    b = _beneficiaire(session, d)
    p = session.get(Prestation, _prestation_active(session, d).id)
    c = session.get(Contrat, d.contrat_id)
    emetteur = session.get(Utilisateur, auteur)
    pieces = [x for x in _pieces(session, d) if x.nature != "dossier_scelle"]
    contenu = {
        "dossier": str(d.id), "matricule": d.matricule, "date_depart": d.date_depart.isoformat(),
        "montant_demande": d.montant_demande, "du": p.du, "verse": p.verse, "calcul": p.calcul,
        "beneficiaire": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in _identite(b).items()},
        "pieces": [{"nature": x.nature, "nom_fichier": x.nom_fichier, "empreinte": x.empreinte.strip()} for x in pieces],
        "contrat": {"assureur": c.assureur, "numero_police": c.numero_police, "mandat": c.mandat_reference},
    }
    empreinte = hashlib.sha256(json.dumps(contenu, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    resume = {"organisation": org.nom, "assureur": c.assureur, "numero_police": c.numero_police,
              "date_depart": d.date_depart.isoformat(), "montant_demande": d.montant_demande,
              "emis_le": aujourd_hui.isoformat(), "emetteur": rapport.nom_de(emetteur), "probant": config.probant}
    numero, pdf = rapport.sceller_pdf(
        session, nature="prise_en_charge", empreinte=empreinte, resume=resume, config=config,
        gabarit="prise_en_charge.html", prefixe="PC",
        contexte=lambda numero, sceau: {
            "org": org, "d": d, "p": p, "b": b, "c": c, "pieces": pieces, "natures": NATURES, "numero": numero,
            "sceau": sceau, "empreinte": empreinte, "probant": config.probant, "emis_le": aujourd_hui,
            "emetteur": rapport.nom_de(emetteur), "url_verification": f"{config.url_publique}/verifier/{numero}"})
    session.add(PieceDossier(organisation_id=org.id, dossier_id=d.id, nature="dossier_scelle",
                             nom_fichier=f"dossier-{numero}.pdf", type_contenu="application/pdf", contenu=pdf,
                             empreinte=hashlib.sha256(pdf).hexdigest(), cree_par=auteur))
    _etape(session, d, "transmis", auteur, le, numero=numero)
    journaliser(session, org.id, auteur, "dossier.transmis", d.id, {"numero": numero})
    return numero


def repondre(session: Session, org: Organisation, auteur: uuid.UUID, d: DossierPriseEnCharge, *, paye: bool,
             montant: int | None, le: date, motif: str | None) -> None:
    if paye:
        if not montant or montant <= 0:
            raise ErreurMetier("montant_requis", "Indiquez le montant payé par l'assureur.", 422)
        _avancer(session, d, "paye", auteur, le, montant=montant)
        # Le paiement constaté s'écrit sur la prestation : une ligne qui remplace la précédente.
        p = _prestation_active(session, d)
        source = p.calcul.get("source") or {}
        s = prestations.Saisie(
            matricule=p.matricule, motif=p.motif, date_embauche=p.date_embauche, date_depart=p.date_depart,
            salaire_mensuel_reference=p.salaire_mensuel_reference, categorie=p.categorie,
            date_naissance=p.date_naissance, verse=p.verse, part_fonds_demandee=d.montant_demande,
            part_fonds_payee=montant, payee_le=le, soldee=True, note=p.note,
            convention_code=source.get("convention_code"))
        prestations.corriger(session, org, auteur, p.id, s, f"Paiement constaté — dossier {numero(session, d)}")
    else:
        if not (motif or "").strip():
            raise ErreurMetier("motif_requis", "Un refus se motive : recopiez celui de l'assureur.", 422)
        _avancer(session, d, "refuse", auteur, le, motif=motif)
    journaliser(session, org.id, auteur, "dossier.paye" if paye else "dossier.refuse", d.id,
                {"montant": montant} if paye else {})


# --- Effacement ---------------------------------------------------------------------------

def effacer_echus(session: Session, aujourd_hui: date) -> int:
    """Efface l'identité et les pièces des dossiers payés depuis douze mois ou plus (dans le contexte courant)."""
    n = 0
    for d in session.scalars(select(DossierPriseEnCharge)):
        paye = _dernier(session, d, "paye")
        if paye is None or paye.le + CONSERVATION > aujourd_hui or _efface(session, d):
            continue
        session.execute(delete(Beneficiaire).where(Beneficiaire.dossier_id == d.id))
        session.execute(delete(PieceDossier).where(PieceDossier.dossier_id == d.id))
        _etape(session, d, "identite_effacee", None, aujourd_hui)
        journaliser(session, d.organisation_id, None, "dossier.identite_effacee", d.id)
        n += 1
    return n


def effacer_echus_partout(moteur: Engine, aujourd_hui: date) -> int:
    """Pour la tâche programmée : chaque organisation, dans son propre contexte."""
    with moteur.connect() as c:
        organisations = list(c.execute(text("SELECT id FROM organisations")).scalars())
    total = 0
    for org_id in organisations:
        with Session(moteur) as session, session.begin():
            contexte(session.connection(), org_id)
            total += effacer_echus(session, aujourd_hui)
    return total


# --- Lire ---------------------------------------------------------------------------------

def obtenir(session: Session, dossier_id: uuid.UUID) -> DossierPriseEnCharge:
    d = session.get(DossierPriseEnCharge, dossier_id)
    if d is None:
        raise Introuvable("Dossier")
    return d


def lister(session: Session) -> list[DossierPriseEnCharge]:
    return list(session.scalars(select(DossierPriseEnCharge).order_by(DossierPriseEnCharge.cree_le.desc())))


def par_depart(session: Session) -> dict[tuple[str, date], DossierPriseEnCharge]:
    return {(d.matricule, d.date_depart): d for d in lister(session)}


def statut(session: Session, d: DossierPriseEnCharge) -> str:
    return next(e.etape for e in reversed(_evenements(session, d)) if e.etape != "identite_effacee")


def numero(session: Session, d: DossierPriseEnCharge) -> str | None:
    t = _dernier(session, d, "transmis")
    return t.numero if t else None


def en_clair(session: Session, d: DossierPriseEnCharge, *, voir_identite: bool, aujourd_hui: date) -> dict:
    evenements = _evenements(session, d)
    c = session.get(Contrat, d.contrat_id)
    efface = any(e.etape == "identite_effacee" for e in evenements)
    paye = _dernier(session, d, "paye")
    b = None if efface or not voir_identite else _beneficiaire(session, d, exiger=False)
    return {
        "id": str(d.id), "matricule": d.matricule, "date_depart": d.date_depart.isoformat(),
        "prestation_id": str(d.prestation_id), "montant_demande": d.montant_demande, "statut": statut(session, d),
        "numero": numero(session, d), "assureur": c.assureur, "numero_police": c.numero_police,
        "mandat_reference": c.mandat_reference,
        "evenements": [{"etape": e.etape, "le": e.le.isoformat(), "montant": e.montant, "motif": e.motif,
                        "numero": e.numero} for e in evenements],
        "beneficiaire": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in _identite(b).items()} if b else None,
        "pieces": [{"id": str(x.id), "nature": x.nature, "nom_fichier": x.nom_fichier, "taille": len(x.contenu),
                    "empreinte": x.empreinte.strip(), "cree_le": x.cree_le.isoformat()}
                   for x in _pieces(session, d)] if voir_identite else [],
        "identite_effacee": efface,
        "efface_le": (paye.le + CONSERVATION).isoformat() if paye and not efface else None,
        "constats": _constats(session, d, evenements, aujourd_hui),
    }


def resume(session: Session, d: DossierPriseEnCharge) -> dict:
    return {"id": str(d.id), "statut": statut(session, d), "numero": numero(session, d)}


# --- Interne ------------------------------------------------------------------------------

def _evenements(session: Session, d: DossierPriseEnCharge) -> list[EvenementDossier]:
    return list(session.scalars(select(EvenementDossier).where(EvenementDossier.dossier_id == d.id)
                                .order_by(EvenementDossier.cree_le)))


def _dernier(session: Session, d: DossierPriseEnCharge, etape: str) -> EvenementDossier | None:
    return next((e for e in reversed(_evenements(session, d)) if e.etape == etape), None)


def _efface(session: Session, d: DossierPriseEnCharge) -> bool:
    return _dernier(session, d, "identite_effacee") is not None


def _exiger(session: Session, d: DossierPriseEnCharge, suivante: str) -> None:
    courant = statut(session, d)
    if suivante not in _SUITES[courant]:
        raise ErreurMetier("etape_impossible", f"Le dossier est « {courant} » : il ne peut pas passer à « {suivante} ».",
                           409)


def _avancer(session, d, etape, auteur, le, **champs) -> None:
    _exiger(session, d, etape)
    _dater(session, d, etape, le)
    _etape(session, d, etape, auteur, le, **champs)


def _dater(session, d: DossierPriseEnCharge, etape: str, le: date) -> None:
    """Une date peut être passée (un dossier repris, envoyé avant d'arriver ici), jamais à venir ni avant le
    départ ; et l'assureur ne répond pas avant d'avoir reçu le dossier."""
    if le > date.today():
        raise ErreurMetier("date_a_venir", "Une étape se note quand elle a eu lieu : pas de date à venir.", 422)
    if le < d.date_depart:
        raise ErreurMetier("date_avant_depart", "Une étape du dossier ne précède pas le départ du salarié.", 422)
    envoi = _dernier(session, d, "transmis")
    if etape in ("paye", "refuse") and envoi and le < envoi.le:
        raise ErreurMetier("reponse_avant_envoi", f"L'assureur ne répond pas avant l'envoi du {envoi.le:%d/%m/%Y}.",
                           422)


def _etape(session, d, etape, auteur, le, **champs) -> None:
    session.add(EvenementDossier(organisation_id=d.organisation_id, dossier_id=d.id, etape=etape, le=le, par=auteur,
                                 **champs))
    session.flush()


def _beneficiaire(session: Session, d: DossierPriseEnCharge, exiger: bool = True) -> Beneficiaire | None:
    b = session.scalars(select(Beneficiaire).where(Beneficiaire.dossier_id == d.id)).first()
    if b is None and exiger:
        raise ErreurMetier("identite_effacee", "L'identité du bénéficiaire a été effacée.", 409)
    return b


def _identite(b: Beneficiaire | None) -> dict:
    if b is None:
        return {}
    return {k: getattr(b, k) for k in ("qualite", "nom", "prenoms", "date_naissance", "piece_type", "piece_numero",
                                       "telephone", "moyen_paiement", "coordonnees_paiement")}


def _pieces(session: Session, d: DossierPriseEnCharge) -> list[PieceDossier]:
    return list(session.scalars(select(PieceDossier).where(PieceDossier.dossier_id == d.id)
                                .order_by(PieceDossier.cree_le)))


def _prestation_active(session: Session, d: DossierPriseEnCharge) -> Prestation:
    p = next((p for p in prestations.actives(session) if (p.matricule, p.date_depart) == (d.matricule, d.date_depart)),
             None)
    if p is None:
        raise ErreurMetier("prestation_introuvable", "Le départ de ce dossier n'a plus de ligne active.", 409)
    return p


def _delai(session: Session) -> tuple[int, bool]:
    fiche = session.scalars(select(FicheRegime).order_by(FicheRegime.emise_le.desc()).limit(1)).first()
    exige = (fiche.conditions or {}).get("delai_paiement_jours_maximum") if fiche else None
    return (int(exige), True) if exige else (DELAI_PAR_DEFAUT, False)


def _constats(session, d, evenements, aujourd_hui: date) -> list[dict]:
    if not evenements or evenements[-1].etape != "transmis":
        return []
    jours = (aujourd_hui - evenements[-1].le).days
    delai, exige = _delai(session)
    if jours <= delai:
        return []
    reference = "exigés au cahier des charges" if exige else "d'usage (aucun délai n'est fixé au cahier des charges)"
    return [{"niveau": "avertit", "code": "retard_assureur",
             "message": f"Transmis le {evenements[-1].le:%d/%m/%Y}, sans réponse depuis {jours} jours : au-delà des "
                        f"{delai} jours {reference}. Relancer l'assureur."}]
