import { api } from "../api";
import { dateFr, pct } from "../format";
import { t } from "../i18n";
import { useCharge } from "./communs";

interface Tableau { depuis: string; jusqu_au: string; entonnoir: { evenement: string; n: number; taux: number | null }[];
  contenus: Record<string, number>; sources_vitrine: Record<string, number> }

const libelles = (): Record<string, string> => ({ vitrine: t("Visites de la vitrine", "Home page visits"),
  essai_ouvert: t("Essais ouverts", "Trials opened"), essai_calcule: t("Essais calculés", "Trials calculated"),
  inscription_ouverte: t("Inscriptions commencées", "Sign-ups started"), inscription_faite: t("Inscriptions faites", "Sign-ups completed"),
  mandat_signe: t("Mandats signés", "Mandates signed"), contenu_ifc: t("Page « Les IFC »", "“End-of-service benefits” page"),
  contenu_cameroun: t("Page « Les IFC au Cameroun »", "“In Cameroon” page") });
const sources = (): Record<string, string> => ({ direct: t("direct", "direct"), recherche: t("moteurs de recherche", "search engines"),
  reseau_social: t("réseaux sociaux", "social networks"), autre: t("autres sites", "other sites") });

/** L'audience des 30 derniers jours, sans témoin : l'entonnoir de la vitrine au mandat, les pages lues, les sources. */
export default function Audience() {
  const { donnee: a } = useCharge(() => api.get<Tableau>("/mesures").catch(() => null), []);
  if (!a) return null;
  const L = libelles();
  return (
    <section className="carte section" aria-labelledby="audience">
      <h2 id="audience" style={{ marginTop: 0 }}>{t("Audience", "Audience")}</h2>
      <p className="discret">{t(`Du ${dateFr(a.depuis)} au ${dateFr(a.jusqu_au)} — un compteur par jour, sans témoin ni identifiant.`,
        `From ${dateFr(a.depuis)} to ${dateFr(a.jusqu_au)} — one counter per day, with no cookie or identifier.`)}</p>
      <div className="defile"><table>
        <thead><tr><th>{t("Étape", "Step")}</th><th className="n">{t("Nombre", "Count")}</th><th className="n">{t("Passage", "Conversion")}</th></tr></thead>
        <tbody>{a.entonnoir.map((e) => (
          <tr key={e.evenement}><td>{L[e.evenement]}</td><td className="n chiffre">{e.n}</td>
            <td className="n discret">{e.taux === null ? "—" : pct(e.taux, 0)}</td></tr>
        ))}</tbody>
      </table></div>
      <p className="discret">{Object.entries(a.contenus).map(([k, n]) => `${L[k]} : ${n}`).join(" · ")}<br />
        {t("D'où viennent les visites : ", "Where visits come from: ")}
        {Object.entries(a.sources_vitrine).map(([k, n]) => `${sources()[k]} ${n}`).join(" · ")}</p>
    </section>
  );
}
