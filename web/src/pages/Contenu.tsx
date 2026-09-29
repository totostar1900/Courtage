import { Link } from "react-router-dom";

import { api } from "../api";
import { useCharge } from "../composants/communs";
import { dateFr } from "../format";
import { t } from "../i18n";
import { useMesure } from "../mesure";

/** Les pages de contenu publiques. Règle : rien d'inventé — un barème vient du référentiel, avec ses sources ; un point
 *  de droit reprend la rédaction prudente des notes juridiques de la plateforme. */

type P = [string, string];
function Bloc({ titre, paragraphes }: { titre: P; paragraphes: P[] }) {
  return (
    <section>
      <h2>{t(...titre)}</h2>
      {paragraphes.map((p, i) => <p key={i}>{t(...p)}</p>)}
    </section>
  );
}

function Appel() {
  return (
    <div className="carte section">
      <p style={{ marginTop: 0 }}><strong>{t("Combien pèse votre engagement ?", "How much is your liability?")}</strong>{" "}
        {t("L'essai le calcule à l'écran, sans compte : votre personnel, votre convention, le résultat.",
           "The trial calculates it on screen, without an account: your staff, your agreement, the result.")}</p>
      <div className="actions">
        <Link to="/essai" className="bouton principal">{t("Essayer sans compte", "Try without an account")}</Link>
        <Link to="/#vitrine-rappel" className="bouton">{t("Parler à un conseiller", "Talk to an adviser")}</Link>
      </div>
    </div>
  );
}

export function PageIfc() {
  useMesure("contenu_ifc");
  return (
    <article className="legal contenu">
      <h1>{t("Les indemnités de fin de carrière", "End-of-service benefits")}</h1>
      <p className="vitrine-chapeau">{t("Ce que l'entreprise devra payer à ses salariés quand ils partiront à la retraite existe déjà aujourd'hui. Voici comment le comprendre, le mesurer et le financer.",
        "What the company will owe its employees when they retire already exists today. Here is how to understand it, measure it and fund it.")}</p>
      <Bloc titre={["Ce que c'est", "What it is"]} paragraphes={[
        ["L'indemnité de fin de carrière (IFC), qu'on appelle aussi indemnité de départ à la retraite, est une somme que l'employeur verse au salarié qui part à la retraite. Elle se compte en mois de salaire et grandit avec l'ancienneté.",
         "The end-of-service benefit (IFC), also called the retirement allowance, is a sum the employer pays to an employee who retires. It is counted in months of salary and grows with length of service."],
        ["Son montant est fixé par la convention collective de la branche. Un accord d'entreprise, ou le contrat de travail, peut prévoir plus favorable ; jamais moins.",
         "Its amount is set by the industry's collective agreement. A company agreement, or the employment contract, can provide more; never less."]]} />
      <Bloc titre={["Un engagement qui grandit chaque année", "A liability that grows every year"]} paragraphes={[
        ["Chaque année de présence ajoute des droits. Ce que l'entreprise paiera demain est donc déjà une dette envers ses salariés, qui se mesure avant d'échoir.",
         "Every year of service adds entitlements. What the company will pay tomorrow is therefore already a debt to its employees, to be measured before it falls due."],
        ["Plusieurs départs la même année, des cadres anciens en particulier, peuvent peser lourd sur la trésorerie s'ils n'ont pas été préparés.",
         "Several departures in the same year, long-serving managers in particular, can weigh heavily on cash if they have not been prepared for."]]} />
      <Bloc titre={["Comment elle se mesure", "How it is measured"]} paragraphes={[
        ["La méthode actuarielle projette, pour chaque salarié, son salaire et son ancienneté au jour de son départ, les pondère par la probabilité qu'il soit encore dans l'entreprise, puis ramène le tout à aujourd'hui. Le résultat est la dette actuarielle.",
         "The actuarial method projects, for each employee, their salary and length of service at retirement, weights them by the probability that they are still with the company, then brings everything back to today. The result is the actuarial liability."],
        ["Ce chiffre dépend d'hypothèses — taux d'actualisation, progression des salaires, rotation du personnel — qui doivent être dites et datées. Une évaluation se refait chaque année, à la même date.",
         "This figure depends on assumptions — discount rate, salary growth, staff turnover — which must be stated and dated. A valuation is redone every year, on the same date."]]} />
      <Bloc titre={["Comment la financer", "How to fund it"]} paragraphes={[
        ["Deux voies. La provision interne : l'entreprise garde les fonds et le risque. Le contrat d'assurance IFC : un assureur gère un fonds dédié, lui sert un rendement et paie les indemnités au moment des départs.",
         "Two ways. An internal provision: the company keeps the funds and the risk. An IFC insurance contract: an insurer manages a dedicated fund, credits it with a return and pays the benefits when employees leave."],
        ["Le bon choix dépend de la taille de l'entreprise, de sa trésorerie et du calendrier des départs. C'est une décision de l'entreprise, avec son expert-comptable.",
         "The right choice depends on the company's size, its cash and the timing of departures. It is the company's decision, with its accountant."]]} />
      <Bloc titre={["Ce que fait la plateforme", "What the platform does"]} paragraphes={[
        ["Elle chiffre l'engagement selon votre convention et votre régime, met les assureurs en concurrence sur ce chiffre, puis suit chaque départ jusqu'au paiement. L'accompagnement ne coûte rien à l'entreprise : le courtier est rémunéré par l'assureur retenu.",
         "It costs the liability under your agreement and your plan, puts insurers in competition on that figure, then follows each departure until payment. The support costs the company nothing: the broker is paid by the insurer chosen."]]} />
      <p><Link to="/ifc/cameroun">{t("Les IFC au Cameroun →", "End-of-service benefits in Cameroon →")}</Link>{" · "}
        <Link to="/guide">{t("La méthode, en détail, dans le guide", "The method, in detail, in the guide")}</Link></p>
      <Appel />
    </article>
  );
}

