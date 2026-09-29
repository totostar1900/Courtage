import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge, Volet } from "../composants/communs";
import { EtatDuDossier } from "../composants/CycleDossier";
import { MenuActions } from "../composants/MenuActions";
import { NettoyerDossier } from "../composants/Nettoyage";
import type { Equipe as DonneesEquipe, Membre, Role } from "../types";
import { useConfirmation } from "../composants/Confirmer";
import { useDossier } from "./Dossier";
import { langue, t } from "../i18n";
import { raisonActivation } from "../activation";
import { ChampTelephone } from "../composants/ChampTelephone";

// Lus au rendu (la langue peut changer) : des fonctions, pas des constantes figées à l'import.
export const libellesRoles = (): Record<Role, string> => ({
  admin_client: t("Administrateur de l'entreprise", "Company administrator"), contributeur_client: t("Contributeur", "Contributor"),
  lecteur_client: t("Lecture seule", "Read-only"), conseiller: t("Conseiller", "Adviser"),
});

const definitions = (): Record<Role, string> => ({
  admin_client: t("décide : adopte le régime, choisit l'assureur, gère ses collègues", "decides: adopts the plan, chooses the insurer, manages colleagues"),
  contributeur_client: t("dépose le personnel, prépare régimes et études, sans adopter", "uploads the staff list, prepares plans and studies, without adopting"),
  lecteur_client: t("consulte tout, sans rien modifier", "sees everything, changes nothing"),
  conseiller: t("suit le dossier, émet les études, gère toute l'équipe", "follows the file, issues the studies, manages the whole team"),
});

