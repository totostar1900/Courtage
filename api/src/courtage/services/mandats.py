"""Le mandat de courtage : le client demande un accompagnement, le conseiller propose le mandat, le client le signe.

Un mandat type, inspiré des lettres de mission des grands courtiers internationaux (« terms of business », « broker
of record ») et adapté au Code des assurances CIMA : l'objet, la mission, le devoir de conseil, les obligations de
chacun, la rémunération (gratuit pour le client : seul l'assureur rémunère le courtier), l'indépendance, la
confidentialité, la durée et la résiliation, la responsabilité, les litiges.

Le texte se construit ici, une fois, pour l'écran comme pour le PDF : le client signe exactement ce qu'il a lu, et
l'empreinte du texte le prouve. Signé, le mandat est scellé (MC-), et un contrat « courtage » prend effet à sa date.
"""
import hashlib
import json
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from courtage.db import Contrat, Document, Justificatif, MandatCourtage, Organisation, Utilisateur
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.langue import langue, t

from . import avis, contrats, journaliser, rapport

BESOINS = {
    "placement": "Placer notre engagement IFC auprès d'un assureur",
    "mise_en_concurrence": "Remettre en concurrence notre contrat actuel",
    "prestations": "Faire porter nos départs en retraite auprès de l'assureur",
    "regime": "Être conseillés sur notre régime et son financement",
}
PERIMETRE = {
    "analyse": "l'analyse des besoins de l'entreprise et de son régime d'indemnités de fin de carrière",
    "consultation": "la consultation du marché, la présentation d'offres comparées et la négociation des conditions",
    "placement": "le placement du contrat auprès de l'assureur choisi par le Client et sa mise en place",
    "gestion": "le suivi du contrat et la présentation des demandes de prestations à l'assureur",
    "renouvellement": "le renouvellement du contrat et sa remise en concurrence périodique",
}
# L'anglais des libellés À L'ÉCRAN (le tableau, les besoins d'une demande). Le texte du mandat (`texte`), lui, reste
# en français : son empreinte est signée, elle ne peut pas dépendre de la langue de celui qui l'ouvre.
BESOINS_EN = {
    "placement": "Place our IFC liability with an insurer",
    "mise_en_concurrence": "Put our current contract out to tender again",
    "prestations": "Have our retirements handled with the insurer",
    "regime": "Get advice on our plan and how it is funded",
}
PERIMETRE_EN = {
    "analyse": "analysing the company's needs and its end-of-service benefit (IFC) plan",
    "consultation": "consulting the market, presenting compared offers and negotiating terms",
    "placement": "placing the contract with the insurer chosen by the Client and setting it up",
    "gestion": "following up the contract and presenting benefit payment claims to the insurer",
    "renouvellement": "renewing the contract and putting it out to tender periodically",
}


def _libelles(fr: dict[str, str], en: dict[str, str]) -> dict[str, str]:
    return {k: en.get(k, v) for k, v in fr.items()} if langue() == "en" else fr


MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre",
        "décembre")
VERSION_TEXTE = "mandat-courtage-2"


def courtier() -> dict:
    """L'identité du cabinet, par la configuration : jamais inventée."""
    from courtage import cabinet
    c = cabinet.identite()
    return {"nom": c["nom"], "agrement": c["agrement"], "adresse": c["adresse"]}


def _date(d: date) -> str:
    return f"{d.day}{'er' if d.day == 1 else ''} {MOIS[d.month - 1]} {d.year}"


# --- Le texte ------------------------------------------------------------------

