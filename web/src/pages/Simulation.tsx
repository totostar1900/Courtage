import { useState } from "react";

import { api } from "../api";
import { Constats, Erreur, Volet } from "../composants/communs";
import { EditeurCategories, CONVENTION_PAR_PAYS, categorieVide } from "../composants/EditeurCategories";
import { millions, montant, pct } from "../format";
import type { Categorie, Constat, Totaux } from "../types";
import { useDossier } from "./Dossier";

interface ResultatVariante {
  nom: string;
  erreur?: { code: string; message: string };
  totaux?: Totaux;
  cotisation_initiale?: number;
  ecart_convention?: number;
  part_cinq_premiers?: number;
  concentration?: { niveau: string; part_des_mieux_payes: number; effectif_mieux_payes: number } | null;
  constats?: Constat[];
}

export default function Simulation() {
  const d = useDossier();
  const versions = d.regimes.flatMap((r) => r.versions.map((v) => ({ ...v, nomRegime: r.nom })));
  const [fichier, setFichier] = useState(d.fichiers[0]?.id ?? "");
  const [date, setDate] = useState(d.fichiers[0]?.date_donnees ?? "");
  const [convention, setConvention] = useState(CONVENTION_PAR_PAYS[d.org.pays] ?? "");
  const [fonds, setFonds] = useState(0);
  const [choisies, setChoisies] = useState<string[]>([]);
  const [idee, setIdee] = useState<Categorie[] | null>(null);
  const [resultats, setResultats] = useState<ResultatVariante[] | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);

  async function simuler() {
    setErreur(null);
    const variantes = [
      ...choisies.map((id) => {
        const v = versions.find((x) => x.id === id)!;
        return { nom: `${v.nomRegime}, version ${v.numero}`, regime_version_id: id };
      }),
      ...(idee ? [{ nom: "Mon idée", categories: idee }] : []),
    ];
    try {
      const r = await api.post<{ resultats: ResultatVariante[] }>(`/organisations/${d.org.id}/simulations`, {
        fichier_id: fichier, date_evaluation: date, convention_code: convention, fonds_disponible: fonds, variantes });
      setResultats(r.resultats);
    } catch (e) { setErreur(e); }
  }

  if (!d.fichiers.length) return <><h1>Simuler</h1><p>Déposez d'abord le fichier de votre personnel.</p></>;

  return (
    <>
      <h1>Simuler avant de décider</h1>
      <p>Sur votre vrai personnel, la convention seule puis chaque variante, côte à côte. Rien n'est enregistré.</p>
      <div className="carte formulaire">
        <div className="grille g4">
          <label>Personnel
            <select value={fichier} onChange={(e) => setFichier(e.target.value)}>
              {d.fichiers.map((f) => <option key={f.id} value={f.id}>{f.nom_fichier}</option>)}
            </select>
          </label>
          <label>Date d'évaluation<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
          <label>Convention<input value={convention} onChange={(e) => setConvention(e.target.value)} /></label>
          <label>Fonds constitué (F)<input type="number" min={0} value={fonds} onChange={(e) => setFonds(Number(e.target.value))} /></label>
        </div>
        {versions.length > 0 && (
          <div>
            <h3>Versions à comparer</h3>
            {versions.map((v) => (
              <label key={v.id} style={{ display: "flex", gap: 8, fontWeight: 400 }}>
                <input type="checkbox" checked={choisies.includes(v.id)}
                       onChange={(e) => setChoisies(e.target.checked ? [...choisies, v.id] : choisies.filter((x) => x !== v.id))} />
                {v.nomRegime}, version {v.numero} ({v.statut === "adoptee" ? "adoptée" : "en analyse"})
              </label>
            ))}
          </div>
        )}
        {idee ? (
          <div><h3>Mon idée</h3><EditeurCategories categories={idee} onChange={setIdee} pays={d.org.pays} />
            <div className="actions"><button type="button" onClick={() => setIdee(null)}>Retirer mon idée</button></div></div>
        ) : (
          <div><button type="button" onClick={() => setIdee([categorieVide(d.org.pays)])}>Tester une idée de barème</button></div>
        )}
        <div className="actions"><button className="principal" onClick={simuler} disabled={!date}>Simuler</button></div>
        <Erreur erreur={erreur} />
      </div>

      {resultats && (
        <Volet titre="Résultats de la simulation" onFermer={() => setResultats(null)} className="section">
          <div className="grille g3">
            {resultats.map((r) => <CarteVariante key={r.nom} r={r} />)}
          </div>
        </Volet>
      )}
    </>
  );
}

function CarteVariante({ r }: { r: ResultatVariante }) {
  if (r.erreur) return <div className="carte"><h3>{r.nom}</h3><div className="erreur">{r.erreur.message}</div></div>;
  const c = r.concentration;
  return (
    <div className="carte offre">
      <h3>{r.nom}</h3>
      <div className="discret">Dette actuarielle</div>
      <div className="gros">{millions(r.totaux!.dette)}</div>
      <div className="lignes-offre">
        <div><span>Au-delà de la convention</span><strong className="chiffre">{montant(r.ecart_convention)}</strong></div>
        <div><span>Charge annuelle</span><span className="chiffre">{montant(r.totaux!.charge)}</span></div>
        <div><span>Cotisation initiale</span><span className="chiffre">{montant(r.cotisation_initiale)}</span></div>
        <div><span>Cinq premiers bénéficiaires</span><span className="chiffre">{pct(r.part_cinq_premiers, 0)}</span></div>
        {c && (
          <div><span>Aux {c.effectif_mieux_payes} mieux payés</span>
            <span className={`etat ${c.niveau === "avertit" ? "attention" : "neutre"}`}>{pct(c.part_des_mieux_payes, 0)} de l'ajout</span></div>
        )}
      </div>
      {!!r.constats?.length && <div className="section"><Constats constats={r.constats} /></div>}
    </div>
  );
}