interface Convention { pays: string; code: string; libelle: string; statut: string; en_vigueur_du: string;
  en_vigueur_au: string | null; en_vigueur_aujourd_hui: boolean; verification: string | null;
  sources: { titre: string; url?: string | null }[]; illustration: { anciennete: number; mois: number }[] }

function BaremesCameroun() {
  const { donnee } = useCharge(() => api.get<{ conventions: Convention[] }>("/referentiel/conventions").catch(() => null), []);
  if (!donnee) return <p className="discret">{t("Chargement des barèmes…", "Loading the scales…")}</p>;
  const cm = donnee.conventions.filter((c) => c.pays === "CM" && c.en_vigueur_aujourd_hui);
  if (!cm.length) return <p className="discret">{t("Aucun barème en vigueur dans le référentiel.", "No scale in force in the reference data.")}</p>;
  const anciennetes = cm[0].illustration.map((x) => x.anciennete);
  return (
    <>
      <div className="defile"><table>
        <thead><tr><th>{t("Convention", "Agreement")}</th>
          {anciennetes.map((a) => <th key={a} className="n">{t(`${a} ans`, `${a} yrs`)}</th>)}</tr></thead>
        <tbody>{cm.map((c) => (
          <tr key={c.code + c.en_vigueur_du}>
            <td>{c.libelle}<div className="discret">{t(`en vigueur depuis le ${dateFr(c.en_vigueur_du)}`, `in force since ${dateFr(c.en_vigueur_du)}`)}
              {c.statut !== "valide" && t(" · barème provisoire", " · provisional scale")}</div></td>
            {c.illustration.map((x) => <td key={x.anciennete} className="n chiffre">{x.mois.toLocaleString("fr-FR")}</td>)}
          </tr>
        ))}</tbody>
      </table></div>
      <p className="discret">{t("En mois de salaire, à l'ancienneté indiquée. Chaque barème est daté et sourcé :", "In months of salary, at the length of service shown. Each scale is dated and sourced:")}</p>
      <ul className="discret">
        {cm.map((c) => (
          <li key={c.code + c.en_vigueur_du}><strong>{c.libelle}</strong>{c.verification && <> — {c.verification}</>}
            {c.sources.length > 0 && <> {t("Sources : ", "Sources: ")}{c.sources.map((s, i) => (
              <span key={i}>{i > 0 && " ; "}{s.url ? <a href={s.url} rel="noopener noreferrer" target="_blank">{s.titre}</a> : s.titre}</span>
            ))}.</>}</li>
        ))}
      </ul>
    </>
  );
}