def texte(org: Organisation, m: MandatCourtage, conseiller: str) -> dict:
    """Les articles du mandat, tels que le client les lit et les signe."""
    c = courtier()
    missions = [PERIMETRE[p] for p in PERIMETRE if p in (m.perimetre or [])]
    exclusivite = ("Le Client confie ce mandat au Courtier à titre exclusif pour les risques ci-dessus : il ne confie "
                   "pas le même mandat à un autre intermédiaire pendant sa durée, et en informe les assureurs "
                   "consultés (lettre de désignation)." if m.exclusif else
                   "Ce mandat n'est pas exclusif : le Client reste libre de consulter d'autres intermédiaires, et en "
                   "informe le Courtier.")
    articles = [
        ("Parties", [
            f"Le présent mandat est conclu entre {org.nom}, ci-après « le Client », et {c['nom']}, intermédiaire "
            f"d'assurance agréé sous le numéro {c['agrement']}, dont le siège est {c['adresse']}, ci-après « le "
            f"Courtier », représenté par {conseiller}, conseiller en charge du dossier."]),
        ("Objet", [
            "Le Client charge le Courtier de le représenter auprès des entreprises d'assurance pour la couverture de "
            "ses engagements d'indemnités de fin de carrière (IFC) envers son personnel.",
            exclusivite]),
        ("Mission du Courtier", [
            "Dans ce cadre, le Courtier assure : " + " ; ".join(missions) + ".",
            "Le Courtier agit au nom et pour le compte du Client. Il ne signe aucun contrat d'assurance à sa place : "
            "le choix de l'assureur et la souscription restent des décisions du Client."]),
        ("Devoir de conseil et d'information", [
            "Le Courtier conseille le Client avec loyauté et compétence, dans son seul intérêt. Il fonde ses "
            "recommandations sur une analyse objective d'un nombre suffisant d'offres du marché, et dit au Client, "
            "par écrit, les raisons de sa recommandation.",
            "Il remet au Client, avant toute souscription, les informations exigées par le Code des assurances des "
            "États membres de la CIMA, et lui signale toute clause qui limiterait sa garantie ou sa liberté de "
            "changer d'assureur."]),
        ("Obligations du Client", [
            "Le Client fournit au Courtier des informations exactes et complètes sur son personnel, son régime et "
            "ses engagements, et l'informe sans délai de tout changement qui les affecterait. Il sait qu'une "
            "déclaration inexacte peut réduire ou supprimer la garantie.",
            "Le Client règle les primes directement à l'assureur, sauf accord écrit contraire."]),
        ("Rémunération", [
            "Le mandat est gratuit pour le Client : le Courtier ne lui facture ni honoraires, ni frais, au titre de "
            "ce mandat ou des études qu'il réalise pour lui.",
            "Le Courtier est rémunéré exclusivement par la commission versée par l'assureur retenu, dans les limites "
            "fixées par la réglementation applicable. Il communique au Client, sur simple demande, le taux et le "
            "montant de cette commission."]),
        ("Indépendance et conflits d'intérêts", [
            "Le Courtier déclare au Client tout lien, capitalistique ou contractuel, avec un assureur consulté. Il "
            "l'informe de toute situation de conflit d'intérêts et de la manière dont il la traite."]),
        ("Confidentialité et données personnelles", [
            "Chaque partie garde confidentielles les informations reçues de l'autre. Le Courtier n'utilise les "
            "données du personnel que pour ce mandat, par matricule ; il ne recueille l'identité d'un salarié que "
            "pour présenter sa prestation à l'assureur, et l'efface une fois celle-ci réglée, selon les durées "
            "légales de conservation."]),
        ("Durée et résiliation", [
            f"Le mandat prend effet le {_date(m.date_effet)}, pour une durée de {m.duree_mois} mois. Il se "
            f"renouvelle ensuite par tacite reconduction, par périodes de douze mois.",
            f"Chaque partie peut y mettre fin par écrit, avec un préavis de {m.preavis_mois} mois. À la fin du "
            "mandat, le Courtier remet au Client, ou au nouvel intermédiaire qu'il désigne, les éléments du dossier "
            "et l'état des demandes en cours."]),
        ("Responsabilité", [
            "Le Courtier est couvert par l'assurance de responsabilité civile professionnelle et la garantie "
            "financière exigées des intermédiaires d'assurance par la réglementation CIMA ; il en justifie sur "
            "demande."]),
        ("Réclamations et litiges", [
            f"Toute réclamation s'adresse d'abord au conseiller du dossier, puis à la direction de {c['nom']}. Le "
            f"mandat est régi par le droit de l'État du siège du Client ; à défaut d'accord amiable, les tribunaux "
            f"de ce siège sont compétents."]),
        ("Signature", [
            "Le Client accepte ce mandat par voie électronique sur la plateforme. Le document scellé qui en résulte "
            "porte un numéro, vérifiable à tout moment, et fait foi de son contenu."]),
    ]
    if (m.conditions or "").strip():
        articles.insert(-1, ("Conditions particulières", [m.conditions.strip()]))
    return {"version": VERSION_TEXTE, "courtier": c, "client": {"nom": org.nom, "pays": org.pays},
            "conseiller": conseiller, "date_effet": m.date_effet.isoformat(), "duree_mois": m.duree_mois,
            "preavis_mois": m.preavis_mois, "exclusif": m.exclusif, "perimetre": list(m.perimetre or []),
            "articles": [{"numero": i + 1, "titre": t, "paragraphes": p} for i, (t, p) in enumerate(articles)]}


