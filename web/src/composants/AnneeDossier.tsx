import { Link } from "react-router-dom";

import { api } from "../api";
import { dateFr } from "../format";
import { t } from "../i18n";
import { useCharge } from "./communs";

interface Calendrier { derniere: string | null; prochaine: string | null;
  etapes: { code: string; libelle: string; echeance: string; fait_le: string | null;
            etat: "fait" | "a_venir" | "bientot" | "en_retard"; pour: string; lien: string }[] }

const etats = (): Record<string, [string, string]> => ({ fait: [t("Fait", "Done"), "bien"],
  a_venir: [t("À venir", "Upcoming"), "neutre"], bientot: [t("Bientôt", "Soon"), "attention"],
  en_retard: [t("En retard", "Late"), "grave"] });

/** L'année du dossier : l'engagement se remesure chaque année à la même date ; chaque étape se lit dans les données. */
export default function AnneeDossier({ orgId }: { orgId: string }) {
  const { donnee: c } = useCharge(() => api.get<Calendrier>(`/organisations/${orgId}/calendrier`).catch(() => null), [orgId]);
  if (!c || !c.prochaine) return null;
  return (
    <section className="carte section" aria-labelledby="annee-dossier">
      <h2 id="annee-dossier" style={{ marginTop: 0 }}>{t("L'année du dossier", "The file's year")}</h2>
      <p className="discret">{t(`Dernière évaluation au ${dateFr(c.derniere)} ; la prochaine est au ${dateFr(c.prochaine)}, la même date un an plus tard.`,
        `Last valuation as at ${dateFr(c.derniere)}; the next one is as at ${dateFr(c.prochaine)}, the same date a year later.`)}</p>
      <ol className="annee-etapes">
        {c.etapes.map((e) => {
          const [libelle, style] = etats()[e.etat];
          return (
            <li key={e.code + e.echeance}>
              <Link to={e.lien}>{e.libelle}</Link>
              <span className="discret">{e.fait_le ? t(`fait (${dateFr(e.fait_le)})`, `done (${dateFr(e.fait_le)})`)
                : t(`d'ici le ${dateFr(e.echeance)}`, `by ${dateFr(e.echeance)}`)}</span>
              <span className={`etat ${style}`}>{libelle}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
