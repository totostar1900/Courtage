import { useEffect } from "react";

import { t } from "../i18n";

const DEFAUT = () => t("Nitch — vos indemnités de fin de carrière, chiffrées puis placées",
  "Nitch — your end-of-service benefits, costed then placed");

/** Le titre de l'onglet (et de la page pour un moteur de recherche) : « … — Nitch » ; le titre par défaut ailleurs. */
export default function Titre({ valeur }: { valeur?: string }) {
  useEffect(() => {
    document.title = valeur ? `${valeur} — Nitch` : DEFAUT();
    return () => { document.title = DEFAUT(); };
  }, [valeur]);
  return null;
}
