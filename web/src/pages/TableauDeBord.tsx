import { Link } from "react-router-dom";

import { api } from "../api";
import { Cle, Constats, useCharge } from "../composants/communs";
import { dateFr, millions, montant } from "../format";
import { etapes } from "../parcours";
import type { Etude } from "../types";
import { useDossier } from "./Dossier";

export default function TableauDeBord() {
  const d = useDossier();
  const suivante = etapes(d.etat).find((e) => e.suivant);
  const derniere = d.etudes.find((e) => e.statut === "emise") ?? d.etudes[0];
  const { donnee: etude } = useCharge(
    () => (derniere ? api.get<Etude>(`/organisations/${d.org.id}/etudes/${derniere.id}`) : Promise.resolve(null)),
    [derniere?.id],
  );

  return (
    <>
      <h1>Où en est votre dossier</h1>
      {suivante ? (
        <div className="carte" style={{ borderColor: "var(--ocre)" }}>
          <div className="discret">Prochaine étape</div>
          <h2 style={{ margin: "4px 0" }}>{suivante.libelle}</h2>
          <p>{suivante.aide}</p>
          <Link to={suivante.cle}><button className="principal">Continuer</button></Link>
        </div>
      ) : (
        <div className="carte"><h2>Toutes les étapes sont faites.</h2>
          <p>Le cahier des charges est parti : les réponses des assureurs viendront s'y comparer.</p></div>
      )}

      {etude && (
        <div className="section">
          <h2>{etude.statut === "emise" ? "Votre engagement" : "Dernier brouillon"} au {dateFr(etude.date_evaluation)}</h2>
          <div className="grille g4">
            <Cle etiquette="Dette actuarielle" valeur={millions(etude.totaux.dette)} sous={montant(etude.totaux.dette)} />
            <Cle etiquette="Charge annuelle" valeur={millions(etude.totaux.charge)} sous="ce que coûte une année de plus" />
            <Cle etiquette="Fonds constitué" valeur={millions(etude.fonds_disponible)} />
            <Cle etiquette="Cotisation à verser" valeur={millions(etude.totaux.cotisation_totale ?? 0)}
                 sous={etude.statut === "emise" ? `rapport ${etude.rapport?.numero}` : "brouillon"} />
          </div>
          <div className="section">
            <Constats constats={etude.anomalies.filter((a) => a.niveau === "avertissement").slice(0, 3).map((a) => ({
              niveau: "avertit", code: a.code, message: a.message }))} vide="" />
          </div>
          <Link to={`etudes/${etude.id}`}>Voir l'étude complète</Link>
        </div>
      )}
    </>
  );
}