export function PageIfcCameroun() {
  useMesure("contenu_cameroun");
  return (
    <article className="legal contenu">
      <p><Link to="/ifc">{t("← Les indemnités de fin de carrière", "← End-of-service benefits")}</Link></p>
      <h1>{t("Les indemnités de fin de carrière au Cameroun", "End-of-service benefits in Cameroon")}</h1>
      <Bloc titre={["D'où vient l'obligation", "Where the obligation comes from"]} paragraphes={[
        ["Selon notre lecture, l'indemnité de départ à la retraite est prévue au Cameroun par les conventions collectives nationales de branche — commerce, banques et établissements financiers, entre autres. Un accord d'entreprise ou le contrat de travail peut prévoir plus favorable.",
         "As we read it, the retirement allowance is provided for in Cameroon by the national industry collective agreements — commerce, banks and financial institutions, among others. A company agreement or the employment contract can provide more."],
        ["La pension de vieillesse servie par la CNPS est distincte : elle ne remplace pas l'indemnité que doit l'employeur.",
         "The old-age pension paid by the CNPS is separate: it does not replace the allowance owed by the employer."]]} />
      <section>
        <h2>{t("Les barèmes dans la plateforme", "The scales in the platform")}</h2>
        <p>{t("Les conventions du Cameroun que la plateforme applique aujourd'hui, et ce qu'elles donnent :",
          "The Cameroon agreements the platform applies today, and what they give:")}</p>
        <BaremesCameroun />
      </section>
      <Bloc titre={["Dans les comptes", "In the accounts"]} paragraphes={[
        ["Selon notre lecture, un régime d'indemnités de fin de carrière relève des engagements à prestations définies : l'entreprise promet un montant, pas une cotisation. À notre connaissance, le SYSCOHADA révisé prévoit la comptabilisation des engagements de retraite ; IAS 19 concerne les entreprises qui publient en IFRS.",
         "As we read it, an end-of-service benefit plan is a defined-benefit obligation: the company promises an amount, not a contribution. To our knowledge, the revised SYSCOHADA provides for recognising retirement obligations; IAS 19 concerns companies reporting under IFRS."],
        ["L'étude actuarielle donne un montant de référence ; le traitement comptable retenu relève de l'entreprise et de son expert-comptable.",
         "The actuarial study gives a reference amount; the accounting treatment adopted is for the company and its accountant."]]} />
      <Bloc titre={["La fiscalité", "Tax"]} paragraphes={[
        ["Le Code général des impôts fixe les conditions de déduction des charges et des provisions. Le traitement des cotisations versées à un assureur pour les indemnités de fin de carrière, comme celui d'une provision interne, mérite d'être examiné avec un fiscaliste : la plateforme n'émet pas d'avis sur ce point.",
         "The General Tax Code sets the conditions for deducting expenses and provisions. The treatment of contributions paid to an insurer for end-of-service benefits, like that of an internal provision, should be examined with a tax adviser: the platform gives no opinion on this point."]]} />
      <Bloc titre={["Financer auprès d'un assureur", "Funding with an insurer"]} paragraphes={[
        ["Des assureurs vie agréés proposent des contrats de gestion des indemnités de fin de carrière : un fonds dédié, un taux garanti, une participation aux bénéfices, et le paiement des indemnités aux départs. Les conditions — frais, transfert, délai de paiement — varient d'un assureur à l'autre : c'est ce que la mise en concurrence compare.",
         "Licensed life insurers offer contracts to manage end-of-service benefits: a dedicated fund, a guaranteed rate, profit sharing, and payment of the benefits at departures. The terms — fees, transfer, payment period — vary from one insurer to another: that is what the tender compares."]]} />
      <Appel />
    </article>
  );
}
