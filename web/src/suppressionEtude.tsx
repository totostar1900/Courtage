import { api } from "./api";
import type { Demande } from "./composants/Confirmer";
import { dateFr } from "./format";
import type { Role } from "./types";

/** Qui supprime quoi : un brouillon, l'équipe ; une étude émise, l'administrateur ou le conseiller, si rien ne la
 *  cite. `null` : l'action se montre ; sinon la raison de la griser. */
export function raisonDeNePasSupprimer(e: { statut: string; raison_de_garder?: string | null }, role: Role): string | null {
  if (role === "lecteur_client") return "En lecture seule.";
  if (e.statut === "emise" && role !== "admin_client" && role !== "conseiller")
    return "Seuls l'administrateur et le conseiller suppriment une étude émise.";
  return e.statut === "emise" ? e.raison_de_garder ?? null : null;
}

/** La demande de confirmation écrite, pour une étude en brouillon ou émise. */
export function demandeSuppression(orgId: string, e: { id: string; statut: string; date_evaluation: string },
                                   apres: () => void): Demande {
  const emise = e.statut === "emise";
  return {
    titre: emise ? `Supprimer l'étude émise au ${dateFr(e.date_evaluation)}` : `Supprimer le brouillon au ${dateFr(e.date_evaluation)}`,
    message: emise
      ? <><p>L'étude et son rapport PDF quittent la plateforme. <b>Téléchargez-les d'abord</b> si vous voulez les garder.</p>
          <p>Le sceau reste : le numéro du rapport se vérifie toujours. Le journal garde la trace de la suppression.</p></>
      : <p>Un brouillon n'engage rien : il se refait à tout moment depuis le même fichier.</p>,
    mot: "SUPPRIMER",
    action: async () => {
      await api.del(`/organisations/${orgId}/etudes/${e.id}${emise ? "?confirmation=SUPPRIMER" : ""}`);
      apres();
    },
  };
}
