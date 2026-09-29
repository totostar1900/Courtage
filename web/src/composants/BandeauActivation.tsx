import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import type { Activation } from "../activation";
import { dateFr } from "../format";
import { t } from "../i18n";
import type { Role } from "../types";
import { Erreur, useCharge } from "./communs";
import { DepotFichier } from "./DepotFichier";

interface Justificatif { id: string; nature: string; nom_fichier: string; depose_le: string }

/** En tête de chaque page d'un dossier dont l'inscription n'est pas confirmée : où elle en est, le RCCM à déposer, et
 *  le bouton pour contacter le conseiller. Rien quand elle est confirmée. Le retrait de l'inscription n'est plus
 *  offert ici : une inscription non confirmée s'efface seule à trente jours, et le courtier peut la retirer. */
export function BandeauActivation({ orgId, activation: a, role }: { orgId: string; activation: Activation; role: Role }) {
  if (a.etat === "confirmee") return null;
  const contacter = (
    <Link to={`/dossier/${orgId}/contact`} className="bouton principal">{t("Contacter votre conseiller", "Contact your adviser")}</Link>
  );

  if (a.etat === "refusee")
    return (
      <div className="constat bloque bandeau-activation" role="status">
        <div className="titre">{t("Inscription refusée", "Sign-up declined")}</div>
        {a.motif && <p>{t("Motif : ", "Reason: ")}{a.motif}</p>}
        <div className="actions">{contacter}</div>
      </div>
    );

  return (
    <div className="constat avertit bandeau-activation" role="status">
      <div className="titre">
        {a.echeance
          ? t(`Inscription en attente de confirmation — votre conseiller vous contacte d'ici le ${dateFr(a.echeance)} (2 jours ouvrés).`,
              `Sign-up awaiting confirmation — your adviser will contact you by ${dateFr(a.echeance)} (2 working days).`)
          : t("Inscription en attente de confirmation — votre conseiller vous contacte sous 2 jours ouvrés.",
              "Sign-up awaiting confirmation — your adviser will contact you within 2 working days.")}
      </div>
      <p>{t("Déjà ouvert : personnel, régime, simulations, études à l'écran, messages. Après confirmation : rapports "
        + "scellés, exports, notes de régime, équipe, catalogue et mandat.",
        "Already open: staff, plan, simulations, on-screen studies, messages. After confirmation: sealed reports, "
        + "exports, plan notices, team, catalogue and mandate.")}</p>
      {role !== "lecteur_client" && role !== "conseiller" && <DepotRccm orgId={orgId} />}
      <div className="actions">{contacter}</div>
      {a.expire_le && (
        <p className="discret">{t(`Une inscription non confirmée est effacée le ${dateFr(a.expire_le)}.`,
          `An unconfirmed sign-up is deleted on ${dateFr(a.expire_le)}.`)}</p>
      )}
    </div>
  );
}

/** Le document RCCM : facultatif à l'inscription, il accélère la confirmation. */
function DepotRccm({ orgId }: { orgId: string }) {
  const { donnee: liste, recharger } = useCharge(
    () => api.get<Justificatif[]>(`/organisations/${orgId}/justificatifs`).catch(() => [] as Justificatif[]), [orgId]);
  const [erreur, setErreur] = useState<unknown>(null);
  const [envoi, setEnvoi] = useState(false);

  const [cle, setCle] = useState(0);
  async function deposer(fichier: File | null) {
    if (!fichier) return;
    setErreur(null);
    setEnvoi(true);
    const donnees = new FormData();
    donnees.append("fichier", fichier);
    try {
      await api.post(`/organisations/${orgId}/justificatifs`, donnees);
      recharger();
    } catch (e) { setErreur(e); }
    finally { setEnvoi(false); setCle((k) => k + 1); }
  }

  return (
    <div className="depot-rccm">
      <DepotFichier key={cle} libelle={t("Votre document RCCM (PDF, JPEG ou PNG)", "Your trade register (RCCM) document (PDF, JPEG or PNG)")}
        accept="application/pdf,image/jpeg,image/png" onChange={deposer} disabled={envoi}
        aide={envoi ? t("Envoi…", "Uploading…") : t("Facultatif : il accélère la confirmation.", "Optional: it speeds up confirmation.")} />
      {!!liste?.length && (
        <ul className="discret">
          {liste.map((j) => (
            <li key={j.id}>{t(`${j.nom_fichier} — déposé le ${dateFr(j.depose_le)}`, `${j.nom_fichier} — uploaded on ${dateFr(j.depose_le)}`)}</li>
          ))}
        </ul>
      )}
      <Erreur erreur={erreur} />
    </div>
  );
}
