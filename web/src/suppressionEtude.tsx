import { api } from "./api";
import type { Demande } from "./composants/Confirmer";
import { dateFr } from "./format";
import { t } from "./i18n";
import type { Role } from "./types";

/** Qui supprime quoi : un brouillon, l'équipe ; une étude émise, l'administrateur ou le conseiller, si rien ne la
 *  cite. `null` : l'action se montre ; sinon la raison de la griser. */
export function raisonDeNePasSupprimer(e: { statut: string; raison_de_garder?: string | null }, role: Role): string | null {
  if (role === "lecteur_client") return t("En lecture seule.", "Read-only.");
  if (e.statut === "emise" && role !== "admin_client" && role !== "conseiller")
    return t("Seuls l'administrateur et le conseiller suppriment une étude émise.",
             "Only the administrator and the adviser can delete an issued study.");
  return e.statut === "emise" ? e.raison_de_garder ?? null : null;
}

/** La demande de confirmation écrite, pour une étude en brouillon ou émise. */
export function demandeSuppression(orgId: string, e: { id: string; statut: string; date_evaluation: string },
                                   apres: () => void): Demande {
  const emise = e.statut === "emise";
  return {
    titre: emise ? t(`Supprimer l'étude émise au ${dateFr(e.date_evaluation)}`, `Delete the study issued as at ${dateFr(e.date_evaluation)}`)
      : t(`Supprimer le brouillon au ${dateFr(e.date_evaluation)}`, `Delete the draft as at ${dateFr(e.date_evaluation)}`),
    message: emise
      ? <><p>{t("L'étude et son rapport PDF quittent la plateforme. ", "The study and its PDF report leave the platform. ")}
            <b>{t("Téléchargez-les d'abord", "Download them first")}</b>
            {t(" si vous voulez les garder.", " if you want to keep them.")}</p>
          <p>{t("Le sceau reste : le numéro du rapport se vérifie toujours. Le journal garde la trace de la suppression.",
                "The seal remains: the report number can still be verified. The log keeps a record of the deletion.")}</p></>
      : <p>{t("Un brouillon n'engage rien : il se refait à tout moment depuis le même fichier.",
              "A draft commits you to nothing: it can be redone at any time from the same file.")}</p>,
    mot: t("SUPPRIMER", "DELETE"),
    action: async () => {
      await api.del(`/organisations/${orgId}/etudes/${e.id}${emise ? "?confirmation=SUPPRIMER" : ""}`);
      apres();
    },
  };
}
