import { useState, type FormEvent } from "react";

import { api } from "../api";
import { useDossier } from "../pages/Dossier";
import type { Catalogue, PartageDossier, Version } from "../types";
import { Erreur, useCharge, Volet } from "./communs";

const taillePour = (effectif: number | undefined) =>
  effectif === undefined ? "50_a_250" : effectif < 50 ? "moins_de_50" : effectif <= 250 ? "50_a_250" : "plus_de_250";

/** Partager une version adoptée dans le catalogue anonyme : l'acte de l'entreprise, avec son accord. */
export default function PartageCatalogue({ version }: { version: Version }) {
  const d = useDossier();
  const { donnee: partages, recharger } = useCharge(
    () => api.get<PartageDossier[]>(`/organisations/${d.org.id}/regimes/partages`), [d.org.id]);
  const [ouvert, setOuvert] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  if (!partages) return null;
  const actif = partages.find((p) => p.actif);
  const celuiCi = actif?.version_id === version.id ? actif : null;

  async function retirer() {
    setErreur(null);
    try { await api.post(`/organisations/${d.org.id}/regimes/partages/${celuiCi!.partage_id}/retrait`); recharger(); }
    catch (e) { setErreur(e); }
  }

  return (
    <div className="partage-catalogue section">
      {celuiCi ? (
        <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
          <span>
            <span className="etat bien">Partagé anonymement</span>{" "}
            <span className="discret">{celuiCi.visible ? "visible dans le catalogue."
              : "en attente : un régime se montre quand son groupe réunit au moins cinq entreprises."}</span>
          </span>
          {d.role === "admin_client" && <button type="button" onClick={retirer}>Retirer du catalogue</button>}
        </div>
      ) : d.role === "admin_client" ? (
        !ouvert && (
          <div className="actions" style={{ marginTop: 0 }}>
            <button type="button" onClick={() => setOuvert(true)}>Partager anonymement</button>
            <span className="discret">Aider d'autres entreprises à écrire le leur, sans qu'elles sachent qui vous êtes.</span>
          </div>
        )
      ) : null}
      {ouvert && <Formulaire version={version} remplace={Boolean(actif)} onFermer={() => setOuvert(false)}
                             onFait={() => { setOuvert(false); recharger(); }} />}
      <Erreur erreur={erreur} />
    </div>
  );
}

function Formulaire({ version, remplace, onFermer, onFait }:
  { version: Version; remplace: boolean; onFermer: () => void; onFait: () => void }) {
  const d = useDossier();
  const { donnee: listes } = useCharge(() => api.get<Catalogue>("/catalogue/regimes"), []);
  const [accord, setAccord] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  async function partager(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await api.post(`/organisations/${d.org.id}/regimes/versions/${version.id}/partage`,
                     { secteur: f.get("secteur"), taille: f.get("taille"), consentement: accord });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre="Partager anonymement" onFermer={onFermer}>
      <form className="formulaire" onSubmit={partager}>
        <div className="grille g2">
          <div>
            <h4>Ce qui part</h4>
            <ul>
              <li>le barème de chaque catégorie, et ses conditions (ancienneté minimale, plafond, base de salaire) ;</li>
              <li>le pays, le secteur et la tranche de taille que vous choisissez ci-dessous ;</li>
              <li>la convention collective, montrée seulement si le secteur l'est.</li>
            </ul>
          </div>
          <div>
            <h4>Ce qui ne part pas</h4>
            <ul>
              <li>le nom de l'entreprise, ni aucun nom de personne ;</li>
              <li>le document, la note, les dates ;</li>
              <li>un nom de catégorie inhabituel, remplacé par « Catégorie A, B… ».</li>
            </ul>
          </div>
        </div>
        <p className="discret">Votre régime ne se montre que dans un groupe d'au moins cinq entreprises ; si le vôtre est
          trop petit, le groupe s'élargit (le secteur, puis le pays s'effacent). Vous pouvez le retirer à tout moment,
          pour l'avenir.{remplace && " Il remplacera le régime que vous partagez aujourd'hui."}</p>
        <div className="grille g2">
          <label>Secteur
            <select name="secteur" defaultValue="commerce">
              {Object.entries(listes?.secteurs ?? { commerce: "Commerce et distribution" }).map(([k, l]) =>
                <option key={k} value={k}>{l}</option>)}
            </select>
          </label>
          <label>Taille
            <select name="taille" defaultValue={taillePour(d.fichiers[0]?.effectif)}>
              {Object.entries(listes?.tailles ?? { moins_de_50: "moins de 50 salariés", "50_a_250": "50 à 250 salariés",
                                                   plus_de_250: "plus de 250 salariés" }).map(([k, l]) =>
                <option key={k} value={k}>{l}</option>)}
            </select>
          </label>
        </div>
        <label style={{ display: "flex", gap: 8, fontWeight: 400 }}>
          <input type="checkbox" checked={accord} onChange={(e) => setAccord(e.target.checked)} />
          <span>Au nom de l'entreprise, j'accepte de partager ce régime dans le catalogue anonyme.</span>
        </label>
        <div className="actions"><button className="principal" disabled={!accord}>Partager</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
