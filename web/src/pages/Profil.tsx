import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, seConnecter } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { useConfirmation } from "../composants/Confirmer";
import { dateFr } from "../format";
import { changerLangue, t, useLangue } from "../i18n";

interface Profil {
  id: string; nom_affiche: string | null; telephone: string | null; email: string | null; email_verifie_le: string | null;
  admin_plateforme: boolean; cree_le: string; avis_courriel: boolean; conditions: { version: string; le: string } | null;
  dossiers: { id: string; nom: string; pays: string; role: string; fonction: string | null; activation: string }[];
  sessions: { id: string; cree_le: string; derniere_activite: string; agent: string | null; courante: boolean }[];
}

const roles = (): Record<string, string> => ({
  admin_client: t("Administrateur de l'entreprise", "Company administrator"),
  contributeur_client: t("Contributeur", "Contributor"), lecteur_client: t("Lecture seule", "Read-only"),
  conseiller: t("Conseiller", "Adviser"),
});

/** Un appareil, lisible : « Chrome · Windows » plutôt qu'une chaîne d'agent. */
function appareil(agent: string | null): string {
  if (!agent) return t("Appareil inconnu", "Unknown device");
  const navigateur = /Edg\//.test(agent) ? "Edge" : /Chrome\//.test(agent) ? "Chrome" : /Firefox\//.test(agent) ? "Firefox"
    : /Safari\//.test(agent) ? "Safari" : t("Navigateur", "Browser");
  const systeme = /Android/.test(agent) ? "Android" : /iPhone|iPad/.test(agent) ? "iOS" : /Windows/.test(agent) ? "Windows"
    : /Mac OS/.test(agent) ? "macOS" : /Linux/.test(agent) ? "Linux" : "";
  return systeme ? `${navigateur} · ${systeme}` : navigateur;
}

