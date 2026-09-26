import { montant } from "../format";
import type { CalculPrestation } from "../types";

/** Le dû d'un départ, dit en une phrase : l'ancienneté, la règle, les mois, la multiplication. */
export function ExpliquerCalcul({ calcul, du, salaire }: { calcul: CalculPrestation; du: number; salaire: number }) {
  if (!calcul.source) return <p>{calcul.raison}</p>;
  return (
    <p>
      {String(calcul.anciennete).replace(".", ",")} ans d'ancienneté ouvrent droit à{" "}
      <strong>{String(calcul.mois).replace(".", ",")} mois</strong> selon {calcul.source.libelle}
      {calcul.source.categorie && calcul.source.categorie !== "*" ? ` (catégorie ${calcul.source.categorie})` : ""}
      {calcul.plancher_applique ? ", au plancher de la convention" : ""} : {String(calcul.mois).replace(".", ",")} ×{" "}
      {montant(salaire)} = <strong>{montant(du)}</strong>.
    </p>
  );
}

