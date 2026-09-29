import { Link } from "react-router-dom";

import { useCabinet } from "../cabinet";
import { useMesure } from "../mesure";
import EtreRappele from "../composants/EtreRappele";
import { t } from "../i18n";

/** La première page d'un visiteur : ce que fait le service, ce qu'il coûte, qui le rend, qui l'exploite, et par où entrer. */
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
    [t("Les assureurs en concurrence pour vous", "Insurers competing for you"),
     t("Votre besoin est porté sur le marché : les assureurs répondent au même cahier des charges, anonymisé. Leurs offres sont confrontées à vos conditions et classées par leur rendement net, taux servi moins frais et chargements. Vous choisissez sur des chiffres, avec une recommandation motivée.",
       "Your need is taken to the market: insurers answer the same anonymised tender specifications. Their offers are checked against your requirements and ranked by net return, the rate paid less fees and charges. You choose on figures, with a reasoned recommendation.")],
    [t("La meilleure solution, à chaque moment", "The best solution, at every moment"),
     t("Le marché bouge, vos effectifs aussi. Votre conseiller suit votre contrat dans la durée : chaque année l'engagement est réévalué, et quand le marché offre mieux pour votre besoin ou votre rendement, il vous le dit et le met en concurrence.",
       "The market moves, and so does your workforce. Your adviser follows your contract over time: each year the liability is revalued, and when the market offers better for your need or your return, they tell you and put it to tender.")],
    [t("Un engagement chiffré, des départs pris en charge", "A costed liability, departures handled"),
     t("La dette IFC selon votre convention et votre régime, dans un rapport scellé et vérifiable. À chaque départ, le montant dû est recalculé et le dossier suivi auprès de l'assureur jusqu'au paiement.",
       "The end-of-service liability under your agreement and your plan, in a sealed, verifiable report. At each departure, the amount due is recalculated and the file followed with the insurer until payment.")],
  ];
  const garanties = [
    [t("Gratuit pour l'entreprise", "Free for the company"),
     t("Ni la plateforme ni l'accompagnement ne vous sont facturés.", "Neither the platform nor the support is charged to you."),
     "M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"],
    [t("Aucun nom de salarié", "No employee names"),
     t("Un matricule, des dates et des salaires suffisent : aucun nom n'est lu ni gardé.", "A staff number, dates and salaries are enough: no name is read or kept."),
     "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21v-1a6 6 0 0 1 9-5.2M16 16l5 5M21 16l-5 5"],
    [t("Des rapports scellés", "Sealed reports"),
     t("Chaque rapport porte un numéro que tout destinataire peut vérifier en ligne.", "Each report carries a number any recipient can verify online."),
     "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6zM9 12l2 2 4-4"],
  ];
  const equipe = [
    ["50+", t("années d'expérience cumulée dans l'assurance", "cumulated years of experience in insurance")],
    [t("Actuaires", "Actuaries"), t("chevronnés, et professionnels du marché de l'assurance", "seasoned, alongside insurance market professionals")],
    [t("Quatre marchés", "Four markets"), t("Cameroun · Afrique · Europe · Amérique", "Cameroon · Africa · Europe · America")],
  ];
  const questions = [
    [t("Combien coûte l'accompagnement ?", "What does the support cost?"),
     t("Rien pour l'entreprise : ni l'usage de la plateforme ni l'accompagnement du courtier ne vous sont facturés. Les conditions sont écrites dans le mandat, que vous lisez avant de signer.",
       "Nothing for the company: neither the platform nor the broker's support is charged to you. The terms are written in the mandate, which you read before signing.")],
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
            <a href="#vitrine-rappel" className="bouton bouton-grand bouton-rappel">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                   strokeLinejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z" /></svg>
              {t("Être rappelé", "Get a call back")}</a>
          </div>
          <p className="vitrine-liens"><Link to="/connexion">{t("Déjà un compte ? Se connecter", "Already have an account? Sign in")}</Link></p>
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

      <ul className="vitrine-garanties" aria-label={t("Nos engagements", "Our commitments")}>
        {garanties.map(([titre, texte, icone]) => (
          <li key={titre}>
            <span className="pastille-icone" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={icone} /></svg>
            </span>
            <div><strong>{titre}</strong><span>{texte}</span></div>
          </li>
        ))}
      </ul>

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
        <p className="vitrine-intro">{t(
          "Le marché mis en concurrence pour vous, et un courtier à vos côtés pour trouver, à chaque moment, la solution et le rendement qui répondent le mieux à votre besoin.",
          "The market competing for you, and a broker at your side to find, at every moment, the solution and the return that best meet your need.")}</p>
        <div className="grille g3">
          {apports.map(([titre, texte], i) => (
            <div key={titre} className={`carte carte-icone${i === 0 ? " carte-vedette" : ""}`}>
              <span className="pastille-icone" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={icones[i]} /></svg>
              </span>
              <h3>{titre}</h3><p>{texte}</p>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="vitrine-equipe" className="vitrine-bloc vitrine-equipe">
        <div>
          <p className="surtitre">{t("L'équipe", "The team")}</p>
          <h2 id="vitrine-equipe">{t("Qui est derrière Nitch", "Who is behind Nitch")}</h2>
          <p>{t(
            "Une équipe de professionnels de l'assurance et d'actuaires chevronnés, forte de plus de 50 ans d'expérience cumulée sur les marchés du Cameroun, d'Afrique, d'Europe et d'Amérique.",
            "A team of insurance professionals and seasoned actuaries, with more than 50 years of cumulated experience in the markets of Cameroon, Africa, Europe and America.")}</p>
          <p>{t(
            "Nous mettons cette expertise au service de vos engagements et de vos portefeuilles d'assurance, pour en révéler les opportunités et le potentiel. Nous comprenons votre besoin, nous connaissons le marché et les solutions qu'il offre : nous le mettons en concurrence pour vous.",
            "We dedicate this expertise to your commitments and your insurance portfolios, to unlock their opportunities and potential. We understand your need, we know the market and the solutions it offers: we get it competing for you.")}</p>
        </div>
        <dl className="vitrine-chiffres">
          {equipe.map(([chiffre, texte]) => <div key={chiffre}><dt>{chiffre}</dt><dd>{texte}</dd></div>)}
        </dl>
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
        <section aria-labelledby="vitrine-rappel" className="carte vitrine-rappel">
          <p className="surtitre">{t("Être rappelé", "Get a call back")}</p>
          <h2 id="vitrine-rappel" style={{ marginTop: 0 }}>{t("Parler à un conseiller", "Talk to an adviser")}</h2>
          <p>{t("Vous préférez en parler avant d'essayer ? Laissez votre numéro : le courtier vous rappelle, au créneau que vous choisissez.",
            "Rather talk it through before trying? Leave your number: the broker calls you back at the time you choose.")}</p>
          <EtreRappele />
        </section>

        <section aria-labelledby="vitrine-cabinet" className="carte vitrine-cabinet">
          <p className="surtitre">{t("L'exploitant", "The operator")}</p>
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
