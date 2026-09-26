import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Constats, Erreur, Volet } from "../composants/communs";
import { EditeurCategories, categorieVide, resumeBareme } from "../composants/EditeurCategories";
import { dateFr } from "../format";
import type { Categorie, Constat, Version } from "../types";
import { useDossier } from "./Dossier";

const FONDEMENTS = {
  accord_entreprise: "Accord d'entreprise", contrat_travail: "Contrats de travail",
  usage: "Usage", decision_direction: "Décision de la direction",
};

export default function Regime() {
  const d = useDossier();
  const [nouveau, setNouveau] = useState(false);
  return (
    <>
      <h1>Votre régime</h1>
      <p>Ce que votre entreprise verse à ses salariés au départ en retraite. La convention collective en est le
        plancher : un régime moins favorable est enregistré tel quel et signalé, et vos salariés gardent droit à la
        convention. Sans régime propre, l'étude s'appuie sur la convention seule.</p>
      {d.regimes.map((r) => (
        <div key={r.id} className="section">
          <h2>{r.nom}</h2>
          {r.versions.map((v) => <CarteVersion key={v.id} version={v} />)}
          {d.role !== "lecteur_client" && <NouvelleVersion regimeId={r.id} />}
        </div>
      ))}
      {d.role !== "lecteur_client" && (
        <div className="section">
          {nouveau ? <NouveauRegime onFini={() => setNouveau(false)} onFermer={() => setNouveau(false)} />
            : <button className="principal" onClick={() => setNouveau(true)}>Décrire un régime</button>}
        </div>
      )}
    </>
  );
}

