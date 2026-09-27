import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { MenuActions } from "../composants/MenuActions";
import { CONVENTION_PAR_PAYS } from "../composants/EditeurCategories";
import { aEnvoyer, Hypotheses, saisieParDefaut, type SaisieHypotheses } from "../composants/Hypotheses";
import { dateFr, montant } from "../format";
import { enCours, libelleVersion, ordonner } from "../regimes";
import type { CatalogueHypotheses, Etude } from "../types";
import { useDossier } from "./Dossier";

export default function Etudes() {
  const d = useDossier();
  const naviguer = useNavigate();
  const [erreur, setErreur] = useState<unknown>(null);
  // Une hypothèse proposée par l'expérience réelle arrive ici, à confirmer : jamais appliquée sans décision.
  const [params] = useSearchParams();
  const proposee = params.get("turnover");
  // La version qui s'applique d'abord.
  const versions = d.regimes.flatMap((r) => ordonner(r.versions).map((v) => ({ ...v, nomRegime: r.nom })));
  const { donnee: catalogue } = useCharge(() => api.get<CatalogueHypotheses>("/referentiel/hypotheses"), []);
  // La dernière étude donne l'effet de chaque hypothèse mesuré sur l'entreprise.
  const derniere = d.etudes[0]?.id;
  const { donnee: precedente } = useCharge(
    () => (derniere ? api.get<Etude>(`/organisations/${d.org.id}/etudes/${derniere}`) : Promise.resolve(null)), [derniere]);
  const [saisie, setSaisie] = useState<SaisieHypotheses | null>(null);
  const [justification, setJustification] = useState(params.get("justification") ?? "");
  const hypotheses = saisie ?? (catalogue ? saisieParDefaut(catalogue, proposee ? { taux_turnover: Number(proposee) } : {}) : null);
  const envoi = catalogue && hypotheses ? aEnvoyer(catalogue, hypotheses) : {};
  const ajustees = Object.keys(envoi).length > 0;

  async function lancer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const version = f.get("regime_version_id") as string;
    setErreur(null);
    try {
      const e = await api.post<Etude>(`/organisations/${d.org.id}/etudes`, {
        fichier_id: f.get("fichier_id"), date_evaluation: f.get("date_evaluation"),
        fonds_disponible: Number(f.get("fonds_disponible") || 0),
        ...(ajustees ? { hypotheses: envoi, justification } : {}),
        ...(version ? { regime_version_id: version } : { convention_code: f.get("convention_code") }),
      });
      d.recharger();
      naviguer(e.id);
    } catch (e) { setErreur(e); }
  }

  return (
    <>
      <h1>Évaluer votre engagement</h1>
      <p>La dette actuarielle, la charge de l'année, la cotisation à verser. Votre conseiller relit et émet le rapport,
        scellé et vérifiable.</p>
      {d.role !== "lecteur_client" && d.fichiers.length > 0 && (
        <form className="carte formulaire" onSubmit={lancer}>
          <div className="grille g4">
            <label>Personnel
              <select name="fichier_id">{d.fichiers.map((f) => <option key={f.id} value={f.id}>{f.nom_fichier}</option>)}</select>
            </label>
            <label>Date d'évaluation (une clôture)
              <input name="date_evaluation" type="date" required defaultValue={d.fichiers[0]?.date_donnees} />
            </label>
            <label>Base
              <select name="regime_version_id" defaultValue={versions.find(enCours)?.id ?? ""}>
                <option value="">la convention seule</option>
                {versions.map((v) => <option key={v.id} value={v.id}>{libelleVersion(v, v.nomRegime)}</option>)}
              </select>
            </label>
            <label>Convention (sans régime)<input name="convention_code" defaultValue={CONVENTION_PAR_PAYS[d.org.pays]} /></label>
          </div>
          <label style={{ maxWidth: 260 }}>Fonds déjà constitué (F)<input name="fonds_disponible" type="number" min={0} defaultValue={0} /></label>
          {proposee && (
            <div className="constat informe section">
              <div className="titre">Rotation proposée par l'expérience réelle</div>
              <p>Elle est reprise dans les hypothèses ci-dessous : la relire, la justifier, puis calculer.</p>
            </div>
          )}
          {catalogue && hypotheses && (
            <Hypotheses catalogue={catalogue} saisie={hypotheses} onChange={setSaisie} lues={precedente?.hypotheses.lues}
                        ouvert={Boolean(proposee)} />
          )}
          {ajustees && (
            <label className="section">Justification des hypothèses ajustées (figurera au rapport)
              <input name="justification" required value={justification} onChange={(e) => setJustification(e.target.value)} />
            </label>
          )}
          <div className="actions"><button className="principal">Calculer</button></div>
          <Erreur erreur={erreur} />
        </form>
      )}
      {d.fichiers.length === 0 && <p>Déposez d'abord le fichier de votre personnel.</p>}

      <div className="section">
        <h2>Vos études</h2>
        <div className="defile">
          <table>
            <thead><tr><th>Évaluation au</th><th>Base</th><th className="n">Dette</th><th>État</th><th aria-label="Actions" /></tr></thead>
            <tbody>
              {d.etudes.map((e) => (
                <tr key={e.id} className="cliquable" onClick={() => naviguer(e.id)}>
                  <td>{dateFr(e.date_evaluation)}</td>
                  <td>{e.convention_code}</td>
                  <td className="n">{montant(e.dette)}</td>
                  <td>{e.statut === "emise" ? <span className="etat bien">Émise le {dateFr(e.emise_le)}</span>
                    : <span className="etat attention">Brouillon</span>}</td>
                  <td className="n" onClick={(ev) => ev.stopPropagation()}>
                    <MenuActions libelle={`Actions sur l'étude au ${dateFr(e.date_evaluation)}`} actions={[
                      { libelle: "Ouvrir", agir: () => naviguer(e.id) },
                      { libelle: "Rapport PDF", cache: e.statut !== "emise",
                        agir: () => api.ouvrir(`/organisations/${d.org.id}/etudes/${e.id}/rapport`) },
                      { libelle: "Exporter en Excel", agir: () => { setErreur(null);
                        api.telecharger(`/organisations/${d.org.id}/etudes/${e.id}/export`, `etude-ifc-${e.date_evaluation}.xlsx`).catch(setErreur); } },
                      { libelle: "Supprimer ce brouillon", danger: true, cache: e.statut !== "brouillon" || d.role === "lecteur_client",
                        agir: async () => {
                          if (!window.confirm("Supprimer ce brouillon ? Il n'engage rien ; une étude émise, elle, reste.")) return;
                          setErreur(null);
                          try { await api.del(`/organisations/${d.org.id}/etudes/${e.id}`); d.recharger(); } catch (x) { setErreur(x); }
                        } },
                    ]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
