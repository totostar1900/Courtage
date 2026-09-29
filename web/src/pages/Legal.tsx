import { Link } from "react-router-dom";

import { useCabinet, type Cabinet } from "../cabinet";
import { t } from "../i18n";

/** Les trois pages légales, publiques. Un texte changé change `CONDITIONS_VERSION` (api/src/courtage/cabinet.py) :
 *  l'inscription enregistre la version acceptée. Le français fait foi. */

type Paragraphe = [string, string];
interface Section { titre: Paragraphe; paragraphes: (Paragraphe | ((c: Cabinet) => Paragraphe))[] }

function Page({ titre, sections, version }: { titre: string; sections: Section[]; version?: boolean }) {
  const c = useCabinet();
  return (
    <article className="legal">
      <h1>{titre}</h1>
      {version && c && <p className="discret">{t("Version", "Version")} {c.conditions_version}</p>}
      <p className="discret">{t("Traduction à titre d'information : le texte français fait foi.",
        "Translation for information: the French text prevails.")}</p>
      {!c ? <p className="discret">{t("Chargement…", "Loading…")}</p> : sections.map((s, i) => (
        <section key={i}>
          <h2>{t(...s.titre)}</h2>
          {s.paragraphes.map((p, j) => <p key={j}>{t(...(typeof p === "function" ? p(c) : p))}</p>)}
        </section>
      ))}
      <nav className="legal-liens" aria-label={t("Autres pages légales", "Other legal pages")}>
        <Link to="/mentions-legales">{t("Mentions légales", "Legal notice")}</Link>
        <Link to="/conditions">{t("Conditions d'utilisation", "Terms of use")}</Link>
        <Link to="/confidentialite">{t("Confidentialité", "Privacy")}</Link>
      </nav>
    </article>
  );
}

export function MentionsLegales() {
  return <Page titre={t("Mentions légales", "Legal notice")} sections={[
    { titre: ["Éditeur", "Publisher"], paragraphes: [
      (c) => [`La plateforme est éditée et exploitée par ${c.nom}, cabinet de courtage d'assurance, RCCM ${c.rccm}, agrément ${c.agrement}, dont le siège est ${c.adresse}.`,
              `The platform is published and operated by ${c.nom}, an insurance brokerage firm, RCCM ${c.rccm}, licence ${c.agrement}, with its registered office at ${c.adresse}.`],
      (c) => [`Contact : ${c.courriel} · ${c.telephone}.`, `Contact: ${c.courriel} · ${c.telephone}.`] ] },
    { titre: ["Activité", "Business"], paragraphes: [
      ["Le cabinet exerce une activité d'intermédiaire en assurance. Il conseille les entreprises, consulte les assureurs pour leur compte sous mandat, et suit l'exécution des contrats. Il n'est pas un assureur : il ne porte aucun risque et ne reçoit pas les primes.",
       "The firm acts as an insurance intermediary. It advises companies, consults insurers on their behalf under mandate, and follows how contracts are carried out. It is not an insurer: it carries no risk and does not receive premiums."] ] },
    { titre: ["Hébergement", "Hosting"], paragraphes: [
      (c) => [`Le site et ses données sont hébergés par ${c.hebergeur}.`, `The site and its data are hosted by ${c.hebergeur}.`] ] },
    { titre: ["Documents scellés", "Sealed documents"], paragraphes: [
      ["Chaque rapport, mandat ou fiche émis par la plateforme porte un numéro et un sceau. Son authenticité se vérifie par ce numéro sur la page « Vérifier un document ».",
       "Each report, mandate or sheet issued by the platform carries a number and a seal. Its authenticity can be checked with that number on the “Verify a document” page."] ] },
  ]} />;
}