def empreinte(contenu: dict) -> str:
    return hashlib.sha256(json.dumps(contenu, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# --- Les actes -----------------------------------------------------------------

def en_cours(session: Session) -> MandatCourtage | None:
    return session.scalars(select(MandatCourtage).where(MandatCourtage.statut.in_(("demande", "propose")))).first()


def obtenir(session: Session, mandat_id: uuid.UUID) -> MandatCourtage:
    m = session.get(MandatCourtage, mandat_id)
    if m is None:
        raise Introuvable("Mandat")
    return m


def demander(session: Session, org: Organisation, auteur: uuid.UUID, besoins: list[str], message: str | None,
             aujourd_hui: date) -> MandatCourtage:
    besoins = [b for b in BESOINS if b in besoins]
    if not besoins:
        raise ErreurMetier("besoins_requis", t("Dire ce que vous attendez de l'accompagnement.",
                                                "Say what you expect from the support."), 422)
    if contrats.service_a_la_date(session, aujourd_hui).service == "courtage":
        raise ErreurMetier("mandat_en_vigueur", t("Un mandat de courtage est déjà en vigueur pour ce dossier.",
                                                   "A brokerage mandate is already in force for this account."), 409)
    if en_cours(session):
        raise ErreurMetier("demande_en_cours", t("Une demande d'accompagnement est déjà en cours.",
                                                  "A request for support is already in progress."), 409)
    m = MandatCourtage(organisation_id=org.id, besoins=besoins, message=(message or "").strip() or None,
                       demande_par=auteur)
    session.add(m)
    session.flush()
    journaliser(session, org.id, auteur, "mandat.demande", m.id, {"besoins": besoins})
    avis.prevoir(session, "mandat_demande", avis.conseillers(session, org.id), auteur=auteur, org=org.id,
                 entreprise=org.nom)
    return m


def proposer(session: Session, org: Organisation, m: MandatCourtage, auteur: uuid.UUID, *, perimetre: list[str],
             date_effet: date, duree_mois: int, preavis_mois: int, exclusif: bool, conditions: str | None,
             aujourd_hui: date) -> MandatCourtage:
    """Proposer, ou reprendre une proposition tant qu'elle n'est pas signée : le texte et son empreinte suivent."""
    if m.statut not in ("demande", "propose"):
        raise ErreurMetier("mandat_clos", t("Ce mandat n'attend plus de proposition.",
                                             "This mandate is no longer awaiting a proposal."), 409)
    perimetre = [p for p in PERIMETRE if p in perimetre]
    if not perimetre:
        raise ErreurMetier("perimetre_requis", t("Choisir au moins une mission.", "Choose at least one service."), 422)
    if date_effet < aujourd_hui:
        raise ErreurMetier("date_passee", t("Un mandat prend effet aujourd'hui ou plus tard.",
                                             "A mandate takes effect today or later."), 422)
    m.perimetre, m.date_effet, m.duree_mois, m.preavis_mois = perimetre, date_effet, duree_mois, preavis_mois
    m.exclusif, m.conditions = exclusif, (conditions or "").strip() or None
    m.propose_par, m.propose_le = auteur, datetime.now(timezone.utc)
    m.empreinte_texte = empreinte(texte(org, m, _nom(session, auteur)))
    m.statut = "propose"
    session.flush()
    journaliser(session, org.id, auteur, "mandat.propose", m.id, {"empreinte": m.empreinte_texte})
    avis.prevoir(session, "mandat_propose", avis.entreprise(session, org.id), auteur=auteur, org=org.id,
                 entreprise=org.nom)
    return m


QUALITES = {"representant_legal": "représentant légal", "delegataire": "délégataire, sur délégation de pouvoir"}
QUALITES_EN = {"representant_legal": "legal representative", "delegataire": "delegate, under a delegation of authority"}


def signer(session: Session, org: Organisation, m: MandatCourtage, auteur: uuid.UUID, *, nom: str,
           fonction: str | None, empreinte_lue: str, config: rapport.ConfigSceau, aujourd_hui: date,
           qualite: str | None = None, delegation_id: uuid.UUID | None = None) -> Document:
    """Signer, c'est aussi dire en quelle qualité : le représentant légal de l'entreprise, ou une personne qui a
    reçu pouvoir et dont la délégation est déposée (`justificatifs`, nature `delegation`)."""
    if m.statut != "propose":
        raise ErreurMetier("mandat_non_propose", t("Ce mandat n'attend pas de signature.",
                                                    "This mandate is not awaiting a signature."), 409)
    nom = (nom or "").strip()
    if len(nom) < 3:
        raise ErreurMetier("signataire_requis", t("Écrire vos nom et prénom pour signer.",
                                                   "Type your full name to sign."), 422)
    if qualite not in QUALITES:
        raise ErreurMetier("qualite_requise", t("Dire en quelle qualité vous signez : représentant légal ou délégataire.",
                                                 "Say in what capacity you sign: legal representative or delegate."), 422)
    delegation = None
    if qualite == "delegataire":
        delegation = session.get(Justificatif, delegation_id) if delegation_id else None
        if delegation is None or delegation.nature != "delegation":
            raise ErreurMetier("delegation_requise", t("Déposer la délégation de pouvoir qui vous autorise à signer.",
                                                        "Upload the delegation of authority that entitles you to sign."), 422)
    contenu = texte(org, m, _nom(session, m.propose_par))
    if empreinte_lue != m.empreinte_texte or empreinte(contenu) != m.empreinte_texte:
        raise ErreurMetier("texte_modifie", t("Le texte a changé depuis que vous l'avez ouvert : relisez-le.",
                                               "The text has changed since you opened it: read it again."), 409)
    signe_le = datetime.now(timezone.utc)
    signature = {"nom": nom, "fonction": (fonction or "").strip() or None, "le": signe_le.isoformat(),
                 "qualite": QUALITES[qualite],
                 "delegation": None if delegation is None else {"nom_fichier": delegation.nom_fichier,
                                                                 "empreinte": delegation.empreinte}}
    resume = {"organisation": org.nom, "pays": org.pays, "courtier": contenu["courtier"]["nom"],
              "date_effet": m.date_effet.isoformat(), "signataire": nom, "qualite": qualite,
              "signe_le": signe_le.date().isoformat(),
              "probant": config.probant}
    document = rapport.sceller_document(
        session, org, nature="mandat_courtage", empreinte=m.empreinte_texte, resume=resume, config=config,
        gabarit="mandat_courtage.html", mandat_id=m.id, prefixe="MC",
        contexte=lambda numero, sceau: {"c": contenu, "signature": signature, "numero": numero, "sceau": sceau,
                                        "url_verification": f"{config.url_publique}/verifier/{numero}",
                                        "probant": config.probant, "empreinte": m.empreinte_texte})
    actuel = contrats.service_a_la_date(session, m.date_effet).contrat
    contrat = contrats.enregistrer(
        session, org.id, auteur, en_vigueur_du=m.date_effet, service="courtage",
        assureur=actuel.assureur if actuel else None, numero_police=actuel.numero_police if actuel else None,
        date_effet_police=actuel.date_effet_police if actuel else None, mandat_reference=document.numero,
        note="Mandat signé sur la plateforme.")
    m.statut, m.signe_par, m.signe_le = "signe", auteur, signe_le
    m.signataire_nom, m.signataire_fonction, m.contrat_id = nom, signature["fonction"], contrat.id
    m.signataire_qualite, m.delegation_id = qualite, delegation.id if delegation else None
    session.flush()
    journaliser(session, org.id, auteur, "mandat.signe", m.id, {"numero": document.numero, "qualite": qualite,
                                                                "delegation": str(m.delegation_id) if m.delegation_id else None})
    avis.prevoir(session, "mandat_signe", avis.conseillers(session, org.id), auteur=auteur, org=org.id,
                 entreprise=org.nom, numero=document.numero)
    return document


def clore(session: Session, m: MandatCourtage, auteur: uuid.UUID, statut: str, motif: str | None) -> None:
    """`refuse` : le client décline la proposition. `retire` : la demande ou la proposition est abandonnée."""
    if m.statut not in ("demande", "propose") or (statut == "refuse" and m.statut != "propose"):
        raise ErreurMetier("mandat_clos", t("Ce mandat ne peut plus être " + ("refusé." if statut == "refuse" else "retiré."),
                                            "This mandate can no longer be "
                                            + ("declined." if statut == "refuse" else "withdrawn.")), 409)
    m.statut, m.motif = statut, (motif or "").strip() or None
    session.flush()
    journaliser(session, m.organisation_id, auteur, f"mandat.{statut}", m.id, {"motif": m.motif})
    if statut == "refuse":
        org = session.get(Organisation, m.organisation_id)
        avis.prevoir(session, "mandat_refuse", avis.conseillers(session, org.id), auteur=auteur, org=org.id,
                     entreprise=org.nom)


# --- Lire ----------------------------------------------------------------------

def _nom(session: Session, utilisateur_id: uuid.UUID | None) -> str:
    return rapport.nom_de(session.get(Utilisateur, utilisateur_id)) if utilisateur_id else ""


def _delegation(session: Session, justificatif_id: uuid.UUID | None) -> dict | None:
    j = session.get(Justificatif, justificatif_id) if justificatif_id else None
    return None if j is None else {"id": str(j.id), "nom_fichier": j.nom_fichier, "depose_le": j.depose_le.isoformat()}


def document_de(session: Session, m: MandatCourtage) -> Document | None:
    return session.scalars(select(Document).where(Document.mandat_id == m.id)).first()


def en_clair(session: Session, org: Organisation, m: MandatCourtage) -> dict:
    d = document_de(session, m)
    contrat = session.get(Contrat, m.contrat_id) if m.contrat_id else None
    besoins = _libelles(BESOINS, BESOINS_EN)
    return {
        "id": str(m.id), "statut": m.statut,
        "besoins": [{"code": b, "libelle": besoins[b]} for b in m.besoins if b in besoins], "message": m.message,
        "demande_par": _nom(session, m.demande_par), "demande_le": m.demande_le.isoformat(),
        "proposition": None if m.statut in ("demande",) or m.propose_le is None else {
            "perimetre": m.perimetre, "date_effet": m.date_effet.isoformat(), "duree_mois": m.duree_mois,
            "preavis_mois": m.preavis_mois, "exclusif": m.exclusif, "conditions": m.conditions,
            "propose_par": _nom(session, m.propose_par), "propose_le": m.propose_le.isoformat(),
            "empreinte": m.empreinte_texte,
            "texte": texte(org, m, _nom(session, m.propose_par))},
        "signature": None if m.statut != "signe" else {
            "nom": m.signataire_nom, "fonction": m.signataire_fonction, "le": m.signe_le.isoformat(),
            "qualite": m.signataire_qualite,
            "qualite_libelle": _libelles(QUALITES, QUALITES_EN).get(m.signataire_qualite) if m.signataire_qualite else None,
            "delegation": _delegation(session, m.delegation_id),
            "numero": d.numero if d else None, "contrat_du": contrat.en_vigueur_du.isoformat() if contrat else None},
        "motif": m.motif,
    }


def tableau(session: Session, org: Organisation, aujourd_hui: date) -> dict:
    mandats = list(session.scalars(select(MandatCourtage).order_by(MandatCourtage.demande_le.desc())))
    return {"service": contrats.service_a_la_date(session, aujourd_hui).service,
            "mandats": [en_clair(session, org, m) for m in mandats],
            "besoins": [{"code": k, "libelle": v} for k, v in _libelles(BESOINS, BESOINS_EN).items()],
            "perimetre": [{"code": k, "libelle": v} for k, v in _libelles(PERIMETRE, PERIMETRE_EN).items()],
            "courtier": courtier()}
