"""Envoi de messages courts (SMS, WhatsApp) : le seul point de contact avec un fournisseur.

La plateforme n'envoie aujourd'hui qu'une chose : le code de connexion. Le
fournisseur est interchangeable (Twilio ici ; Africa's Talking, Orange ou un
agrégateur local se branchent de la même façon). En développement,
`ExpediteurJournal` écrit le message dans le journal au lieu de l'envoyer.
"""
import logging
from dataclasses import dataclass, field

journal = logging.getLogger("courtage.messagerie")


@dataclass(frozen=True)
class Message:
    telephone: str
    texte: str


class ErreurEnvoi(Exception):
    pass


@dataclass
class ExpediteurJournal:
    """Développement et tests : garde les messages et les écrit dans le journal."""
    canal: str = "journal"
    envoyes: list[Message] = field(default_factory=list)

    def envoyer(self, telephone: str, texte: str) -> None:
        self.envoyes.append(Message(telephone, texte))
        journal.warning("[développement] message pour %s : %s", telephone, texte)


@dataclass
class ExpediteurTwilio:
    compte: str
    jeton: str
    emetteur: str                 # numéro ou identifiant d'émetteur ; « whatsapp:+… » pour WhatsApp
    canal: str = "sms"

    def envoyer(self, telephone: str, texte: str) -> None:
        import httpx
        destinataire = f"whatsapp:{telephone}" if self.canal == "whatsapp" else telephone
        r = httpx.post(f"https://api.twilio.com/2010-04-01/Accounts/{self.compte}/Messages.json",
                       data={"From": self.emetteur, "To": destinataire, "Body": texte},
                       auth=(self.compte, self.jeton), timeout=10)
        if r.status_code >= 300:
            raise ErreurEnvoi(f"Twilio a refusé l'envoi ({r.status_code})")


def expediteur_depuis_environnement(env) -> object | None:
    """TWILIO_COMPTE, TWILIO_JETON, TWILIO_EMETTEUR et TWILIO_CANAL (sms | whatsapp)."""
    if env.get("TWILIO_COMPTE") and env.get("TWILIO_JETON") and env.get("TWILIO_EMETTEUR"):
        return ExpediteurTwilio(env["TWILIO_COMPTE"], env["TWILIO_JETON"], env["TWILIO_EMETTEUR"],
                                env.get("TWILIO_CANAL", "sms"))
    return None


# --- Courriel ---------------------------------------------------------------------
# Le code de vérification d'une adresse à l'inscription. Tout fournisseur SMTP convient (celui de l'hébergeur,
# Brevo, Mailgun, SES…) : `COURTAGE_SMTP_URL` = smtp[s]://utilisateur:mot-de-passe@hôte:port, et
# `COURTAGE_COURRIEL_EXPEDITEUR` = l'adresse d'envoi.

@dataclass
class CourrielJournal:
    """Développement et tests : garde les courriels et les écrit dans le journal."""
    envoyes: list[Message] = field(default_factory=list)

    def envoyer(self, adresse: str, sujet: str, texte: str) -> None:
        self.envoyes.append(Message(adresse, texte))
        journal.warning("[développement] courriel pour %s : %s — %s", adresse, sujet, texte)


@dataclass
class CourrielSMTP:
    url: str
    expediteur: str

    def envoyer(self, adresse: str, sujet: str, texte: str) -> None:
        import smtplib
        from email.message import EmailMessage
        from urllib.parse import unquote, urlparse
        u = urlparse(self.url)
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = self.expediteur, adresse, sujet
        m.set_content(texte)
        classe = smtplib.SMTP_SSL if u.scheme == "smtps" else smtplib.SMTP
        try:
            with classe(u.hostname, u.port or (465 if u.scheme == "smtps" else 587), timeout=10) as s:
                if u.scheme != "smtps":
                    s.starttls()
                if u.username:
                    s.login(unquote(u.username), unquote(u.password or ""))
                s.send_message(m)
        except (OSError, smtplib.SMTPException) as e:
            raise ErreurEnvoi(f"Envoi du courriel impossible ({type(e).__name__})") from None


def courriel_depuis_environnement(env) -> object | None:
    if env.get("COURTAGE_SMTP_URL") and env.get("COURTAGE_COURRIEL_EXPEDITEUR"):
        return CourrielSMTP(env["COURTAGE_SMTP_URL"], env["COURTAGE_COURRIEL_EXPEDITEUR"])
    return None
