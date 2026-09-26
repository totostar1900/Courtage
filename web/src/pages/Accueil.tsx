import { Link } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import type { Moi } from "../types";

const ROLES = { admin_client: "Votre entreprise", lecteur_client: "En lecture", conseiller: "Vous conseillez" };

export default function Accueil() {
  const { donnee: moi, erreur } = useCharge(() => api.get<Moi>("/moi"), []);
  return (
    <>
      <h1>Vos dossiers</h1>
      <Erreur erreur={erreur} />
      {moi && moi.organisations.length === 0 && (
        <p>Aucun dossier pour l'instant.{moi.admin_plateforme && " En tant que plateforme, vous ouvrez les dossiers des clients."}</p>
      )}
      <div className="grille g3">
        {moi?.organisations.map((o) => (
          <Link key={o.id} to={`/dossier/${o.id}`} className="carte lien">
            <h2 style={{ marginBottom: 4 }}>{o.nom}</h2>
            <div className="discret">{o.pays} · {ROLES[o.role]}</div>
          </Link>
        ))}
      </div>
    </>
  );
}
