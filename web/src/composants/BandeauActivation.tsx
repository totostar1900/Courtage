import { useState, type ChangeEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api";
import type { Activation } from "../activation";
import { dateFr } from "../format";
import { t } from "../i18n";
import type { Role } from "../types";
import { useConfirmation } from "./Confirmer";
import { Erreur, useCharge } from "./communs";

interface Justificatif { id: string; nature: string; nom_fichier: string; depose_le: string }

/** En tête de chaque page d'un dossier dont l'inscription n'est pas confirmée : où elle en est, le RCCM à déposer,
 *  le conseiller à qui écrire, et le retrait de l'inscription. Rien quand elle est confirmée. */
export function BandeauActivation({ orgId, activation: a, role }: { orgId: string; activation: Activation; role: Role }) {
  const naviguer = useNavigate();
  const [demander, fenetre] = useConfirmation();
  if (a.etat === "confirmee") return null;

  function retirer() {
    demander({
      titre: t("Retirer mon inscription", "Withdraw my sign-up"),
      message: <p>{t("Tout ce que le dossier contient est effacé : personnel, régimes, études, messages. Cela ne se "
        + "défait pas.", "Everything in the file is erased: staff, plans, studies, messages. This cannot be undone.")}</p>,
      mot: "SUPPRIMER", bouton: t("Retirer mon inscription", "Withdraw my sign-up"),
      action: async () => {
        await api.del(`/organisations/${orgId}/inscription?confirmation=SUPPRIMER`);
        naviguer("/");
      },
    });
  }
  const actionRetrait = role === "admin_client" && (
    <button type="button" className="danger" onClick={retirer}>{t("Retirer mon inscription", "Withdraw my sign-up")}</button>
  );

  if (a.etat === "refusee")
    return (
      <div className="constat bloque bandeau-activation" role="status">
        {fenetre}
        <div className="titre">{t("Inscription refusée", "Sign-up declined")}</div>
        {a.motif && <p>{t("Motif : ", "Reason: ")}{a.motif}</p>}
        <div className="actions">
          <Link to={`/dossier/${orgId}/messages`}>{t("Écrire à votre conseiller", "Write to your adviser")}</Link>
          {actionRetrait}
        </div>
      </div>
    );

  return (
    <div className="constat avertit bandeau-activation" role="status">
      {fenetre}
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
      <div className="actions">
        <Link to={`/dossier/${orgId}/messages`}>{t("Écrire à votre conseiller", "Write to your adviser")}</Link>
        {actionRetrait}
      </div>
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

  async function deposer(ev: ChangeEvent<HTMLInputElement>) {
    const fichier = ev.currentTarget.files?.[0];
    const champ = ev.currentTarget;
    if (!fichier) return;
    setErreur(null);
    setEnvoi(true);
    const donnees = new FormData();
    donnees.append("fichier", fichier);
    try {
      await api.post(`/organisations/${orgId}/justificatifs`, donnees);
      recharger();
    } catch (e) { setErreur(e); }
    finally { setEnvoi(false); champ.value = ""; }
  }

  return (
    <div className="depot-rccm">
      <label>{t("Votre document RCCM (PDF, JPEG ou PNG)", "Your trade register (RCCM) document (PDF, JPEG or PNG)")}
        <input type="file" accept="application/pdf,image/jpeg,image/png" onChange={deposer} disabled={envoi} />
      </label>
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
