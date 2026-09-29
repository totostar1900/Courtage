import { Link } from "react-router-dom";

import { useCabinet } from "../cabinet";
import { t } from "../i18n";

/** La première page d'un visiteur : ce que fait le service, ce qu'il coûte, qui l'exploite, et par où entrer. */
export default function Vitrine() {
  const cabinet = useCabinet();
  const etapes = [
    { titre: t("Essayer, sans compte", "Try it, no account"),
      texte: t("Déposez votre fichier du personnel, décrivez votre régime et votre fonds : l'étude se calcule à l'écran. Rien n'est gardé.",
               "Upload your staff file, describe your plan and your fund: the study is calculated on screen. Nothing is kept.") },
    { titre: t("S'inscrire", "Sign up"),
      texte: t("Téléphone et courriel vérifiés, numéro RCCM de l'entreprise. Le courtier confirme sous deux jours ouvrés ; en attendant, vous travaillez.",
               "Phone and email verified, the company's RCCM number. The broker confirms within two working days; meanwhile, you can work.") },
    { titre: t("Mandater le courtier", "Appoint the broker"),
      texte: t("Un mandat lu et signé en ligne, scellé. Le courtier consulte les assureurs, compare leurs offres et vous recommande la plus adaptée ; vous choisissez.",
               "A mandate read and signed online, sealed. The broker consults insurers, compares their offers and recommends the best fit; you choose.") },
    { titre: t("Suivre le contrat", "Follow the contract"),
      texte: t("Départs, dossiers de prise en charge avec leurs délais, évaluation de chaque année : tout reste au même endroit, tracé.",
               "Departures, benefit claim files with their deadlines, each year's valuation: everything stays in one place, recorded.") },
  ];
  const apports = [
    [t("Un chiffrage de votre engagement", "A costing of your liability"),
     t("La dette IFC selon votre convention et votre régime, l'échéancier des départs, les hypothèses dites et datées. Le rapport émis est scellé et vérifiable.",
       "The end-of-service liability under your collective agreement and your plan, the schedule of departures, stated and dated assumptions. The issued report is sealed and verifiable.")],
    [t("Une mise en concurrence tracée", "A recorded tender"),
     t("Un cahier des charges anonymisé, les offres confrontées à vos conditions et classées par leur coût, une recommandation motivée.",
       "Anonymised tender specifications, offers checked against your requirements and ranked by cost, a reasoned recommendation.")],
    [t("Des départs pris en charge", "Departures handled"),
     t("Le montant dû recalculé à chaque départ, le dossier transmis à l'assureur et suivi jusqu'au paiement.",
       "The amount due recalculated at each departure, the claim file sent to the insurer and followed until payment.")],
  ];
  const questions = [
    [t("Combien coûte l'accompagnement ?", "What does the support cost?"),
     t("Rien pour l'entreprise. Le courtier est rémunéré par la commission de l'assureur retenu ; le mandat le dit, et son taux est communiqué sur demande.",
       "Nothing for the company. The broker is paid by the commission of the insurer chosen; the mandate says so, and its rate is available on request.")],
    [t("Mes salariés sont-ils nommés ?", "Are my employees named?"),
     t("Non. Le fichier du personnel se lit par matricule, dates et salaires : aucun nom n'est lu ni gardé. Une identité n'apparaît que dans un dossier de prise en charge, sous mandat.",
       "No. The staff file is read by employee number, dates and salaries: no name is read or kept. An identity appears only in a benefit claim file, under mandate.")],
    [t("Qui voit nos données ?", "Who sees our data?"),
     t("Votre équipe, selon les droits que vous donnez, et le conseiller que le courtier désigne. Un assureur ne reçoit qu'un cahier des charges anonymisé.",
       "Your team, with the rights you give, and the adviser the broker assigns. An insurer receives only anonymised tender specifications.")],
    [t("Quels pays ?", "Which countries?"),
     t("Les six pays de la CEMAC, dont la plateforme connaît les conventions collectives.",
       "The six CEMAC countries, whose collective agreements the platform knows.")],
  ];
  return (
    <div className="vitrine">
      <section className="vitrine-une">
        <h1>{t("Vos indemnités de fin de carrière, chiffrées puis placées", "Your end-of-service benefits, costed then placed")}</h1>
        <p className="vitrine-chapeau">{t(
          "Un courtier en ligne pour les entreprises de la CEMAC : il mesure votre engagement envers vos salariés, met les assureurs en concurrence pour le financer, et suit chaque départ jusqu'au paiement.",
          "An online broker for CEMAC companies: it measures your commitment to your employees, puts insurers in competition to fund it, and follows each departure until payment.")}</p>
        <div className="actions">
          <Link to="/essai" className="bouton principal">{t("Essayer sans compte", "Try without an account")}</Link>
          <Link to="/inscription" className="bouton">{t("S'inscrire", "Sign up")}</Link>
          <Link to="/connexion" className="lien-discret">{t("Déjà un compte ? Se connecter", "Already have an account? Sign in")}</Link>
        </div>
        <p className="vitrine-gratuit"><strong>{t("Gratuit pour l'entreprise.", "Free for the company.")}</strong>{" "}
          {t("Le courtier est rémunéré par l'assureur que vous retenez.", "The broker is paid by the insurer you choose.")}</p>
      </section>

      <section aria-labelledby="vitrine-etapes">
        <h2 id="vitrine-etapes">{t("Comment ça marche", "How it works")}</h2>
        <ol className="vitrine-etapes">
          {etapes.map((e, i) => (
            <li key={i} className="carte"><span className="vitrine-numero">{i + 1}</span>
              <h3>{e.titre}</h3><p>{e.texte}</p></li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="vitrine-apports">
        <h2 id="vitrine-apports">{t("Ce que vous obtenez", "What you get")}</h2>
        <div className="grille g3">
          {apports.map(([titre, texte]) => <div key={titre} className="carte"><h3>{titre}</h3><p>{texte}</p></div>)}
        </div>
      </section>

      <section aria-labelledby="vitrine-questions">
        <h2 id="vitrine-questions">{t("Questions fréquentes", "Frequently asked questions")}</h2>
        <div className="vitrine-questions">
          {questions.map(([q, r]) => <details key={q} className="carte"><summary>{q}</summary><p>{r}</p></details>)}
        </div>
        <p className="discret">{t("Pour aller plus loin : ", "To go further: ")}<Link to="/guide">{t("le guide", "the guide")}</Link>.</p>
      </section>

      <section aria-labelledby="vitrine-cabinet" className="carte vitrine-cabinet">
        <h2 id="vitrine-cabinet" style={{ marginTop: 0 }}>{t("Le cabinet", "The brokerage firm")}</h2>
        {cabinet ? (
          <div className="lignes-offre">
            <div><span>{t("Raison sociale", "Company name")}</span><strong>{cabinet.nom}</strong></div>
            <div><span>{t("Agrément de courtier", "Broker's licence")}</span><span>{cabinet.agrement}</span></div>
            <div><span>{t("Siège", "Registered office")}</span><span>{cabinet.adresse}</span></div>
            <div><span>{t("Contact", "Contact")}</span><span>{cabinet.courriel} · {cabinet.telephone}</span></div>
          </div>
        ) : <p className="discret">{t("Chargement…", "Loading…")}</p>}
      </section>
    </div>
  );
}
