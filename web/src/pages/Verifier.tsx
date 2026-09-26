import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { dateFr, montant } from "../format";

interface Verification {
  numero: string;
  nature: string;
  emis_le: string;
  authentique: boolean;
  probant: boolean;
  resume: Record<string, string | number | boolean>;
}

const NATURES: Record<string, string> = { etude_ifc: "Étude actuarielle IFC", fiche_regime: "Cahier des charges" };

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
      <h1>Vérifier un document</h1>
      <form className="actions" onSubmit={(e) => { e.preventDefault(); naviguer(`/verifier/${new FormData(e.currentTarget).get("n")}`); }}>
        <input name="n" defaultValue={numero} placeholder="RL-XXXX-XXXX" aria-label="Numéro du document" />
        <button className="principal">Vérifier</button>
      </form>
      <Erreur erreur={erreur} />
      {v && (
        <div className="carte section">
          <div className="actions" style={{ marginTop: 0 }}>
            {v.authentique
              ? <span className="etat bien">Authentique</span>
              : <span className="etat grave">Non authentique : le document ou son enregistrement a été modifié</span>}
            {v.authentique && !v.probant && <span className="etat attention">Sceau de développement, non probant</span>}
          </div>
          <h2 style={{ marginTop: 12 }}>{NATURES[v.nature] ?? v.nature}</h2>
          <div className="lignes-offre">
            <div><span>Organisation</span><strong>{String(v.resume.organisation)}</strong></div>
            <div><span>Évaluation au</span><span>{dateFr(String(v.resume.date_evaluation))}</span></div>
            {"dette" in v.resume && <div><span>Dette actuarielle</span><span>{montant(Number(v.resume.dette))}</span></div>}
            <div><span>Émis le</span><span>{dateFr(v.emis_le)}{v.resume.emetteur ? ` par ${v.resume.emetteur}` : ""}</span></div>
          </div>
          <form className="actions" onSubmit={comparer}>
            <input type="file" name="document" accept="application/pdf" aria-label="Le PDF à comparer" required />
            <button>Ce PDF est-il l'original ?</button>
          </form>
          {conforme !== null && (conforme
            ? <p><span className="etat bien">Conforme</span> Le fichier est l'original, octet pour octet.</p>
            : <p><span className="etat grave">Différent</span> Ce fichier n'est pas celui qui a été émis.</p>)}
        </div>
      )}
    </div>
  );
}
