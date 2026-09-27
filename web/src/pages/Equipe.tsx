import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge, Volet } from "../composants/communs";
import { EtatDuDossier } from "../composants/CycleDossier";
import { MenuActions } from "../composants/MenuActions";
import type { Equipe as DonneesEquipe, Membre, Role } from "../types";
import { useDossier } from "./Dossier";

export const LIBELLES_ROLES: Record<Role, string> = {
  admin_client: "Administrateur de l'entreprise", contributeur_client: "Contributeur", lecteur_client: "Lecture seule",
  conseiller: "Conseiller",
};

const DEFINITIONS: Record<Role, string> = {
  admin_client: "décide : adopte le régime, choisit l'assureur, gère ses collègues",
  contributeur_client: "dépose le personnel, prépare régimes et études, sans adopter",
  lecteur_client: "consulte tout, sans rien modifier",
  conseiller: "suit le dossier, émet les études, gère toute l'équipe",
};

/** Qui suit le dossier. Chacun voit ses collègues ; le client voit son conseiller à part, comme un contact. */
export default function Equipe() {
  const d = useDossier();
  const { donnee: e, erreur, recharger } = useCharge(() => api.get<DonneesEquipe>(`/organisations/${d.org.id}/equipe`), [d.org.id]);
  const [inscrireDemande, setInscrire] = useState<boolean | null>(null);
  const [modifier, setModifier] = useState<Membre | null>(null);
  const [erreurAction, setErreurAction] = useState<unknown>(null);
  const aller = useNavigate();
  if (erreur) return <Erreur erreur={erreur} />;
  if (!e) return <p className="discret">Chargement…</p>;
  const conseil = d.role === "conseiller";
  const lignes = conseil ? e.membres : e.membres.filter((m) => m.role !== "conseiller");
  const conseillers = conseil ? [] : e.membres.filter((m) => m.role === "conseiller");
  const ouvert = (d.org.etat ?? "ouvert") === "ouvert";
  // Un dossier neuf, sans personne de l'entreprise : le formulaire s'ouvre de lui-même pour le conseiller.
  const inscrire = inscrireDemande ?? (conseil && ouvert && !e.membres.some((m) => m.role !== "conseiller"));
  const rafraichir = () => { recharger(); d.recharger(); };

  async function retirer(m: Membre) {
    if (!window.confirm(m.moi ? "Vous retirer de ce dossier ? Vous n'y aurez plus accès." :
      `Retirer ${m.nom} du dossier ? Ce qu'il ou elle y a fait reste au journal, sous son nom.`)) return;
    setErreurAction(null);
    try {
      await api.del(`/organisations/${d.org.id}/membres/${m.id}`);
      if (m.moi) aller("/"); else rafraichir();
    } catch (x) { setErreurAction(x); }
  }

  return (
    <>
      <h1>Équipe du dossier</h1>
      <p>Chaque personne se connecte avec son numéro de téléphone, par un code reçu par message. Aucun mot de passe.
        Les <b>droits</b> disent ce qu'elle peut faire ; la <b>fonction</b> dit qui elle est.</p>
      {conseillers.map((c) => (
        <div key={c.id} className="carte section conseiller-carte">
          <div className="discret">Votre conseiller</div>
          <div className="conseiller"><div className="avatar">{c.nom.slice(0, 1)}</div>
            <div><strong>{c.nom}</strong><div className="discret">{c.email ?? c.telephone}</div></div></div>
        </div>
      ))}
      <div className="defile section">
        <table>
          <thead><tr><th>Nom</th><th>Fonction</th><th>Droits</th><th>Téléphone</th><th aria-label="Actions" /></tr></thead>
          <tbody>{lignes.map((m) => (
            <tr key={m.id}>
              <td>{m.nom}{m.moi && <span className="discret"> (vous)</span>}</td>
              <td>{m.fonction ?? <span className="discret">—</span>}</td>
              <td title={DEFINITIONS[m.role]}>{LIBELLES_ROLES[m.role]}</td>
              <td>{m.telephone ?? m.email ?? "—"}</td>
              <td className="n">
                <MenuActions libelle={`Actions sur ${m.nom}`} actions={[
                  { libelle: "Modifier : nom, fonction, droits", agir: () => setModifier(m), cache: !m.modifiable || !ouvert },
                  { libelle: m.moi ? "Me retirer du dossier" : "Retirer du dossier", agir: () => retirer(m), danger: true,
                    cache: !m.modifiable || !ouvert, raison: m.retirable ? null : m.raison_retrait },
                ]} />
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p className="discret">Droits : {(Object.keys(DEFINITIONS) as Role[]).filter((r) => conseil || r !== "conseiller")
        .map((r) => `${LIBELLES_ROLES[r]}, ${DEFINITIONS[r]}`).join(" · ")}. Pour changer un numéro de téléphone :
        retirer la personne, puis l'inscrire avec le nouveau.</p>
      {e.droits_attribuables.length > 0 && ouvert && !inscrire && (
        <div className="actions"><button type="button" className="principal" onClick={() => setInscrire(true)}>
          Inscrire quelqu'un</button></div>
      )}
      {inscrire && <FormulaireMembre equipe={e} onFermer={() => setInscrire(false)}
                                     onFait={() => { setInscrire(false); rafraichir(); }} />}
      {modifier && <FormulaireMembre equipe={e} membre={modifier} onFermer={() => setModifier(null)}
                                     onFait={() => { setModifier(null); rafraichir(); }} />}
      <Erreur erreur={erreurAction} />
      <EtatDuDossier orgId={d.org.id} conseiller={conseil} onChange={d.recharger} />
    </>
  );
}

function FormulaireMembre({ equipe: e, membre, onFermer, onFait }: {
  equipe: DonneesEquipe; membre?: Membre; onFermer: () => void; onFait: () => void;
}) {
  const d = useDossier();
  const [erreur, setErreur] = useState<unknown>(null);
  const droits = e.droits_attribuables;
  async function valider(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const corps = { nom_affiche: String(f.get("nom") ?? "").trim(), fonction: String(f.get("fonction") ?? "").trim(),
                    role: f.get("role") };
    setErreur(null);
    try {
      if (membre) await api.patch(`/organisations/${d.org.id}/membres/${membre.id}`, corps);
      else await api.post(`/organisations/${d.org.id}/membres`, { ...corps, telephone: String(f.get("telephone") ?? "").trim() });
      onFait();
    } catch (x) { setErreur(x); }
  }
  return (
    <Volet titre={membre ? `Modifier : ${membre.nom}` : "Inscrire quelqu'un"} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={valider}>
        <div className="grille g4">
          <label>Nom<input name="nom" required defaultValue={membre?.nom} /></label>
          <label>Fonction<input name="fonction" list="fonctions-equipe" placeholder="DRH, DG, DAF…" maxLength={80}
                                defaultValue={membre?.fonction ?? ""} /></label>
          <label>Droits
            <select name="role" defaultValue={membre?.role ?? droits.find((r) => r.role !== "conseiller")?.role}>
              {droits.map((r) => <option key={r.role} value={r.role}>{r.libelle}</option>)}
            </select>
          </label>
          {!membre && <label>Téléphone<input name="telephone" type="tel" required placeholder="+237 6 …" /></label>}
        </div>
        <datalist id="fonctions-equipe">{e.fonctions.map((x) => <option key={x} value={x} />)}</datalist>
        <p className="discret">{membre ? "Le numéro de téléphone est l'identité de connexion : il ne se modifie pas." :
          "La personne se connectera avec ce numéro, par un code reçu par message."}</p>
        <div className="actions"><button className="principal">{membre ? "Enregistrer" : "Inscrire"}</button>
          <button type="button" onClick={onFermer}>Annuler</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
