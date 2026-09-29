import { Link } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { dateFr } from "../format";
import { t } from "../i18n";

interface Ligne {
  id: string; nom: string; pays: string; etape: string; depuis: string | null; jours: number | null; conseillers: string[];
  portefeuille?: { polices: { assureur: string; statut: string; numero: string | null }[]; primes_en_retard: number;
    prochaine_etape: { libelle: string; echeance: string; etat: string } | null; prises_en_charge_ouvertes: number;
    alertes_graves: number };
}
interface Tableau { etapes: { code: string; libelle: string; n: number }[]; dossiers: Ligne[] }

const statutsPolice = (): Record<string, string> => ({ retenue: t("offre retenue", "offer chosen"), recue: t("police reçue", "policy received"),
  signee: t("signée", "signed"), premiere_prime: t("première prime encaissée", "first premium received"), en_vigueur: t("en vigueur", "in force") });

/** Le pipeline (chaque dossier à son étape) et le portefeuille (les dossiers sous mandat, ce qui les attend). */
export default function Portefeuille() {
  const { donnee: x, erreur } = useCharge(() => api.get<Tableau>("/portefeuille"), []);
  if (erreur) return <Erreur erreur={erreur} />;
  if (!x) return <p className="discret">{t("Chargement…", "Loading…")}</p>;
  const libelle = Object.fromEntries(x.etapes.map((e) => [e.code, e.libelle]));
  const sousMandat = x.dossiers.filter((d) => d.portefeuille);
  return (
    <>
      <p><Link to="/">{t("← Vos dossiers", "← Your files")}</Link></p>
      <h1>{t("Pipeline et portefeuille", "Pipeline and portfolio")}</h1>

      <section className="section" aria-labelledby="pipeline">
        <h2 id="pipeline">{t("Le pipeline", "The pipeline")}</h2>
        <ol className="pipeline">
          {x.etapes.map((e) => <li key={e.code}><span className="gros chiffre">{e.n}</span><span>{e.libelle}</span></li>)}
        </ol>
        <div className="defile"><table>
          <thead><tr><th>{t("Dossier", "File")}</th><th>{t("Étape", "Stage")}</th><th>{t("Depuis", "Since")}</th><th>{t("Conseiller", "Adviser")}</th></tr></thead>
          <tbody>{x.dossiers.map((d) => (
            <tr key={d.id}><td><Link to={`/dossier/${d.id}`}>{d.nom}</Link><div className="discret">{d.pays}</div></td>
              <td>{libelle[d.etape] ?? d.etape}</td>
              <td>{d.depuis ? <>{dateFr(d.depuis)}<div className="discret">{t(`${d.jours} j`, `${d.jours} d`)}</div></> : "—"}</td>
              <td>{d.conseillers.join(", ") || "—"}</td></tr>
          ))}</tbody>
        </table></div>
      </section>

      <section className="section" aria-labelledby="portefeuille">
        <h2 id="portefeuille">{t("Le portefeuille", "The portfolio")}</h2>
        {sousMandat.length === 0 ? <p className="discret">{t("Aucun dossier sous mandat.", "No file under mandate.")}</p> : (
          <div className="defile"><table>
            <thead><tr><th>{t("Dossier", "File")}</th><th>{t("Police", "Policy")}</th><th className="n">{t("Primes en retard", "Late premiums")}</th>
              <th>{t("Prochaine étape de l'année", "Next step of the year")}</th><th className="n">{t("Prises en charge ouvertes", "Open claims")}</th>
              <th className="n">{t("Alertes graves", "Serious alerts")}</th></tr></thead>
            <tbody>{sousMandat.map((d) => {
              const p = d.portefeuille!;
              return (
                <tr key={d.id}><td><Link to={`/dossier/${d.id}`}>{d.nom}</Link></td>
                  <td>{p.polices.length ? p.polices.map((x) => <div key={x.assureur}>{x.assureur}
                    <span className="discret"> · {statutsPolice()[x.statut] ?? x.statut}</span></div>) : <span className="discret">{t("pas encore placée", "not placed yet")}</span>}</td>
                  <td className="n">{p.primes_en_retard > 0 ? <span className="etat grave">{p.primes_en_retard}</span> : "0"}</td>
                  <td>{p.prochaine_etape ? <>{p.prochaine_etape.libelle}<div className="discret">{dateFr(p.prochaine_etape.echeance)}
                    {p.prochaine_etape.etat === "en_retard" && <>{" "}<span className="etat grave">{t("en retard", "late")}</span></>}</div></> : "—"}</td>
                  <td className="n">{p.prises_en_charge_ouvertes}</td>
                  <td className="n">{p.alertes_graves > 0 ? <span className="etat grave">{p.alertes_graves}</span> : "0"}</td></tr>
              );
            })}</tbody>
          </table></div>
        )}
      </section>
    </>
  );
}
