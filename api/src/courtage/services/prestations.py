"""Prestations (spec prestations §2, §4, §5) : un départ, sans identité, et ce qu'il aurait dû coûter.

Le DÛ est recalculé par la plateforme avec la règle en vigueur le jour du
départ : la version adoptée du régime (le plus favorable de lui et de la
convention, ancienneté par ancienneté), sinon la convention — nommée, ou celle
de la dernière étude. Le VERSÉ est déclaré ; il peut dépasser le dû (l'entreprise
est souveraine) : un écart est montré, jamais bloqué. Un départ hors retraite ne
doit rien au titre du régime mais compte pour la rotation.

Une prestation est une écriture. Une correction ajoute une ligne qui en remplace
une autre (une seule fois) et dit pourquoi ; une annulation aussi. Les lignes
« actives » sont celles qu'aucune autre ne remplace, hors annulations.
"""
import uuid
from math import floor
from dataclasses import asdict, dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from courtage.actuariat.ifc import Regles, annees_entre, mois_dus
from courtage.db import DossierPriseEnCharge, Etude, FichierPersonnel, Organisation, Prestation, Regime, VersionRegime
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.fichier import Anomalie, anomalies_en_clair
from courtage.langue import t
from courtage.fichier.departs import LigneDepart, lire_departs
from courtage.referentiel import referentiel_courant

from . import contrats, journaliser, regimes

AUTRES = "*"


@dataclass(frozen=True)
class Saisie:
    matricule: str
    motif: str
    date_embauche: date
    date_depart: date
    salaire_mensuel_reference: int
    categorie: str | None = None
    date_naissance: date | None = None
    verse: int | None = None
    part_fonds_demandee: int | None = None
    part_fonds_payee: int | None = None
    payee_le: date | None = None
    soldee: bool = False
    note: str | None = None
    convention_code: str | None = None


# --- Le dû ----------------------------------------------------------------------------

def regle_au_depart(session: Session, jour: date, categorie: str | None,
                    convention_code: str | None) -> tuple[Regles, dict]:
    """La règle qui s'appliquait le jour du départ, et d'où elle vient."""
    version = session.scalars(
        select(VersionRegime).where(VersionRegime.statut == "adoptee", VersionRegime.en_vigueur_du <= jour)
        .order_by(VersionRegime.en_vigueur_du.desc(), VersionRegime.numero.desc()).limit(1)).first()
    if version is not None:
        par_categorie = regimes.regles(session, version, jour)
        retenue = categorie if categorie in par_categorie else AUTRES if AUTRES in par_categorie else None
        if retenue is None:
            connues = ", ".join(sorted(par_categorie))
            raise ErreurMetier("categorie_inconnue", t(
                f"La catégorie « {categorie or '—'} » n'a pas de règle dans le "
                f"régime en vigueur au {jour:%d/%m/%Y} (catégories : {connues}).",
                f"Category “{categorie or '—'}” has no rule in the plan in force on {jour:%d/%m/%Y} "
                f"(categories: {connues})."), 422)
        regime = session.get(Regime, version.regime_id)
        return par_categorie[retenue], {"type": "regime", "regime_version_id": str(version.id),
                                        "libelle": f"{regime.nom}, version {version.numero}", "categorie": retenue}

    code = convention_code or _convention_de_la_derniere_etude(session)
    if not code:
        raise ErreurMetier("convention_requise", t(
            "Aucun régime adopté ne couvre cette date et aucune étude ne dit la "
            "convention : indiquez la convention collective applicable.",
            "No adopted plan covers this date and no study names the collective agreement: specify the "
            "applicable collective agreement."), 422)
    try:
        convention = referentiel_courant().convention(code, jour)
    except LookupError as e:
        raise ErreurMetier("convention_introuvable", str(e), 422) from None
    return Regles(bareme=convention.bareme), {"type": "convention", "convention_code": code,
                                              "libelle": convention.libelle}


def _convention_de_la_derniere_etude(session: Session) -> str | None:
    etude = session.scalars(select(Etude).order_by((Etude.statut == "emise").desc(), Etude.date_evaluation.desc(),
                                                   Etude.cree_le.desc()).limit(1)).first()
    return etude.convention_code if etude else None


