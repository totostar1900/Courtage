import { useNavigate } from "react-router-dom";

import { api, seConnecter } from "../api";
import { Erreur, useCharge } from "../composants/communs";

interface Personne { id: string; nom_affiche: string | null; email: string | null; admin_plateforme: boolean }

/** Connexion de DÉVELOPPEMENT : on choisit en tant que qui naviguer. La vraie connexion arrive à la tâche 8. */
export default function Connexion() {
  const naviguer = useNavigate();
  const { donnee, erreur } = useCharge(() => api.get<Personne[]>("/dev/utilisateurs"), []);
  return (
    <div style={{ maxWidth: 560 }}>
      <h1>Bienvenue</h1>
      <p>Version de démonstration : choisissez la personne dont vous voulez voir l'écran.</p>
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
      {donnee && donnee.length === 0 && (
        <p className="discret">Aucune personne : lancez <code>python -m courtage.demo</code>.</p>
      )}
    </div>
  );
}