/** Qui suit le dossier. Chacun voit ses collègues ; le client voit son conseiller à part, comme un contact. */
export default function Equipe() {
  const d = useDossier();
  const { donnee: e, erreur, recharger } = useCharge(() => api.get<DonneesEquipe>(`/organisations/${d.org.id}/equipe`), [d.org.id]);
  const [inscrireDemande, setInscrire] = useState<boolean | null>(null);
  const [modifier, setModifier] = useState<Membre | null>(null);
  const aller = useNavigate();
  const [demander, fenetre] = useConfirmation();
  if (erreur) return <Erreur erreur={erreur} />;
  if (!e) return <p className="discret">{t("Chargement…", "Loading…")}</p>;
  const LIBELLES_ROLES = libellesRoles(), DEFINITIONS = definitions();
  const conseil = d.role === "conseiller";
  const lignes = conseil ? e.membres : e.membres.filter((m) => m.role !== "conseiller");
  const conseillers = conseil ? [] : e.membres.filter((m) => m.role === "conseiller");
  const ouvert = (d.org.etat ?? "ouvert") === "ouvert";
  // Un dossier neuf, sans personne de l'entreprise : le formulaire s'ouvre de lui-même pour le conseiller.
  const inscrire = inscrireDemande ?? (conseil && ouvert && !e.membres.some((m) => m.role !== "conseiller"));
  const rafraichir = () => { recharger(); d.recharger(); };
  // En attente de confirmation : ni invitation, ni droits ; chacun garde la main sur sa propre fonction.
  const attente = raisonActivation(d.activation, "equipe");

  function retirer(m: Membre) {
    demander({
      titre: m.moi ? t("Vous retirer de ce dossier", "Remove yourself from this file") : t(`Retirer ${m.nom} du dossier`, `Remove ${m.nom} from the file`),
      message: <p>{m.moi ? t("Vous n'y aurez plus accès.", "You will no longer have access to it.") : t("Ce qu'il ou elle y a fait reste au journal, sous son nom.", "What they did in it stays in the log, under their name.")}</p>,
      mot: t("RETIRER", "REMOVE"), bouton: t("Retirer", "Remove"),
      action: async () => {
        await api.del(`/organisations/${d.org.id}/membres/${m.id}`);
        if (m.moi) aller("/"); else rafraichir();
      },
    });
  }

  return (
    <>
      {fenetre}
      <h1>{t("Équipe du dossier", "File team")}</h1>
      {langue() === "fr"
        ? <p>Chaque personne se connecte avec son numéro de téléphone, par un code reçu par message. Aucun mot de passe.
            Les <b>droits</b> disent ce qu'elle peut faire ; la <b>fonction</b> dit qui elle est.</p>
        : <p>Each person signs in with their phone number, using a code received by text message. No password.
            <b>Access rights</b> say what they can do; the <b>job title</b> says who they are.</p>}
      {conseillers.map((c) => (
        <div key={c.id} className="carte section conseiller-carte">
          <div className="discret">{t("Votre conseiller", "Your adviser")}</div>
          <div className="conseiller"><div className="avatar">{c.nom.slice(0, 1)}</div>
            <div><strong>{c.nom}</strong><div className="discret">{c.email ?? c.telephone}</div></div></div>
        </div>
      ))}
      <div className="defile section">
        <table>
          <thead><tr><th>{t("Nom", "Name")}</th><th>{t("Fonction", "Job title")}</th><th>{t("Droits", "Access rights")}</th><th>{t("Téléphone", "Phone")}</th><th aria-label={t("Actions", "Actions")} /></tr></thead>
          <tbody>{lignes.map((m) => (
            <tr key={m.id}>
              <td>{m.nom}{m.moi && <span className="discret">{t(" (vous)", " (you)")}</span>}</td>
              <td>{m.fonction ?? <span className="discret">—</span>}</td>
              <td title={DEFINITIONS[m.role]}>{LIBELLES_ROLES[m.role]}</td>
              <td>{m.telephone ?? m.email ?? "—"}</td>
              <td className="n">
                <MenuActions libelle={t(`Actions sur ${m.nom}`, `Actions on ${m.nom}`)} actions={[
                  { libelle: t("Modifier : nom, fonction, droits", "Edit: name, job title, access rights"), agir: () => setModifier(m), cache: !m.modifiable || !ouvert,
                    raison: m.moi ? null : attente },
                  { libelle: m.moi ? t("Me retirer du dossier", "Remove me from the file") : t("Retirer du dossier", "Remove from the file"), agir: () => retirer(m), danger: true,
                    cache: !m.modifiable || !ouvert, raison: m.retirable ? null : m.raison_retrait },
                ]} />
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p className="discret">{t("Droits :", "Access rights:")} {(Object.keys(DEFINITIONS) as Role[]).filter((r) => conseil || r !== "conseiller")
        .map((r) => `${LIBELLES_ROLES[r]}, ${DEFINITIONS[r]}`).join(" · ")}. {t("Pour changer un numéro de téléphone : retirer la personne, puis l'inscrire avec le nouveau.",
        "To change a phone number: remove the person, then add them again with the new one.")}</p>
      {e.droits_attribuables.length > 0 && ouvert && (!inscrire || attente) && (
        <div className="actions"><button type="button" className="principal" onClick={() => setInscrire(true)}
                                         disabled={!!attente} title={attente ?? undefined}>
          {t("Inscrire quelqu'un", "Add someone")}</button>
          {attente && <span className="discret">{attente}</span>}</div>
      )}
      {inscrire && !attente && <FormulaireMembre equipe={e} onFermer={() => setInscrire(false)}
                                     onFait={() => { setInscrire(false); rafraichir(); }} />}
      {modifier && <FormulaireMembre equipe={e} membre={modifier} onFermer={() => setModifier(null)}
                                     onFait={() => { setModifier(null); rafraichir(); }} />}
      <EtatDuDossier orgId={d.org.id} conseiller={conseil} onChange={d.recharger} />
      {(conseil || d.role === "admin_client") && ouvert && <NettoyerDossier orgId={d.org.id} onFait={rafraichir} />}
    </>
  );
}

function FormulaireMembre({ equipe: e, membre, onFermer, onFait }: {
  equipe: DonneesEquipe; membre?: Membre; onFermer: () => void; onFait: () => void;
}) {
  const d = useDossier();
  const [erreur, setErreur] = useState<unknown>(null);
  const droits = e.droits_attribuables;
  // Sa propre fiche, inscription en attente : la fonction (et le nom) seulement, sans toucher aux droits.
  const sansDroits = Boolean(membre?.moi && raisonActivation(d.activation, "equipe"));
  async function valider(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const corps = { nom_affiche: String(f.get("nom") ?? "").trim(), fonction: String(f.get("fonction") ?? "").trim(),
                    ...(sansDroits ? {} : { role: f.get("role") }) };
    setErreur(null);
    try {
      if (membre) await api.patch(`/organisations/${d.org.id}/membres/${membre.id}`, corps);
      else await api.post(`/organisations/${d.org.id}/membres`, { ...corps, telephone: String(f.get("telephone") ?? "").trim() });
      onFait();
    } catch (x) { setErreur(x); }
  }
  return (
    <Volet titre={membre ? t(`Modifier : ${membre.nom}`, `Edit: ${membre.nom}`) : t("Inscrire quelqu'un", "Add someone")} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={valider}>
        <div className="grille g4">
          <label>{t("Nom", "Name")}<input name="nom" required defaultValue={membre?.nom} /></label>
          <label>{t("Fonction", "Job title")}<input name="fonction" list="fonctions-equipe" placeholder={t("DRH, DG, DAF…", "HR director, CEO, CFO…")} maxLength={80}
                                defaultValue={membre?.fonction ?? ""} /></label>
          <label>{t("Droits", "Access rights")}
            <select name="role" defaultValue={membre?.role ?? droits.find((r) => r.role !== "conseiller")?.role}
                    disabled={sansDroits} title={sansDroits ? raisonActivation(d.activation, "equipe") ?? undefined : undefined}>
              {droits.map((r) => <option key={r.role} value={r.role}>{r.libelle}</option>)}
            </select>
          </label>
          {!membre && <ChampTelephone libelle={t("Téléphone", "Phone")} name="telephone" required />}
        </div>
        <datalist id="fonctions-equipe">{e.fonctions.map((x) => <option key={x} value={x} />)}</datalist>
        <p className="discret">{membre ? t("Le numéro de téléphone est l'identité de connexion : il ne se modifie pas.", "The phone number is the sign-in identity: it cannot be changed.") :
          t("La personne se connectera avec ce numéro, par un code reçu par message.", "The person will sign in with this number, using a code received by text message.")}</p>
        <div className="actions"><button className="principal">{membre ? t("Enregistrer", "Save") : t("Inscrire", "Add")}</button>
          <button type="button" onClick={onFermer}>{t("Annuler", "Cancel")}</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
