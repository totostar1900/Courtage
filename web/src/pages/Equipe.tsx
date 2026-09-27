import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Erreur, Volet } from "../composants/communs";
import { EtatDuDossier } from "../composants/CycleDossier";
import type { Role } from "../types";
import { useDossier } from "./Dossier";

export const LIBELLES_ROLES: Record<Role, string> = {
  admin_client: "DRH de l'entreprise", lecteur_client: "Lecture seule", conseiller: "Conseiller",
};

/** Qui suit le dossier ; le conseiller y inscrit les personnes par leur numéro. */
export default function Equipe() {
  const d = useDossier();
  const [ouvert, setOuvert] = useState(d.role === "conseiller" && d.equipe.length <= 1);
  return (
    <>
      <h1>Équipe du dossier</h1>
      <p>Chaque personne se connecte avec son numéro de téléphone, par un code reçu par message. Aucun mot de passe.</p>
      <table>
        <thead><tr><th>Nom</th><th>Téléphone</th><th>Rôle</th></tr></thead>
        <tbody>{d.equipe.map((m) => (
          <tr key={m.id}><td>{m.nom}</td><td>{m.telephone ?? m.email ?? "—"}</td><td>{LIBELLES_ROLES[m.role]}</td></tr>
        ))}</tbody>
      </table>
      {d.role === "conseiller" && !ouvert && (d.org.etat ?? "ouvert") === "ouvert" && (
        <div className="actions"><button type="button" className="principal" onClick={() => setOuvert(true)}>
          Inscrire quelqu'un</button></div>
      )}
      {ouvert && <Inscrire onFermer={() => setOuvert(false)} onFait={() => { setOuvert(false); d.recharger(); }} />}
      <EtatDuDossier orgId={d.org.id} conseiller={d.role === "conseiller"} onChange={d.recharger} />
    </>
  );
}

function Inscrire({ onFermer, onFait }: { onFermer: () => void; onFait: () => void }) {
  const d = useDossier();
  const [erreur, setErreur] = useState<unknown>(null);
  async function inscrire(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await api.post(`/organisations/${d.org.id}/membres`, {
        nom_affiche: String(f.get("nom") ?? "").trim(), telephone: String(f.get("telephone") ?? "").trim(),
        role: f.get("role") });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre="Inscrire quelqu'un" onFermer={onFermer}>
      <form className="formulaire" onSubmit={inscrire}>
        <div className="grille g3">
          <label>Nom<input name="nom" required /></label>
          <label>Téléphone<input name="telephone" type="tel" required placeholder="+237 6 …" /></label>
          <label>Rôle
            <select name="role" defaultValue="admin_client">
              {Object.entries(LIBELLES_ROLES).map(([r, l]) => <option key={r} value={r}>{l}</option>)}
            </select>
          </label>
        </div>
        <p className="discret">La DRH dépose le fichier du personnel et adopte le régime ; la lecture seule consulte.</p>
        <div className="actions"><button className="principal">Inscrire</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
