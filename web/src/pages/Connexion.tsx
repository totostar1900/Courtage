import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, seConnecter } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { t } from "../i18n";

interface Personne { id: string; nom_affiche: string | null; email: string | null; admin_plateforme: boolean }

/** Connexion par téléphone : le numéro, puis le code reçu par SMS ou WhatsApp. */
export default function Connexion() {
  const naviguer = useNavigate();
  const { donnee: mode } = useCharge(() => api.get<{ mode: string }>("/auth/mode"), []);
  const [telephone, setTelephone] = useState("");
  const [codeDemande, setCodeDemande] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function demander(ev: FormEvent) {
    ev.preventDefault();
    setErreur(null);
    try {
      const r = await api.post<{ message: string }>("/auth/code", { telephone });
      setMessage(r.message);
      setCodeDemande(true);
    } catch (e) { setErreur(e); }
  }

  async function verifier(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setErreur(null);
    try {
      await api.post("/auth/verification", { telephone, code: new FormData(ev.currentTarget).get("code") });
      seConnecter(null);
      naviguer("/");
    } catch (e) { setErreur(e); }
  }

  const choixPersonne = mode?.mode === "entete_dev" || mode?.mode === "demonstration";

  return (
    <div style={{ maxWidth: 480 }}>
      <h1>{t("Connexion", "Sign in")}</h1>
      {mode?.mode !== "demonstration" && (
        <div className="carte">
          {!codeDemande ? (
            <form key="numero" className="formulaire" onSubmit={demander}>
              <p>{t("Saisissez votre numéro : vous recevez un code par message.", "Enter your number: you will receive a code by message.")}</p>
              <label>{t("Téléphone", "Phone")}
                <input id="telephone" type="tel" inputMode="tel" autoComplete="tel" required value={telephone}
                       onChange={(e) => setTelephone(e.target.value)} placeholder="6 99 12 34 56" />
              </label>
              <div className="actions"><button className="principal">{t("Recevoir un code", "Get a code")}</button></div>
            </form>
          ) : (
            // Une clé propre : sans elle, React réutiliserait le champ du numéro, qui resterait affiché dans celui du code.
            <form key="code" className="formulaire" onSubmit={verifier}>
              <p>{message}</p>
              <label>{t("Code reçu", "Code received")}
                <input id="code" name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}"
                       maxLength={6} required placeholder="123456" />
              </label>
              <div className="actions">
                <button className="principal">{t("Se connecter", "Sign in")}</button>
                <button type="button" onClick={() => { setCodeDemande(false); setErreur(null); }}>{t("Changer de numéro", "Change number")}</button>
              </div>
            </form>
          )}
          <Erreur erreur={erreur} />
        </div>
      )}
      {choixPersonne && <ChoixPersonne demo={mode?.mode === "demonstration"} />}
      <p className="section discret">{t("Première fois ? ", "First time? ")}
        <Link to="/guide">{t("Découvrez la plateforme dans le guide", "Discover the platform in the guide")}</Link>
        {t(", sans compte.", ", no account needed.")}</p>
    </div>
  );
}

/** Développement et démonstration : on choisit la personne dont on veut voir l'écran. */
function ChoixPersonne({ demo }: { demo: boolean }) {
  const naviguer = useNavigate();
  const { donnee, erreur } = useCharge(() => api.get<Personne[]>("/dev/utilisateurs"), []);
  return (
    <div className="section">
      <h2>{demo ? t("Choisissez un point de vue", "Choose a point of view") : t("Mode développement", "Development mode")}</h2>
      <p className="discret">{demo ? t("La démonstration se visite sans compte.", "The demo needs no account.")
                                   : t("Sans code : réservé au développement.", "No code: for development only.")}</p>
      <Erreur erreur={erreur} />
      <div className="grille">
        {donnee?.map((p) => (
          <button key={p.id} className="carte lien" style={{ textAlign: "left" }}
                  onClick={() => { seConnecter(p.id); naviguer("/"); }}>
            <strong>{p.nom_affiche ?? p.email}</strong>
            <div className="discret">{p.admin_plateforme ? t("Plateforme", "Platform") : p.email}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
