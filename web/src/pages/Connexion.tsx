import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, seConnecter } from "../api";
import { Erreur, useCharge } from "../composants/communs";

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
      <h1>Connexion</h1>
      {mode?.mode !== "demonstration" && (
        <div className="carte">
          {!codeDemande ? (
            <form key="numero" className="formulaire" onSubmit={demander}>
              <p>Saisissez votre numéro : vous recevez un code par message.</p>
              <label>Téléphone
                <input id="telephone" type="tel" inputMode="tel" autoComplete="tel" required value={telephone}
                       onChange={(e) => setTelephone(e.target.value)} placeholder="6 99 12 34 56" />
              </label>
              <div className="actions"><button className="principal">Recevoir un code</button></div>
            </form>
          ) : (
            // Une clé propre : sans elle, React réutiliserait le champ du numéro, qui resterait affiché dans celui du code.
            <form key="code" className="formulaire" onSubmit={verifier}>
              <p>{message}</p>
              <label>Code reçu
                <input id="code" name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}"
                       maxLength={6} required placeholder="123456" />
              </label>
              <div className="actions">
                <button className="principal">Se connecter</button>
                <button type="button" onClick={() => { setCodeDemande(false); setErreur(null); }}>Changer de numéro</button>
              </div>
            </form>
          )}
          <Erreur erreur={erreur} />
        </div>
      )}
      {choixPersonne && <ChoixPersonne demo={mode?.mode === "demonstration"} />}
      <p className="section discret">Première fois ? <Link to="/guide">Découvrez la plateforme dans le guide</Link>,
        sans compte.</p>
    </div>
  );
}

/** Développement et démonstration : on choisit la personne dont on veut voir l'écran. */
function ChoixPersonne({ demo }: { demo: boolean }) {
  const naviguer = useNavigate();
  const { donnee, erreur } = useCharge(() => api.get<Personne[]>("/dev/utilisateurs"), []);
  return (
    <div className="section">
      <h2>{demo ? "Choisissez un point de vue" : "Mode développement"}</h2>
      <p className="discret">{demo ? "La démonstration se visite sans compte." : "Sans code : réservé au développement."}</p>
      <Erreur erreur={erreur} />
      <div className="grille">
        {donnee?.map((p) => (
          <button key={p.id} className="carte lien" style={{ textAlign: "left" }}
                  onClick={() => { seConnecter(p.id); naviguer("/"); }}>
            <strong>{p.nom_affiche ?? p.email}</strong>
            <div className="discret">{p.admin_plateforme ? "Plateforme" : p.email}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
