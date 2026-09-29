import { Link } from "react-router-dom";

import { useCabinet } from "../cabinet";
import { useMesure } from "../mesure";
import EtreRappele from "../composants/EtreRappele";
import { t } from "../i18n";

/** La première page d'un visiteur : ce que fait le service, ce qu'il coûte, qui l'exploite, et par où entrer. */
export default function Vitrine() {
  const cabinet = useCabinet();
  useMesure("vitrine");
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
     t("Un cahier des charges anonymisé, les offres confrontées à vos conditions et classées par leur rendement net, une recommandation motivée.",
       "Anonymised tender specifications, offers checked against your requirements and ranked by net return, a reasoned recommendation.")],
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
  const icones = [
    "M3 3v18h18M7 15l4-4 3 3 5-6",                                          // un chiffrage
    "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",                    // une mise en concurrence
    "M20 7 9 18l-5-5",                                                       // des départs pris en charge
  ];
  return (
    <div className="vitrine">
      <section className="vitrine-une">
        <div className="vitrine-une-texte">
          <p className="surtitre surtitre-clair">{t("Courtage IFC · CEMAC", "End-of-service benefit brokerage · CEMAC")}</p>
          <h1>{t("Vos indemnités de fin de carrière, chiffrées puis placées", "Your end-of-service benefits, costed then placed")}</h1>
          <p className="vitrine-chapeau">{t(
            "Un courtier en ligne pour les entreprises de la CEMAC : il mesure votre engagement envers vos salariés, met les assureurs en concurrence pour le financer, et suit chaque départ jusqu'au paiement.",
            "An online broker for CEMAC companies: it measures your commitment to your employees, puts insurers in competition to fund it, and follows each departure until payment.")}</p>
          <div className="actions">
            <Link to="/essai" className="bouton principal bouton-grand">{t("Essayer sans compte", "Try without an account")}</Link>
            <Link to="/inscription" className="bouton bouton-grand bouton-clair">{t("S'inscrire", "Sign up")}</Link>
          </div>
          <p className="vitrine-liens"><a href="#vitrine-rappel">{t("Être rappelé", "Be called back")}</a>
            <Link to="/connexion">{t("Déjà un compte ? Se connecter", "Already have an account? Sign in")}</Link></p>
          <ul className="vitrine-assurances">
            <li className="vitrine-gratuit"><strong>{t("Gratuit pour l'entreprise.", "Free for the company.")}</strong>{" "}
              {t("Le courtier est rémunéré par l'assureur que vous retenez.", "The broker is paid by the insurer you choose.")}</li>
            <li>{t("Aucun nom de salarié : un matricule suffit.", "No employee names: a staff number is enough.")}</li>
            <li>{t("Des rapports scellés, vérifiables par leur numéro.", "Sealed reports, verifiable by their number.")}</li>
          </ul>
        </div>
        <div className="vitrine-une-visuel" aria-hidden="true">
          <div className="apercu-carte">
            <div className="apercu-tete"><span>{t("Votre engagement au 31/12", "Your liability at 31/12")}</span><span className="etat bien">{t("Scellé", "Sealed")}</span></div>
            <div className="apercu-chiffre">135,8 M F</div>
            <div className="apercu-barres">{[38, 12, 30, 6, 64, 8, 22, 46, 18, 14].map((h, i) => <span key={i} style={{ height: `${h}px` }} />)}</div>
            <div className="apercu-ligne"><span>{t("Offres reçues", "Offers received")}</span><strong>3</strong></div>
            <div className="apercu-ligne"><span>{t("Meilleur rendement net", "Best net return")}</span><strong>3,12 %</strong></div>
          </div>
        </div>
      </section>

      <section aria-labelledby="vitrine-etapes" className="vitrine-bloc">
        <p className="surtitre">{t("Le parcours", "The journey")}</p>
        <h2 id="vitrine-etapes">{t("Comment ça marche", "How it works")}</h2>
        <ol className="frise frise-4 vitrine-frise">
          {etapes.map((e, i) => (
            <li key={i}><span className="frise-num">{i + 1}</span><strong>{e.titre}</strong><span>{e.texte}</span></li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="vitrine-apports" className="vitrine-bloc">
        <p className="surtitre">{t("Le service", "The service")}</p>
        <h2 id="vitrine-apports">{t("Ce que vous obtenez", "What you get")}</h2>
        <div className="grille g3">
          {apports.map(([titre, texte], i) => (
            <div key={titre} className="carte carte-icone">
              <span className="pastille-icone" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={icones[i]} /></svg>
              </span>
              <h3>{titre}</h3><p>{texte}</p>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="vitrine-questions" className="vitrine-bloc">
        <p className="surtitre">{t("Questions", "Questions")}</p>
        <h2 id="vitrine-questions">{t("Questions fréquentes", "Frequently asked questions")}</h2>
        <div className="vitrine-questions">
          {questions.map(([q, r]) => (
            <details key={q} className="pli"><summary><span>{q}</span></summary><div className="pli-corps"><p>{r}</p></div></details>
          ))}
        </div>
        <p className="discret">{t("Pour aller plus loin : ", "To go further: ")}
          <Link to="/ifc">{t("les indemnités de fin de carrière", "end-of-service benefits")}</Link>{" · "}
          <Link to="/ifc/cameroun">{t("les IFC au Cameroun", "end-of-service benefits in Cameroon")}</Link>{" · "}
          <Link to="/guide">{t("le guide", "the guide")}</Link>.</p>
      </section>

      <div className="vitrine-bas">
        <section aria-labelledby="vitrine-rappel" className="carte">
          <p className="surtitre">{t("Un conseiller", "An adviser")}</p>
          <h2 id="vitrine-rappel" style={{ marginTop: 0 }}>{t("Parler à un conseiller", "Talk to an adviser")}</h2>
          <p>{t("Vous préférez en parler avant d'essayer ? Laissez votre numéro : le courtier vous rappelle, au créneau que vous choisissez.",
            "Rather talk it through before trying? Leave your number: the broker calls you back at the time you choose.")}</p>
          <EtreRappele />
        </section>

        <section aria-labelledby="vitrine-cabinet" className="carte vitrine-cabinet">
          <p className="surtitre">{t("Qui nous sommes", "Who we are")}</p>
          <h2 id="vitrine-cabinet" style={{ marginTop: 0 }}>{t("Le cabinet", "The brokerage firm")}</h2>
          {cabinet ? (
            <dl className="fiche-cabinet">
              <dt>{t("Raison sociale", "Company name")}</dt><dd><strong>{cabinet.nom}</strong></dd>
              <dt>{t("Agrément de courtier", "Broker's licence")}</dt><dd>{cabinet.agrement}</dd>
              <dt>{t("Siège", "Registered office")}</dt><dd>{cabinet.adresse}</dd>
              <dt>{t("Contact", "Contact")}</dt><dd>{cabinet.courriel}<br />{cabinet.telephone}</dd>
            </dl>
          ) : <p className="discret">{t("Chargement…", "Loading…")}</p>}
        </section>
      </div>
    </div>
  );
}
