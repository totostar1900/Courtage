import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { dateFr, montant } from "../format";
import { t } from "../i18n";

interface Verification {
  numero: string;
  nature: string;
  emis_le: string;
  authentique: boolean;
  probant: boolean;
  resume: Record<string, string | number | boolean>;
}

const natures = (): Record<string, string> => ({
  etude_ifc: t("Étude actuarielle IFC", "IFC actuarial study"), fiche_regime: t("Cahier des charges", "Tender specifications"),
  prise_en_charge: t("Dossier de prise en charge", "Claim file"), dossier_scelle: t("Dossier de prise en charge", "Claim file"),
  fiche_de_calcul: t("Fiche de calcul", "Calculation sheet"), note_regime_salaries: t("Note aux salariés", "Note to employees"),
  note_regime_assureurs: t("Note aux assureurs", "Note to insurers"), mandat_courtage: t("Mandat de courtage", "Brokerage mandate"),
});

/** Page publique : n'importe qui vérifie un document par son numéro, sans compte. */
export default function Verifier() {
  const { numero } = useParams();
  const naviguer = useNavigate();
  const { donnee: v, erreur } = useCharge(
    () => (numero ? api.get<Verification>(`/verifier/${numero}`) : Promise.resolve(null)), [numero]);
  const [conforme, setConforme] = useState<boolean | null>(null);

  async function comparer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const r = await api.post<{ conforme: boolean }>(`/verifier/${numero}`, new FormData(ev.currentTarget));
    setConforme(r.conforme);
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <h1>{t("Vérifier un document", "Verify a document")}</h1>
      <form className="actions" onSubmit={(e) => { e.preventDefault(); naviguer(`/verifier/${new FormData(e.currentTarget).get("n")}`); }}>
        <input name="n" defaultValue={numero} placeholder="RL-XXXX-XXXX" aria-label={t("Numéro du document", "Document number")} />
        <button className="principal">{t("Vérifier", "Verify")}</button>
      </form>
      <Erreur erreur={erreur} />
      {v && (
        <div className="carte section">
          <div className="actions" style={{ marginTop: 0 }}>
            {v.authentique
              ? <span className="etat bien">{t("Authentique", "Authentic")}</span>
              : <span className="etat grave">{t("Non authentique : le document ou son enregistrement a été modifié", "Not authentic: the document or its record has been altered")}</span>}
            {v.authentique && !v.probant && <span className="etat attention">{t("Sceau de développement, non probant", "Development seal, not probative")}</span>}
          </div>
          <h2 style={{ marginTop: 12 }}>{natures()[v.nature] ?? v.nature}</h2>
          <div className="lignes-offre">
            <div><span>{t("Organisation", "Organisation")}</span><strong>{String(v.resume.organisation)}</strong></div>
            {"date_evaluation" in v.resume && <div><span>{t("Évaluation au", "Valuation as at")}</span><span>{dateFr(String(v.resume.date_evaluation))}</span></div>}
            {"courtier" in v.resume && <div><span>{t("Courtier", "Broker")}</span><span>{String(v.resume.courtier)}</span></div>}
            {"date_effet" in v.resume && <div><span>{t("Prise d'effet", "Effective date")}</span><span>{dateFr(String(v.resume.date_effet))}</span></div>}
            {"signataire" in v.resume && <div><span>{t("Signé par", "Signed by")}</span><span>{String(v.resume.signataire)}</span></div>}
            {"dette" in v.resume && <div><span>{t("Dette actuarielle", "Actuarial liability")}</span><span>{montant(Number(v.resume.dette))}</span></div>}
            <div><span>{t("Émis le", "Issued on")}</span><span>{dateFr(v.emis_le)}{v.resume.emetteur ? t(` par ${v.resume.emetteur}`, ` by ${v.resume.emetteur}`) : ""}</span></div>
          </div>
          <form className="actions" onSubmit={comparer}>
            <input type="file" name="document" accept="application/pdf" aria-label={t("Le PDF à comparer", "The PDF to compare")} required />
            <button>{t("Ce PDF est-il l'original ?", "Is this PDF the original?")}</button>
          </form>
          {conforme !== null && (conforme
            ? <p><span className="etat bien">{t("Conforme", "Matches")}</span>{t(" Le fichier est l'original, octet pour octet.", " The file is the original, byte for byte.")}</p>
            : <p><span className="etat grave">{t("Différent", "Different")}</span>{t(" Ce fichier n'est pas celui qui a été émis.", " This file is not the one that was issued.")}</p>)}
        </div>
      )}
    </div>
  );
}