def calculer(session: Session, s: Saisie) -> tuple[int, dict]:
    anciennete = annees_entre(s.date_embauche, s.date_depart)
    # Affichée tronquée : 21,997 ans se lit « 21,99 » — le barème compte 21 années révolues, pas 22.
    lue = floor(anciennete * 100 + 1e-9) / 100
    if s.motif != "retraite":
        return 0, {"anciennete": lue, "mois": 0, "plancher_applique": False, "source": None,
                   "raison": RAISON_HORS_RETRAITE}
    regles, source = regle_au_depart(session, s.date_depart, s.categorie, s.convention_code)
    mois, plancher = mois_dus(regles, anciennete)
    return round(mois * s.salaire_mensuel_reference), {
        "anciennete": lue, "mois": round(mois, 4), "plancher_applique": plancher, "source": source}


# Enregistrée dans `calcul` (en français, comme toute écriture) ; traduite à l'affichage par `_calcul_en_clair`.
RAISON_HORS_RETRAITE = "Départ hors retraite : pas d'IFC au titre du régime ; il compte pour la rotation."


def _calcul_en_clair(calcul: dict | None) -> dict | None:
    if calcul and calcul.get("raison") == RAISON_HORS_RETRAITE:
        return {**calcul, "raison": t(RAISON_HORS_RETRAITE, "Departure other than retirement: no IFC under the "
                                                            "plan; it counts towards staff turnover.")}
    return calcul


# --- Écrire -----------------------------------------------------------------------------

def _verifier(s: Saisie) -> None:
    if s.date_depart < s.date_embauche:
        raise ErreurMetier("depart_avant_embauche", t("La date de départ précède la date d'embauche.",
                                                       "The departure date is before the hire date."), 422)
    if s.date_naissance and s.date_naissance >= s.date_embauche:
        raise ErreurMetier("naissance_apres_embauche", t("La date de naissance doit précéder l'embauche.",
                                                          "The date of birth must be before the hire date."), 422)
    if s.part_fonds_payee is not None and s.payee_le is None:
        raise ErreurMetier("date_paiement_requise", t("Un paiement du fonds a une date : indiquez-la.",
                                                       "A payment by the fund has a date: enter it."), 422)


def enregistrer(session: Session, org: Organisation, auteur: uuid.UUID, s: Saisie, *, origine: str = "saisie",
                import_id: uuid.UUID | None = None, remplace: Prestation | None = None,
                motif_correction: str | None = None) -> Prestation:
    _verifier(s)
    du, calcul = calculer(session, s)
    p = Prestation(organisation_id=org.id, matricule=s.matricule.strip(), categorie=s.categorie, motif=s.motif,
                   date_naissance=s.date_naissance, date_embauche=s.date_embauche, date_depart=s.date_depart,
                   salaire_mensuel_reference=s.salaire_mensuel_reference, du=du, calcul=calcul, verse=s.verse,
                   part_fonds_demandee=s.part_fonds_demandee, part_fonds_payee=s.part_fonds_payee,
                   payee_le=s.payee_le, soldee=s.soldee, origine=origine, import_id=import_id, note=s.note,
                   remplace_id=remplace.id if remplace else None, motif_correction=motif_correction,
                   cree_par=auteur)
    _inserer(session, p)
    journaliser(session, org.id, auteur, "prestation.corrigee" if remplace else "prestation.enregistree", p.id,
                {"motif": s.motif, "date_depart": s.date_depart.isoformat(), "origine": origine,
                 **({"remplace": str(remplace.id)} if remplace else {})})
    return p


def corriger(session: Session, org: Organisation, auteur: uuid.UUID, prestation_id: uuid.UUID, s: Saisie,
             motif_correction: str) -> Prestation:
    ancienne = _active(session, prestation_id)
    if (s.matricule.strip(), s.date_depart) != (ancienne.matricule, ancienne.date_depart):
        _sans_dossier(session, ancienne)
    return enregistrer(session, org, auteur, s, origine=ancienne.origine, import_id=ancienne.import_id,
                       remplace=ancienne, motif_correction=_motif(motif_correction))


