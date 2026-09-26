import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api";
import { DecompteAlertes } from "../composants/Alertes";
import { Erreur, useCharge, Volet } from "../composants/communs";
import { ilYa, lireReprise } from "../reprise";
import type { Alerte, Moi } from "../types";

type Decomptes = Record<string, Record<Alerte["niveau"], number>>;

const ROLES = { admin_client: "Votre entreprise", lecteur_client: "En lecture", conseiller: "Vous conseillez" };

/** Les pays que la plateforme couvre : ceux de la CEMAC, dont elle connaît les conventions. */
export const PAYS_CEMAC = { CM: "Cameroun", GA: "Gabon", CG: "Congo", TD: "Tchad", CF: "Centrafrique",
                            GQ: "Guinée équatoriale" } as const;

export default function Accueil() {
  const { donnee: moi, erreur } = useCharge(() => api.get<Moi>("/moi"), []);
  const [ouvrir, setOuvrir] = useState(false);
  const { donnee: decomptes } = useCharge(
    () => api.get<Decomptes>("/alertes").catch((): Decomptes => ({})), []);
  return (
    <>
      <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>Vos dossiers</h1>
        {moi?.admin_plateforme && !ouvrir && (
          <button type="button" className="principal" onClick={() => setOuvrir(true)}>Ouvrir un dossier client</button>
        )}
      </div>
      <Erreur erreur={erreur} />
      {moi && <Reprendre moi={moi} />}
      {ouvrir && <NouveauDossier onFermer={() => setOuvrir(false)} />}
      {moi && moi.organisations.length === 0 && (
        <p>Aucun dossier pour l'instant.{moi.admin_plateforme
          && " En tant que plateforme, vous ouvrez les dossiers des clients : « Ouvrir un dossier client », puis inscrivez la DRH par son numéro."}</p>
      )}
      <div className="grille g3">
        {moi?.organisations.map((o) => (
          <Link key={o.id} to={`/dossier/${o.id}`} className="carte lien">
            <h2 style={{ marginBottom: 4 }}>{o.nom}</h2>
            <div className="discret">{PAYS_CEMAC[o.pays as keyof typeof PAYS_CEMAC] ?? o.pays} · {ROLES[o.role]}</div>
            <div style={{ marginTop: 8 }}><DecompteAlertes decompte={decomptes?.[o.id]} /></div>
          </Link>
        ))}
      </div>
    </>
  );
}

/** La dernière page ouverte, si son dossier est toujours le vôtre : un clic pour y revenir. */
function Reprendre({ moi }: { moi: Moi }) {
  const reprise = lireReprise(moi.id);
  const org = reprise && moi.organisations.find((o) => o.id === reprise.org);
  if (!reprise || !org) return null;
  return (
    <section className="carte reprendre section" aria-label="Reprendre où vous en étiez">
      <div>
        <div className="discret">Reprendre où vous en étiez · {ilYa(reprise.quand)}</div>
        <strong>{[org.nom, ...reprise.pages].join(" › ")}</strong>
      </div>
      <Link to={reprise.chemin} className="bouton principal">Reprendre</Link>
    </section>
  );
}

function NouveauDossier({ onFermer }: { onFermer: () => void }) {
  const aller = useNavigate();
  const [erreur, setErreur] = useState<unknown>(null);
  async function ouvrir(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      const org = await api.post<{ id: string }>("/organisations", {
        nom: String(f.get("nom") ?? "").trim(), pays: f.get("pays"),
        secteur: String(f.get("secteur") ?? "").trim() || null, suivre: true });
      aller(`/dossier/${org.id}/equipe`);
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre="Ouvrir un dossier client" onFermer={onFermer}>
      <form className="formulaire" onSubmit={ouvrir}>
        <p className="discret">Le dossier d'une entreprise cliente. Vous en devenez le conseiller ; vous y inscrivez
          ensuite sa DRH, qui se connectera avec son numéro.</p>
        <div className="grille g3">
          <label>Entreprise<input name="nom" required /></label>
          <label>Pays
            <select name="pays" defaultValue="CM">
              {Object.entries(PAYS_CEMAC).map(([code, nom]) => <option key={code} value={code}>{nom}</option>)}
            </select>
          </label>
          <label>Secteur<input name="secteur" placeholder="facultatif" /></label>
        </div>
        <div className="actions"><button className="principal">Ouvrir le dossier</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
