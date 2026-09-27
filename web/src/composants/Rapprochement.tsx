import { montant } from "../format";
import { rapprocher, tauxFrais } from "../rapprochement";
import { langue, t } from "../i18n";
import type { Etude } from "../types";

/** Les quatre chiffres clés, réconciliés ligne à ligne jusqu'à la cotisation à verser. */
export default function Rapprochement({ etude, titre = true }: { etude: Etude; titre?: boolean }) {
  const lignes = rapprocher(etude.totaux, etude.fonds_disponible, tauxFrais(etude.hypotheses.valeurs, etude.totaux));
  return (
    <div className="rapprochement">
      {titre && <h3>{t("Du passif à la cotisation", "From liability to contribution")}</h3>}
      <div className="defile"><table>
        <tbody>
          {lignes.map((l, i) => (
            <tr key={i} className={l.total ? "total" : undefined}>
              <td>{l.total ? "=" : l.montant < 0 ? "−" : i === 0 ? "" : "+"}</td>
              <td>{l.libelle}{l.note && <div className="discret">{l.note}</div>}</td>
              <td className="n">{montant(Math.abs(l.montant))}</td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  );
}

export function sousCotisation(etude: Etude): string {
  const frais = (etude.totaux.cotisation_totale ?? 0) - (etude.totaux.cotisation_nette ?? 0);
  const taux = tauxFrais(etude.hypotheses.valeurs, etude.totaux);
  if (langue() === "en") return frais > 0 ? `including ${montant(frais)} in charges (${(taux * 100).toLocaleString("en-GB")}%)` : "no charges";
  return frais > 0 ? `dont ${montant(frais)} de frais (${(taux * 100).toLocaleString("fr-FR")} %)` : "sans frais";
}
