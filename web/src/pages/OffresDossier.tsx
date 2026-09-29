import { Link } from "react-router-dom";

import { t } from "../i18n";
import { useDossier } from "./Dossier";
import { ReponsesDeLaFiche } from "./Reponses";

/** Les offres : celles que le conseiller a obtenues des assureurs consultés, et rien d'autre — plus de comparaison sur
 *  des chiffres saisis au hasard. Avant la confirmation, le mandat ou le cahier des charges, la page dit ce qui vient
 *  et qui le fait. */
export default function OffresDossier() {
  const d = useDossier();
  const sousMandat = d.activation?.capacites.cahier !== false;
  const derniere = [...d.fiches].sort((a, b) => b.emise_le.localeCompare(a.emise_le))[0];
  if (sousMandat && derniere) return <ReponsesDeLaFiche fiche={derniere.id} />;

  const pas: [string, string, string, boolean][] = [
    [t("Votre inscription confirmée", "Your sign-up confirmed"), t("Votre conseiller vérifie l'entreprise.", "Your adviser checks the company."),
     "..", d.activation?.etat === "confirmee"],
    [t("Le mandat de courtage signé", "The brokerage mandate signed"), t("Demandé, proposé par votre conseiller, signé en ligne.", "Requested, proposed by your adviser, signed online."),
     "../accompagnement", sousMandat],
    [t("Le cahier des charges envoyé", "The specifications sent"), t("Votre étude émise, vos conditions : les assureurs répondent sur la même base.", "Your issued study, your terms: insurers answer on the same basis."),
     "../cahier", Boolean(derniere)],
    [t("Les offres, classées", "The offers, ranked"), t("Votre conseiller les apporte ici, par rendement net ; vous choisissez.", "Your adviser brings them here, by net return; you choose."),
     "", false],
  ];
  return (
    <>
      <h1>{t("Les offres des assureurs", "The insurers' offers")}</h1>
      <p>{t("Les offres arrivent ici quand votre conseiller a consulté les assureurs pour vous. Elles sont classées par rendement net : ce que chacune rapporte à votre fonds une fois tous les frais payés.",
        "Offers arrive here once your adviser has consulted insurers for you. They are ranked by net return: what each one earns your fund once all charges are paid.")}</p>
      <section className="carte section verrou" aria-labelledby="offres-a-venir">
        <p className="surtitre">{t("Pas encore d'offre", "No offer yet")}</p>
        <h2 id="offres-a-venir">{t("Ce qui vient avant les offres", "What comes before the offers")}</h2>
        <ol className="frise frise-4">
          {pas.map(([titre, texte, vers, fait], i) => (
            <li key={titre} className={fait ? "fait" : ""}>
              <span className="frise-num">{fait ? "✓" : i + 1}</span>
              <strong>{vers ? <Link to={vers}>{titre}</Link> : titre}</strong><span>{texte}</span>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}