function CarteVersion({ version: v }: { version: Version }) {
  const d = useDossier();
  const [analyse, setAnalyse] = useState<Constat[] | null>(null);
  const [fichier, setFichier] = useState(d.fichiers[0]?.id ?? "");
  const [accepte, setAccepte] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  const nonConforme = v.constats.some((c) => c.code === "sous_le_plancher");

  async function analyser() {
    setErreur(null);
    try {
      const params = fichier ? `?fichier_id=${fichier}` : "";
      const r = await api.get<{ constats: Constat[] }>(`/organisations/${d.org.id}/regimes/versions/${v.id}/analyse${params}`);
      setAnalyse(r.constats);
    } catch (e) { setErreur(e); }
  }
  async function adopter() {
    setErreur(null);
    try {
      await api.post(`/organisations/${d.org.id}/regimes/versions/${v.id}/adoption`, { accepte_non_conformite: accepte });
      d.recharger();
    } catch (e) { setErreur(e); }
  }

  return (
    <div className="carte" style={{ marginBottom: 14 }}>
      <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <div>
          <strong>Version {v.numero}</strong> · en vigueur à partir du {dateFr(v.en_vigueur_du)}
          <div className="discret">{FONDEMENTS[v.fondement as keyof typeof FONDEMENTS]} — {v.document_reference}</div>
        </div>
        {v.statut === "adoptee"
          ? <span className="etat bien">Adoptée{v.non_conformite_acceptee && ", non-conformité assumée"}</span>
          : <span className="etat attention">En analyse</span>}
      </div>
      <div className="defile section" style={{ marginTop: 12 }}>
        <table>
          <thead><tr><th>Catégorie</th><th>Plancher</th><th>Barème</th><th>Conditions</th></tr></thead>
          <tbody>
            {v.categories.map((c: Categorie) => (
              <tr key={c.categorie}>
                <td>{c.categorie === "*" ? "Tout le personnel" : c.categorie}</td>
                <td>{c.convention_code}</td>
                <td>{resumeBareme(c)}</td>
                <td className="discret">
                  {c.anciennete_minimale ? `${c.anciennete_minimale} ans minimum · ` : ""}
                  {c.plafond_mois ? `plafond ${c.plafond_mois} mois · ` : ""}
                  {c.base_salaire === "moyenne_12_mois" ? "moyenne 12 mois" : "dernier salaire"}
                  {c.avec_primes ? " avec primes" : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Constats constats={v.constats} vide="Conforme à la convention collective." />

      <div className="actions">
        <select value={fichier} onChange={(e) => setFichier(e.target.value)} aria-label="Personnel pour l'analyse">
          <option value="">sans personnel (légalité seule)</option>
          {d.fichiers.map((f) => <option key={f.id} value={f.id}>{f.nom_fichier} ({dateFr(f.date_donnees)})</option>)}
        </select>
        <button onClick={analyser}>Analyser : légalité, pièges, coûts</button>
      </div>
      {analyse && (
        <Volet titre="Analyse" onFermer={() => setAnalyse(null)} className="section">
          <Constats constats={analyse} />
        </Volet>
      )}

      {v.statut === "analyse" && d.role === "admin_client" && (
        <div className="actions">
          {nonConforme && (
            <label style={{ display: "flex", gap: 8, fontWeight: 400 }}>
              <input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)} />
              J'ai vu que ce régime donne moins que la convention ; mes salariés gardent droit au plancher.
            </label>
          )}
          <button className="principal" onClick={adopter} disabled={nonConforme && !accepte}>Adopter cette version</button>
        </div>
      )}
      {v.statut === "analyse" && d.role === "conseiller" && (
        <p className="discret">L'adoption appartient à l'entreprise.</p>
      )}
      <Erreur erreur={erreur} />
    </div>
  );
}

function FormulaireVersion({ onValider, bouton }: { onValider: (v: object) => Promise<void>; bouton: string }) {
  const d = useDossier();
  const [categories, setCategories] = useState<Categorie[]>([categorieVide(d.org.pays)]);
  const [erreur, setErreur] = useState<unknown>(null);
  async function envoyer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await onValider({ en_vigueur_du: f.get("en_vigueur_du"), fondement: f.get("fondement"),
                        document_reference: f.get("document_reference"), categories });
      d.recharger();
    } catch (e) { setErreur(e); }
  }
  return (
    <form className="formulaire" onSubmit={envoyer}>
      <div className="grille g3">
        <label>En vigueur à partir du<input name="en_vigueur_du" type="date" required /></label>
        <label>Fondement
          <select name="fondement">{Object.entries(FONDEMENTS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        </label>
        <label>Document<input name="document_reference" required placeholder="Accord du 12/03/2015, art. 12" /></label>
      </div>
      <EditeurCategories categories={categories} onChange={setCategories} pays={d.org.pays} />
      <div className="actions"><button className="principal">{bouton}</button></div>
      <Erreur erreur={erreur} />
    </form>
  );
}

function NouveauRegime({ onFini, onFermer }: { onFini: () => void; onFermer: () => void }) {
  const d = useDossier();
  const [nom, setNom] = useState("");
  return (
    <Volet titre="Décrire un régime" onFermer={onFermer}>
      <label style={{ marginBottom: 12 }}>Nom<input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Accord IFC 2015" /></label>
      <FormulaireVersion bouton="Enregistrer pour analyse" onValider={async (v) => {
        const r = await api.post<{ id: string }>(`/organisations/${d.org.id}/regimes`, { nom: nom || "Régime IFC" });
        await api.post(`/organisations/${d.org.id}/regimes/${r.id}/versions`, v);
        onFini();
      }} />
    </Volet>
  );
}

function NouvelleVersion({ regimeId }: { regimeId: string }) {
  const d = useDossier();
  const [ouvert, setOuvert] = useState(false);
  if (!ouvert) return <button onClick={() => setOuvert(true)}>Nouvelle version</button>;
  return (
    <Volet titre="Nouvelle version" onFermer={() => setOuvert(false)}>
      <FormulaireVersion bouton="Enregistrer pour analyse" onValider={async (v) => {
        await api.post(`/organisations/${d.org.id}/regimes/${regimeId}/versions`, v);
        setOuvert(false);
      }} />
    </Volet>
  );
}