/** L'espace personnel : l'identité, les dossiers, la langue, les appareils connectés. */
export default function Profil() {
  const { donnee: p, erreur, recharger } = useCharge(() => api.get<Profil>("/moi/profil"), []);
  const [modifier, setModifier] = useState(false);
  const [erreurAction, setErreurAction] = useState<unknown>(null);
  const [demander, fenetre] = useConfirmation();
  const l = useLangue();
  const aller = useNavigate();
  if (erreur) return <Erreur erreur={erreur} />;
  if (!p) return <p className="discret">{t("Chargement…", "Loading…")}</p>;
  const autres = p.sessions.filter((s) => !s.courante);

  async function enregistrer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const nom = String(new FormData(ev.currentTarget).get("nom") ?? "").trim();
    setErreurAction(null);
    try { await api.patch("/moi/profil", { nom_affiche: nom }); setModifier(false); recharger(); }
    catch (e) { setErreurAction(e); }
  }

  async function deconnecter() {
    await api.post("/auth/deconnexion").catch(() => undefined);
    seConnecter(null);
    aller("/connexion");
  }

  return (
    <div className="profil">
      {fenetre}
      <h1>{t("Mon profil", "My profile")}</h1>

      <section className="carte section" aria-labelledby="profil-identite">
        <h2 id="profil-identite" style={{ marginTop: 0 }}>{t("Identité", "Identity")}</h2>
        {modifier ? (
          <form className="formulaire" onSubmit={enregistrer}>
            <label>{t("Nom affiché", "Display name")}<input name="nom" defaultValue={p.nom_affiche ?? ""} minLength={2} maxLength={120} required /></label>
            <div className="actions"><button className="principal">{t("Enregistrer", "Save")}</button>
              <button type="button" onClick={() => setModifier(false)}>{t("Annuler", "Cancel")}</button></div>
            <Erreur erreur={erreurAction} />
          </form>
        ) : (
          <div className="lignes-offre">
            <div><span>{t("Nom", "Name")}</span><strong>{p.nom_affiche ?? "—"}</strong></div>
            <div><span>{t("Téléphone", "Phone")}</span><span>{p.telephone ?? "—"}{p.telephone && <span className="etat bien" style={{ marginLeft: 8 }}>{t("vérifié", "verified")}</span>}</span></div>
            <div><span>{t("Courriel", "Email")}</span><span>{p.email ?? "—"}{p.email_verifie_le && <span className="etat bien" style={{ marginLeft: 8 }}>{t("vérifié", "verified")}</span>}</span></div>
            <div><span>{t("Compte créé le", "Account created on")}</span><span>{dateFr(p.cree_le)}</span></div>
            {p.conditions && <div><span>{t("Conditions acceptées", "Terms accepted")}</span>
              <span><Link to="/conditions">{p.conditions.version}</Link> · {dateFr(p.conditions.le)}</span></div>}
          </div>
        )}
        {!modifier && <div className="actions"><button onClick={() => setModifier(true)}>{t("Modifier mon nom", "Change my name")}</button></div>}
        <p className="discret">{t("Votre téléphone et votre courriel vous identifient : pour les changer, écrivez à votre conseiller.",
          "Your phone and email identify you: to change them, write to your adviser.")}</p>
      </section>

      <section className="carte section" aria-labelledby="profil-dossiers">
        <h2 id="profil-dossiers" style={{ marginTop: 0 }}>{t("Mes dossiers", "My files")}</h2>
        {p.dossiers.length === 0 ? <p className="discret">{t("Aucun dossier.", "No files.")}</p> : (
          <ul className="liste-simple">
            {p.dossiers.map((d) => (
              <li key={d.id}><Link to={`/dossier/${d.id}`}>{d.nom}</Link>
                <span className="discret"> · {roles()[d.role] ?? d.role}{d.fonction ? ` · ${d.fonction}` : ""}</span>
                {d.activation !== "confirmee" && <span className="etat attention" style={{ marginLeft: 8 }}>
                  {d.activation === "en_attente" ? t("en attente de confirmation", "awaiting confirmation") : t("refusée", "refused")}</span>}</li>
            ))}
          </ul>
        )}
        {p.admin_plateforme && <p className="discret">{t("Vous administrez la plateforme.", "You administer the platform.")}</p>}
      </section>

      <section className="carte section" aria-labelledby="profil-preferences">
        <h2 id="profil-preferences" style={{ marginTop: 0 }}>{t("Préférences", "Preferences")}</h2>
        <fieldset className="choix-langue"><legend>{t("Langue de l'interface", "Interface language")}</legend>
          <label className="case"><input type="radio" name="langue" checked={l === "fr"} onChange={() => changerLangue("fr")} /> Français</label>
          <label className="case"><input type="radio" name="langue" checked={l === "en"} onChange={() => changerLangue("en")} /> English</label>
        </fieldset>
        <p className="discret">{t("Gardée dans ce navigateur. Les documents scellés restent en français.",
          "Kept in this browser. Sealed documents stay in French.")}</p>
        <label className="case">
          <input type="checkbox" checked={p.avis_courriel} disabled={!p.email} onChange={async (e) => {
            setErreurAction(null);
            try { await api.patch("/moi/profil", { avis_courriel: e.target.checked }); recharger(); }
            catch (err) { setErreurAction(err); }
          }} />{" "}{t("Me prévenir par courriel quand un événement m'attend (message, mandat, dossier)",
            "Email me when something is waiting for me (message, mandate, claim file)")}</label>
        <p className="discret">{p.email
          ? t("Le courriel ne dit rien du dossier : il donne le lien de la page. Les avis sont en français.",
              "The email says nothing about the file: it gives the link to the page. Notices are in French.")
          : t("Aucune adresse sur votre compte : écrivez à votre conseiller pour en ajouter une.",
              "No address on your account: write to your adviser to add one.")}</p>
      </section>

      <section className="carte section" aria-labelledby="profil-securite">
        <h2 id="profil-securite" style={{ marginTop: 0 }}>{t("Appareils connectés", "Signed-in devices")}</h2>
        <div className="defile"><table>
          <thead><tr><th>{t("Appareil", "Device")}</th><th>{t("Connecté le", "Signed in on")}</th><th>{t("Dernière activité", "Last activity")}</th><th aria-label={t("Actions", "Actions")} /></tr></thead>
          <tbody>{p.sessions.map((s) => (
            <tr key={s.id}><td>{appareil(s.agent)}{s.courante && <span className="etat bien" style={{ marginLeft: 8 }}>{t("cet appareil", "this device")}</span>}</td>
              <td>{dateFr(s.cree_le)}</td><td>{dateFr(s.derniere_activite)}</td>
              <td className="n">{!s.courante && <button className="lien" onClick={async () => {
                setErreurAction(null);
                try { await api.del(`/moi/sessions/${s.id}`); recharger(); } catch (e) { setErreurAction(e); }
              }}>{t("Déconnecter", "Sign out")}</button>}</td></tr>
          ))}</tbody>
        </table></div>
        <div className="actions">
          {autres.length > 0 && <button onClick={() => demander({
            titre: t("Déconnecter les autres appareils", "Sign out other devices"),
            message: <p>{t(`${autres.length} autre(s) appareil(s) devront se reconnecter avec un code.`, `${autres.length} other device(s) will have to sign in again with a code.`)}</p>,
            bouton: t("Déconnecter", "Sign out"),
            action: async () => { await api.post("/moi/sessions/fermeture-des-autres"); recharger(); },
          })}>{t("Déconnecter les autres appareils", "Sign out other devices")}</button>}
          <button className="danger" onClick={deconnecter}>{t("Se déconnecter", "Sign out")}</button>
        </div>
        <Erreur erreur={erreurAction} />
      </section>
    </div>
  );
}
