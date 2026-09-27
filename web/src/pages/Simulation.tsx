import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api";
import type { Variante } from "../comparatif";
import { Comparatif } from "../composants/Comparatif";
import { Constats, Erreur, Volet } from "../composants/communs";
import { EditeurCategories, CONVENTION_PAR_PAYS, categorieVide } from "../composants/EditeurCategories";
import { millions, montant, pct } from "../format";
import { t } from "../i18n";
import { libelleVersion, ordonner } from "../regimes";
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
  courbes?: Record<string, number[]>;
}

export default function Simulation() {
  const d = useDossier();
  const versions = d.regimes.flatMap((r) => ordonner(r.versions).map((v) => ({ ...v, nomRegime: r.nom })));
  const [fichier, setFichier] = useState(d.fichiers[0]?.id ?? "");
  const [date, setDate] = useState(d.fichiers[0]?.date_donnees ?? "");
  const [convention, setConvention] = useState(CONVENTION_PAR_PAYS[d.org.pays] ?? "");
  const [fonds, setFonds] = useState(0);
  // « Comparer » depuis le menu d'une version arrive ici avec la version cochée.
  const [params] = useSearchParams();
  const [choisies, setChoisies] = useState<string[]>(params.getAll("version"));
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
      ...(idee ? [{ nom: t("Mon idée", "My idea"), categories: idee }] : []),
    ];
    try {
      const r = await api.post<{ resultats: ResultatVariante[] }>(`/organisations/${d.org.id}/simulations`, {
        fichier_id: fichier, date_evaluation: date, convention_code: convention, fonds_disponible: fonds, variantes });
      setResultats(r.resultats);
    } catch (e) { setErreur(e); }
  }

  if (!d.fichiers.length) return <><h1>{t("Simuler", "Simulate")}</h1><p>{t("Déposez d'abord le fichier de votre personnel.", "Upload your staff file first.")}</p></>;

  return (
    <>
      <h1>{t("Simuler avant de décider", "Simulate before deciding")}</h1>
      <p>{t("Sur votre vrai personnel, la convention seule puis chaque variante, côte à côte. Rien n'est enregistré.",
        "On your actual staff, the collective agreement alone and then each variant, side by side. Nothing is saved.")}</p>
      <div className="carte formulaire">
        <div className="grille g4">
          <label>{t("Personnel", "Staff")}
            <select value={fichier} onChange={(e) => setFichier(e.target.value)}>
              {d.fichiers.map((f) => <option key={f.id} value={f.id}>{f.nom_fichier}</option>)}
            </select>
          </label>
          <label>{t("Date d'évaluation", "Valuation date")}<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
          <label>{t("Convention", "Collective agreement")}<input value={convention} onChange={(e) => setConvention(e.target.value)} /></label>
          <label>{t("Fonds constitué (F)", "Fund built up (F)")}<input type="number" min={0} value={fonds} onChange={(e) => setFonds(Number(e.target.value))} /></label>
        </div>
        {versions.length > 0 && (
          <div>
            <h3>{t("Versions à comparer", "Versions to compare")}</h3>
            {versions.map((v) => (
              <label key={v.id} style={{ display: "flex", gap: 8, fontWeight: 400 }}>
                <input type="checkbox" checked={choisies.includes(v.id)}
                       onChange={(e) => setChoisies(e.target.checked ? [...choisies, v.id] : choisies.filter((x) => x !== v.id))} />
                {libelleVersion(v, v.nomRegime)}
              </label>
            ))}
          </div>
        )}
        {idee ? (
          <div><h3>{t("Mon idée", "My idea")}</h3><EditeurCategories categories={idee} onChange={setIdee} pays={d.org.pays} />
            <div className="actions"><button type="button" onClick={() => setIdee(null)}>{t("Retirer mon idée", "Remove my idea")}</button></div></div>
        ) : (
          <div><button type="button" onClick={() => setIdee([categorieVide(d.org.pays)])}>{t("Tester une idée de barème", "Test a scale idea")}</button></div>
        )}
        <div className="actions"><button className="principal" onClick={simuler} disabled={!date}>{t("Simuler", "Simulate")}</button></div>
        <Erreur erreur={erreur} />
      </div>

      {resultats && (
        <Volet titre={t("Résultats de la simulation", "Simulation results")} onFermer={() => setResultats(null)} className="section">
          <div className="grille g3">
            {resultats.map((r) => <CarteVariante key={r.nom} r={r} />)}
          </div>
          <div className="section">
            <Comparatif variantes={resultats.filter((r) => !r.erreur && r.courbes) as unknown as Variante[]} />
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
      <div className="discret">{t("Dette actuarielle", "Actuarial liability")}</div>
      <div className="gros">{millions(r.totaux!.dette)}</div>
      <div className="lignes-offre">
        <div><span>{t("Au-delà de la convention", "Above the collective agreement")}</span><strong className="chiffre">{montant(r.ecart_convention)}</strong></div>
        <div><span>{t("Charge annuelle", "Annual cost")}</span><span className="chiffre">{montant(r.totaux!.charge)}</span></div>
        <div><span>{t("Cotisation initiale", "Initial contribution")}</span><span className="chiffre">{montant(r.cotisation_initiale)}</span></div>
        <div><span>{t("Cinq premiers bénéficiaires", "Top five beneficiaries")}</span><span className="chiffre">{pct(r.part_cinq_premiers, 0)}</span></div>
        {c && (
          <div><span>{t(`Aux ${c.effectif_mieux_payes} mieux payés`, `To the ${c.effectif_mieux_payes} highest paid`)}</span>
            <span className={`etat ${c.niveau === "avertit" ? "attention" : "neutre"}`}>{pct(c.part_des_mieux_payes, 0)}{t(" de l'ajout", " of the increase")}</span></div>
        )}
      </div>
      {!!r.constats?.length && <div className="section"><Constats constats={r.constats} /></div>}
    </div>
  );
}