def annuler(session: Session, org: Organisation, auteur: uuid.UUID, prestation_id: uuid.UUID,
            motif_correction: str) -> Prestation:
    """Une ligne qui retire la précédente : elle en reprend les faits, pour que l'annulation se lise seule."""
    a = _active(session, prestation_id)
    _sans_dossier(session, a)
    p = Prestation(organisation_id=org.id, matricule=a.matricule, categorie=a.categorie, motif=a.motif,
                   date_naissance=a.date_naissance, date_embauche=a.date_embauche, date_depart=a.date_depart,
                   salaire_mensuel_reference=a.salaire_mensuel_reference, du=a.du, calcul=a.calcul, verse=a.verse,
                   part_fonds_demandee=a.part_fonds_demandee, part_fonds_payee=a.part_fonds_payee,
                   payee_le=a.payee_le, soldee=a.soldee, origine=a.origine, import_id=a.import_id, note=a.note,
                   remplace_id=a.id, annulation=True, motif_correction=_motif(motif_correction), cree_par=auteur)
    _inserer(session, p)
    journaliser(session, org.id, auteur, "prestation.annulee", p.id, {"annule": str(a.id)})
    return p


def apercu(session: Session, s: Saisie) -> dict:
    """Le dû, le calcul et les constats d'une saisie, sans rien enregistrer."""
    _verifier(s)
    du, calcul = calculer(session, s)
    return {"du": du, "calcul": _calcul_en_clair(calcul), "constats": constats(_vue(s, du), presences(session)),
            "service": contrats.service_a_la_date(session, s.date_depart).service}


def _vue(s: Saisie, du: int) -> "_Apercu":
    return _Apercu(**{k: getattr(s, k) for k in _Apercu.__dataclass_fields__ if k != "du"}, du=du)


def declarer_paiement(session: Session, org: Organisation, auteur: uuid.UUID, prestation_id: uuid.UUID, *,
                      part_fonds_demandee: int | None, part_fonds_payee: int, payee_le: date) -> Prestation:
    """Hors dossier de courtage : l'entreprise déclare ce que son assureur a payé. Une ligne qui remplace."""
    a = _active(session, prestation_id)
    _sans_dossier(session, a)
    if payee_le < a.date_depart:
        raise ErreurMetier("paiement_avant_depart", t("Un paiement ne précède pas le départ du salarié.",
                                                       "A payment cannot be before the employee's departure."), 422)
    source = (a.calcul or {}).get("source") or {}
    s = Saisie(matricule=a.matricule, motif=a.motif, date_embauche=a.date_embauche, date_depart=a.date_depart,
               salaire_mensuel_reference=a.salaire_mensuel_reference, categorie=a.categorie,
               date_naissance=a.date_naissance, verse=a.verse,
               part_fonds_demandee=part_fonds_demandee if part_fonds_demandee is not None else a.part_fonds_demandee,
               part_fonds_payee=part_fonds_payee, payee_le=payee_le, soldee=True, note=a.note,
               convention_code=source.get("convention_code"))
    return enregistrer(session, org, auteur, s, origine=a.origine, import_id=a.import_id, remplace=a,
                       motif_correction="Paiement de l'assureur déclaré par l'entreprise")


def _sans_dossier(session: Session, p: Prestation) -> None:
    """Un départ porté par un dossier de prise en charge garde son matricule et sa date : c'est sa clé."""
    if session.scalar(select(DossierPriseEnCharge.id).where(DossierPriseEnCharge.matricule == p.matricule,
                                                            DossierPriseEnCharge.date_depart == p.date_depart)):
        raise ErreurMetier("dossier_ouvert", t("Un dossier de prise en charge porte ce départ : il ne s'annule pas, et "
                                               "son matricule comme sa date de départ ne changent pas.",
                                               "A claim file covers this departure: it cannot be cancelled, and its "
                                               "staff number and departure date cannot change."), 409)


def _motif(texte: str) -> str:
    if not (texte or "").strip():
        raise ErreurMetier("motif_correction_requis", t("Dites pourquoi la ligne est corrigée ou annulée.",
                                                         "Say why the line is being corrected or cancelled."), 422)
    return texte.strip()


def _inserer(session: Session, p: Prestation) -> None:
    session.add(p)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as e:
        if "prestations_remplace_id_key" in str(e.orig):
            raise ErreurMetier("deja_corrigee", _DEJA_CORRIGEE(), 409) from None
        raise


def _DEJA_CORRIGEE() -> str:  # noqa: N802
    return t("Cette ligne a déjà été corrigée ou annulée : corrigez la plus récente.",
             "This line has already been corrected or cancelled: correct the most recent one.")