export function Conditions() {
  return <Page version titre={t("Conditions d'utilisation", "Terms of use")} sections={[
    { titre: ["1. Objet", "1. Purpose"], paragraphes: [
      (c) => [`Ces conditions régissent l'usage de la plateforme exploitée par ${c.nom} (« le cabinet ») par les entreprises et leurs équipes (« le client »). La plateforme sert à mesurer l'engagement d'indemnités de fin de carrière, à préparer et suivre sa couverture par un assureur, et à échanger avec le cabinet.`,
              `These terms govern the use of the platform operated by ${c.nom} (“the firm”) by companies and their teams (“the client”). The platform is used to measure the end-of-service benefit liability, to prepare and follow its cover by an insurer, and to communicate with the firm.`] ] },
    { titre: ["2. Comptes et accès", "2. Accounts and access"], paragraphes: [
      ["Un compte est personnel. On s'y connecte par un code à usage unique envoyé au téléphone vérifié ; ce code ne se communique à personne. L'administrateur de l'entreprise invite ses collègues et fixe leurs droits.",
       "An account is personal. You sign in with a one-time code sent to the verified phone; this code must not be shared with anyone. The company's administrator invites colleagues and sets their rights."],
      ["Sans compte, l'essai calcule à l'écran et ne garde rien. Inscrit, le client travaille dans son dossier ; ce qui sort de la plateforme (documents scellés, exports, invitations) s'ouvre quand le cabinet a confirmé l'inscription, et ce qui touche aux assureurs s'ouvre sous mandat.",
       "Without an account, the trial calculates on screen and keeps nothing. Once signed up, the client works in their file; what leaves the platform (sealed documents, exports, invitations) opens once the firm has confirmed the sign-up, and what involves insurers opens under mandate."] ] },
    { titre: ["3. Gratuité pour le client", "3. Free for the client"], paragraphes: [
      ["L'usage de la plateforme et l'accompagnement du cabinet ne sont pas facturés au client. Le cabinet est rémunéré par la commission versée par l'assureur retenu, selon les termes du mandat de courtage ; son taux est communiqué sur demande.",
       "Using the platform and the firm's support are not charged to the client. The firm is paid by the commission paid by the insurer chosen, under the terms of the brokerage mandate; its rate is available on request."] ] },
    { titre: ["4. Ce que la plateforme ne fait pas", "4. What the platform does not do"], paragraphes: [
      ["Elle ne couvre aucun risque, ne reçoit ni ne verse aucune somme, et n'engage pas un assureur : seul le contrat signé avec l'assureur le fait.",
       "It covers no risk, neither receives nor pays any money, and does not commit an insurer: only the contract signed with the insurer does."],
      ["Une étude est une estimation, faite à partir des données déposées par le client et d'hypothèses que le rapport énonce et date. Elle éclaire une décision ; elle ne la prend pas.",
       "A study is an estimate, based on the data uploaded by the client and on assumptions that the report states and dates. It informs a decision; it does not make it."] ] },
    { titre: ["5. Données déposées par le client", "5. Data uploaded by the client"], paragraphes: [
      ["Le client répond de l'exactitude des données qu'il dépose et du droit de les communiquer. Le fichier du personnel ne doit porter aucun nom : la plateforme lit matricules, dates et salaires. Les données restent celles du client ; la politique de confidentialité dit ce qui en est fait.",
       "The client is responsible for the accuracy of the data they upload and for the right to share it. The staff file must carry no names: the platform reads employee numbers, dates and salaries. The data remain the client's; the privacy policy says what is done with them."] ] },
    { titre: ["6. Mandat de courtage", "6. Brokerage mandate"], paragraphes: [
      ["Le mandat est proposé par le cabinet et signé en ligne par une personne qui a qualité pour engager l'entreprise : son représentant légal, ou une personne qui a reçu pouvoir et en dépose la délégation. Le mandat signé est scellé et ne se modifie plus.",
       "The mandate is proposed by the firm and signed online by a person entitled to commit the company: its legal representative, or a person who has received authority and uploads the delegation. The signed mandate is sealed and can no longer be changed."] ] },
    { titre: ["7. Suspension et effacement", "7. Suspension and erasure"], paragraphes: [
      ["Une inscription que le cabinet ne confirme pas dans les 30 jours est effacée, ainsi que ce qu'elle contient. Le client peut effacer lui-même une inscription non confirmée, ou demander la clôture d'un dossier. Le cabinet peut suspendre un accès utilisé contrairement à ces conditions, après en avoir informé le client.",
       "A sign-up that the firm does not confirm within 30 days is erased, with everything it contains. The client can erase an unconfirmed sign-up themselves, or ask for a file to be closed. The firm may suspend access used contrary to these terms, after informing the client."] ] },
    { titre: ["8. Responsabilité", "8. Liability"], paragraphes: [
      ["Le cabinet répond de son devoir de conseil dans les termes du mandat. La plateforme est fournie avec soin ; une interruption de service ou une erreur de données déposées ne peut être reprochée au cabinet au-delà de ce que prévoient le mandat et les règles applicables à l'intermédiation en assurance.",
       "The firm is accountable for its duty to advise under the terms of the mandate. The platform is provided with care; a service interruption or an error in uploaded data cannot be held against the firm beyond what the mandate and the rules applicable to insurance intermediation provide."] ] },
    { titre: ["9. Modifications, droit applicable", "9. Changes, governing law"], paragraphes: [
      ["Une nouvelle version de ces conditions est signalée à l'utilisateur, qui l'accepte pour continuer. Un différend est d'abord soumis au cabinet en vue d'une solution amiable ; à défaut, il relève du droit et des juridictions du siège du cabinet.",
       "A new version of these terms is shown to the user, who accepts it to continue. A dispute is first submitted to the firm for an amicable solution; failing that, it falls under the law and courts of the firm's registered office."] ] },
  ]} />;
}