def _active(session: Session, prestation_id: uuid.UUID) -> Prestation:
    p = session.get(Prestation, prestation_id)
    if p is None or p.annulation:
        raise Introuvable("Prestation")
    if session.scalar(select(Prestation.id).where(Prestation.remplace_id == p.id)) is not None:
        raise ErreurMetier("deja_corrigee", _DEJA_CORRIGEE(), 409)
    return p


# --- Lire -----------------------------------------------------------------------------

def actives(session: Session) -> list[Prestation]:
    suivante = aliased(Prestation)
    remplacees = select(suivante.remplace_id).where(suivante.remplace_id.is_not(None))
    return list(session.scalars(select(Prestation).where(Prestation.annulation.is_(False),
                                                         Prestation.id.not_in(remplacees))
                                .order_by(Prestation.date_depart.desc(), Prestation.cree_le.desc())))


def presences(session: Session) -> list[tuple[date, set[str]]]:
    """Pour chaque fichier du personnel : sa date et ses matricules."""
    return [(f.date_donnees, {l["matricule"] for l in f.lignes if l.get("matricule")})
            for f in session.scalars(select(FichierPersonnel))]


def constats(p, presences_: list[tuple[date, set[str]]]) -> list[dict]:
    """Ce que la ligne révèle. `p` : une Prestation ou une ligne d'aperçu (mêmes attributs)."""
    sortie = []
    if p.verse is not None and p.verse < p.du:
        sortie.append(_c("avertit", "verse_sous_le_du", t(
            f"Versé {_f(p.verse)}, dû {_f(p.du)} : le salarié garde droit au dû, soit {_f(p.du - p.verse)} de plus.",
            f"Paid {_f(p.verse)}, due {_f(p.du)}: the employee remains entitled to the amount due, i.e. "
            f"{_f(p.du - p.verse)} more.")))
    elif p.verse is not None and p.verse > p.du:
        sortie.append(_c("informe", "verse_au_dela_du_du", t(
            f"Versé {_f(p.verse)} pour {_f(p.du)} dus : l'entreprise a donné plus que son régime, c'est son droit.",
            f"Paid {_f(p.verse)} for {_f(p.du)} due: the company gave more than its plan, which is its right.")))
    if p.part_fonds_demandee is not None and p.verse is not None and p.part_fonds_demandee > p.verse:
        sortie.append(_c("avertit", "fonds_demande_au_dela_du_verse",
                         t("La part demandée au fonds dépasse ce qui a été versé au salarié.",
                           "The share claimed from the fund exceeds what was paid to the employee.")))
    if p.part_fonds_payee is not None and p.part_fonds_demandee is not None and p.part_fonds_payee > p.part_fonds_demandee:
        sortie.append(_c("avertit", "fonds_paye_au_dela_demande", t("Le fonds a payé plus que la part demandée.",
                                                                     "The fund paid more than the share claimed.")))
    posterieurs = [d for d, matricules in presences_ if d > p.date_depart and p.matricule in matricules]
    if posterieurs:
        sortie.append(_c("avertit", "encore_present", t(
            f"Le matricule {p.matricule} figure encore dans le fichier du "
            f"personnel arrêté au {max(posterieurs):%d/%m/%Y}, après ce départ : vérifier.",
            f"Staff number {p.matricule} still appears in the staff file as at {max(posterieurs):%d/%m/%Y}, after "
            "this departure: check.")))
    return sortie


def _c(niveau: str, code: str, message: str) -> dict:
    return {"niveau": niveau, "code": code, "message": message}


def _f(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " F"


def totaux(ps: list[Prestation]) -> dict:
    return {"nombre": len(ps), "retraites": sum(p.motif == "retraite" for p in ps),
            "autres_departs": sum(p.motif != "retraite" for p in ps), "du": sum(p.du for p in ps),
            "verse": sum(p.verse or 0 for p in ps), "part_fonds_payee": sum(p.part_fonds_payee or 0 for p in ps)}


def en_clair(session: Session, p: Prestation, presences_: list | None = None) -> dict:
    presences_ = presences(session) if presences_ is None else presences_
    return {
        "id": str(p.id), "matricule": p.matricule, "categorie": p.categorie, "motif": p.motif,
        "date_naissance": _iso(p.date_naissance), "date_embauche": _iso(p.date_embauche),
        "date_depart": _iso(p.date_depart), "salaire_mensuel_reference": p.salaire_mensuel_reference,
        "du": p.du, "calcul": _calcul_en_clair(p.calcul), "verse": p.verse, "part_fonds_demandee": p.part_fonds_demandee,
        "part_fonds_payee": p.part_fonds_payee, "payee_le": _iso(p.payee_le), "soldee": p.soldee,
        "origine": p.origine, "import_id": str(p.import_id) if p.import_id else None, "note": p.note,
        "remplace_id": str(p.remplace_id) if p.remplace_id else None, "annulation": p.annulation,
        "motif_correction": p.motif_correction,
        "service": contrats.service_a_la_date(session, p.date_depart).service,
        "constats": constats(p, presences_),
    }


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


# --- L'historique, par tableur --------------------------------------------------------------

def importer(session: Session, org: Organisation, auteur: uuid.UUID, *, contenu: bytes, nom_fichier: str,
             convention_code: str | None, enregistrer_: bool) -> dict:
    """Lit le tableur, calcule chaque dû ; enregistre tout ou rien (un seul bloquant arrête le lot)."""
    lecture = lire_departs(contenu, nom_fichier)
    presences_ = presences(session)
    deja = {(p.matricule, p.date_depart) for p in actives(session)}
    apercu, saisies = [], []
    for l in lecture.lignes:
        if l.bloquee:
            continue
        s = _saisie_de(l, convention_code)
        if (s.matricule, s.date_depart) in deja:
            lecture.anomalies.append(Anomalie("bloquant", "deja_enregistree", f"Le départ du matricule {s.matricule} "
                                              f"au {s.date_depart:%d/%m/%Y} est déjà enregistré.", ligne=l.numero))
            continue
        try:
            du, calcul = calculer(session, s)
        except ErreurMetier as e:
            lecture.anomalies.append(Anomalie("bloquant", e.code, e.message, ligne=l.numero))
            continue
        ligne = _vue(s, du)
        apercu.append({"numero": l.numero, **{k: (v.isoformat() if isinstance(v, date) else v)
                                              for k, v in asdict(ligne).items()},
                       "calcul": _calcul_en_clair(calcul), "constats": constats(ligne, presences_)})
        saisies.append(s)

    bloquants = [a for a in lecture.anomalies if a.niveau == "bloquant"]
    reponse = {"lignes": apercu, "anomalies": anomalies_en_clair([asdict(a) for a in lecture.anomalies]),
               "colonnes": lecture.colonnes, "colonnes_ignorees": lecture.colonnes_ignorees, "enregistrees": 0}
    if not enregistrer_:
        return reponse
    if bloquants:
        raise ErreurMetier("import_bloque", t(f"{len(bloquants)} point(s) bloquant(s) : rien n'est enregistré.",
                                              f"{len(bloquants)} blocking issue(s): nothing is saved."), 422,
                           {"anomalies": reponse["anomalies"]})
    lot = uuid.uuid4()
    for s in saisies:
        enregistrer(session, org, auteur, s, origine="import", import_id=lot)
    journaliser(session, org.id, auteur, "prestations.importees", lot, {"nom_fichier": nom_fichier,
                                                                         "nombre": len(saisies)})
    return {**reponse, "enregistrees": len(saisies), "import_id": str(lot)}


@dataclass(frozen=True)
class _Apercu:
    matricule: str
    motif: str
    date_embauche: date
    date_depart: date
    salaire_mensuel_reference: int
    verse: int | None
    part_fonds_demandee: int | None
    part_fonds_payee: int | None
    payee_le: date | None
    categorie: str | None
    du: int


def _saisie_de(l: LigneDepart, convention_code: str | None) -> Saisie:
    return Saisie(matricule=l.matricule, motif=l.motif, date_embauche=l.date_embauche, date_depart=l.date_depart,
                  salaire_mensuel_reference=l.salaire_mensuel_reference, categorie=l.categorie,
                  date_naissance=l.date_naissance, verse=l.verse, part_fonds_payee=l.part_fonds_payee,
                  payee_le=l.payee_le, soldee=True, convention_code=convention_code)