export function Confidentialite() {
  return <Page version titre={t("Politique de confidentialité", "Privacy policy")} sections={[
    { titre: ["Responsable du traitement", "Data controller"], paragraphes: [
      (c) => [`${c.nom}, ${c.adresse}. Pour toute question ou demande sur vos données : ${c.courriel}.`,
              `${c.nom}, ${c.adresse}. For any question or request about your data: ${c.courriel}.`] ] },
    { titre: ["Ce qui est traité", "What is processed"], paragraphes: [
      ["Votre compte : nom affiché, fonction, téléphone et courriel vérifiés, les appareils connectés. L'entreprise : raison sociale, RCCM et son justificatif, taille, adresse. Le personnel : matricules, dates de naissance et d'embauche, salaires, catégories — jamais de nom.",
       "Your account: display name, job title, verified phone and email, signed-in devices. The company: name, RCCM and its supporting document, size, address. The staff: employee numbers, dates of birth and hire, salaries, categories — never a name."],
      ["Sous mandat seulement, un dossier de prise en charge porte l'identité du bénéficiaire et ses pièces, le temps de le traiter.",
       "Under mandate only, a benefit claim file carries the beneficiary's identity and documents, for the time it takes to handle it."],
      ["Une demande de rappel laissée sur la vitrine : votre nom, votre entreprise, votre téléphone, votre courriel si vous le donnez, le créneau et votre message, avec votre accord pour être rappelé.",
       "A callback request left on the home page: your name, your company, your phone, your email if you give it, the time slot and your message, with your consent to be called back."] ] },
    { titre: ["Pourquoi", "Why"], paragraphes: [
      ["Pour vous identifier et sécuriser l'accès ; pour calculer vos études et en sceller les résultats ; pour exécuter le mandat de courtage (consultation des assureurs, suivi du contrat et des prises en charge) ; pour vous prévenir d'un événement qui vous attend.",
       "To identify you and secure access; to calculate your studies and seal their results; to carry out the brokerage mandate (consulting insurers, following the contract and the claims); to notify you of an event waiting for you."] ] },
    { titre: ["Qui les lit", "Who reads them"], paragraphes: [
      ["Votre équipe, selon les droits donnés par votre administrateur, et le conseiller que le cabinet désigne. Un assureur ne reçoit qu'un cahier des charges anonymisé et, sous mandat, le dossier de prise en charge qui le concerne.",
       "Your team, with the rights set by your administrator, and the adviser the firm assigns. An insurer receives only anonymised tender specifications and, under mandate, the claim file that concerns it."],
      ["Des prestataires techniques : l'hébergeur, le fournisseur d'envoi des SMS et des courriels. La lecture d'un texte de régime par l'intelligence artificielle Claude (Anthropic) n'a lieu qu'avec votre accord explicite, à chaque fois ; le document n'est pas gardé, seule la proposition relue l'est.",
       "Technical providers: the host, the SMS and email sending provider. Having a plan text read by the Claude artificial intelligence (Anthropic) happens only with your explicit consent, each time; the document is not kept, only the reviewed proposal is."] ] },
    { titre: ["Combien de temps", "How long"], paragraphes: [
      ["Une demande de rappel : douze mois. Une inscription non confirmée : 30 jours. Un dossier de prise en charge : effacé douze mois après le paiement. Un code de vérification : 10 minutes. Le journal des actes (qui a fait quoi, quand, sans donnée du personnel) et les documents scellés : conservés, car ils prouvent ce qui a été fait. Le reste : tant que le dossier est ouvert, puis selon les obligations de conservation du cabinet.",
       "A callback request: twelve months. An unconfirmed sign-up: 30 days. A benefit claim file: erased twelve months after payment. A verification code: 10 minutes. The log of actions (who did what, when, with no staff data) and sealed documents: kept, because they prove what was done. The rest: while the file is open, then according to the firm's retention obligations."] ] },
    { titre: ["Témoins et stockage local", "Cookies and local storage"], paragraphes: [
      ["Un seul témoin, celui de la session, nécessaire à la connexion. Le navigateur garde aussi vos préférences (langue, visite guidée, dernière page). Aucun témoin de mesure d'audience ni de publicité.",
       "A single cookie, the session cookie, needed to sign in. The browser also keeps your preferences (language, guided tour, last page). No audience-measurement or advertising cookie."],
      ["Pour savoir combien de visiteurs viennent, d'où, et jusqu'où ils vont, la plateforme compte les visites de ses pages publiques : un compteur par jour et par page, avec la catégorie du site d'origine (moteur de recherche, réseau social…), sans témoin, sans identifiant, sans adresse IP et sans prestataire tiers. Rien n'est envoyé si votre navigateur demande à ne pas être suivi.",
       "To know how many visitors come, from where, and how far they go, the platform counts visits to its public pages: one counter per day and per page, with the category of the referring site (search engine, social network…), with no cookie, no identifier, no IP address and no third party. Nothing is sent if your browser asks not to be tracked."] ] },
    { titre: ["Vos droits", "Your rights"], paragraphes: [
      (c) => [`Vous pouvez demander l'accès à vos données, leur rectification, leur effacement ou vous opposer à un traitement, dans les conditions prévues par les textes de protection des données personnelles applicables. Écrivez à ${c.courriel}. Vous pouvez aussi saisir l'autorité de protection des données de votre pays lorsqu'elle existe.`,
              `You can ask to access, correct or erase your data, or object to processing, under the conditions set by the applicable personal data protection texts. Write to ${c.courriel}. You may also refer the matter to your country's data protection authority where one exists.`] ] },
    { titre: ["Sécurité", "Security"], paragraphes: [
      ["Connexion par code à usage unique, sessions révocables depuis votre profil, séparation des données de chaque entreprise dans la base, documents scellés, journal des actes.",
       "Sign-in by one-time code, sessions you can revoke from your profile, separation of each company's data in the database, sealed documents, log of actions."] ] },
  ]} />;
}
