import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Constats, Erreur, Volet } from "../composants/communs";
import { EditeurCategories, categorieVide, resumeBareme } from "../composants/EditeurCategories";
import ExtractionTexte from "../composants/ExtractionTexte";
import CatalogueRegimes from "../composants/CatalogueRegimes";
import ModelesTypes from "../composants/ModelesTypes";
import PartageCatalogue from "../composants/PartageCatalogue";
import { dateFr } from "../format";
import { ACTUELS, ETATS_VERSION, etatVersion, ordonner } from "../regimes";
import type { Categorie, Constat, EtatVersion, Version, VersionProposee } from "../types";
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
      {d.regimes.length > 0 && <Reperes />}
      {d.regimes.map((r) => {
        const versions = ordonner(r.versions);
        const actuelles = versions.filter((v) => ACTUELS.includes(etatVersion(v)));
        const anciennes = versions.filter((v) => !ACTUELS.includes(etatVersion(v)));
        return (
          <div key={r.id} className="section">
            <h2>{r.nom}</h2>
            {actuelles.map((v) => <CarteVersion key={v.id} version={v} />)}
            {!actuelles.length && <p className="discret">Aucune version en vigueur ni en projet.</p>}
            {anciennes.length > 0 && (
              <details className="repli section">
                <summary>Versions précédentes ({anciennes.length}) : remplacées ou abandonnées</summary>
                {anciennes.map((v) => <CarteVersion key={v.id} version={v} />)}
              </details>
            )}
            {d.role !== "lecteur_client" && <NouvelleVersion regimeId={r.id} />}
          </div>
        );
      })}
      {d.role !== "lecteur_client" && (
        <div className="section">
          {nouveau ? <NouveauRegime onFini={() => setNouveau(false)} onFermer={() => setNouveau(false)} />
            : <button className="principal" onClick={() => setNouveau(true)}>Décrire un régime</button>}
        </div>
      )}
    </>
  );
}

/** Ce que veulent dire les états d'une version et les niveaux de l'analyse : un seul lexique, ouvert à la demande. */
function Reperes() {
  return (
    <details className="repli reperes section">
      <summary>Que veulent dire ces repères ?</summary>
      <h3>Les états d'une version</h3>
      <dl className="definitions">
        {(Object.keys(ETATS_VERSION) as EtatVersion[]).map((e) => (
          <div key={e}>
            <dt><span className={`etat ${ETATS_VERSION[e].classe}`}>{ETATS_VERSION[e].libelle}</span></dt>
            <dd>{ETATS_VERSION[e].definition} {ETATS_VERSION[e].impact} <span className="discret">{ETATS_VERSION[e].suite}</span></dd>
          </div>
        ))}
      </dl>
      <p className="discret">Le parcours : Projet → Adoptée (à venir, puis en vigueur) → Remplacée par une version plus
        récente. Un projet non retenu est abandonné, ou supprimé si aucune étude ne s'en est servie. Une version adoptée
        ne se supprime jamais : des études et des rapports la citent.</p>
      <h3>Les niveaux de l'analyse</h3>
      <dl className="definitions">
        <div><dt><span className="etat grave">Bloquant</span></dt><dd>Empêche d'adopter ou d'évaluer tant que ce n'est pas corrigé.</dd></div>
        <div><dt><span className="etat attention">Attention</span></dt><dd>À regarder avant de décider. Un régime moins favorable que la convention s'adopte quand même, en le confirmant : les salariés gardent droit au plancher.</dd></div>
        <div><dt><span className="etat neutre">Bon à savoir</span></dt><dd>Une information : un chiffre, ou un point juridique ou fiscal à examiner avec votre conseil.</dd></div>
      </dl>
    </details>
  );
}

function periode(v: Version): string {
  const e = etatVersion(v);
  if (e === "projet") return `prévue à partir du ${dateFr(v.en_vigueur_du)}`;
  if (e === "a_venir") return `en vigueur à partir du ${dateFr(v.en_vigueur_du)}`;
  if (e === "en_vigueur") return `en vigueur depuis le ${dateFr(v.en_vigueur_du)}`;
  if (e === "remplacee") return `appliquée à partir du ${dateFr(v.en_vigueur_du)}, remplacée par la version ${v.remplacee_par} le ${dateFr(v.jusqu_au)}`;
  return `abandonnée le ${dateFr(v.abandonnee_le)}`;
}

function CarteVersion({ version: v }: { version: Version }) {
  const d = useDossier();
  const [analyse, setAnalyse] = useState<Constat[] | null>(null);
  const [fichier, setFichier] = useState(d.fichiers[0]?.id ?? "");
  const [accepte, setAccepte] = useState(false);
  const [acte, setActe] = useState<"abandonner" | "supprimer" | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const etat = etatVersion(v);
  const E = ETATS_VERSION[etat];
  const nonConforme = v.constats.some((c) => c.code === "sous_le_plancher");
  const redacteur = d.role !== "lecteur_client";

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
    <div className={`carte version version-${etat}`} style={{ marginBottom: 14 }} data-etat={etat}>
      <div className="version-tete">
        <div>
          <strong>Version {v.numero}</strong> · {periode(v)}
          <div className="discret">{FONDEMENTS[v.fondement as keyof typeof FONDEMENTS]} — {v.document_reference}</div>
        </div>
        <span className={`etat ${E.classe}`} title={E.definition}>{E.libelle}</span>
      </div>
      <p className="discret version-impact">{E.impact}
        {etat === "abandonnee" && v.motif_abandon && <> Motif : « {v.motif_abandon} ».</>}</p>
      <div className="defile" style={{ marginTop: 8 }}>
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
      <h4 className="version-rubrique">Conformité à la convention</h4>
      <Constats constats={v.constats} vide="Conforme à la convention collective." />
      {v.non_conformite_acceptee && (
        <p className="discret">À l'adoption, l'entreprise a confirmé avoir vu cette non-conformité.</p>
      )}

      {etat !== "abandonnee" && (
        <div className="actions">
          <select value={fichier} onChange={(e) => setFichier(e.target.value)} aria-label="Personnel pour l'analyse">
            <option value="">sans personnel (légalité seule)</option>
            {d.fichiers.map((f) => <option key={f.id} value={f.id}>{f.nom_fichier} ({dateFr(f.date_donnees)})</option>)}
          </select>
          <button onClick={analyser}>Analyser : légalité, pièges, coûts</button>
        </div>
      )}
      {analyse && (
        <Volet titre="Analyse" onFermer={() => setAnalyse(null)} className="section">
          <Constats constats={analyse} />
          <p className="discret">Les points juridiques et fiscaux sont des repères pour décider, à examiner avec
            votre conseil ; les chiffres sont calculés sur votre personnel.</p>
        </Volet>
      )}

      {etat === "projet" && (
        <div className="version-decision">
          <h4 className="version-rubrique">La décision</h4>
          <p className="discret">{E.suite}</p>
          {d.role === "admin_client" && nonConforme && (
            <label style={{ display: "flex", gap: 8, fontWeight: 400 }}>
              <input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)} />
              J'ai vu que ce régime donne moins que la convention ; mes salariés gardent droit au plancher.
            </label>
          )}
          <div className="actions">
            {d.role === "admin_client" && (
              <button className="principal" onClick={adopter} disabled={nonConforme && !accepte}>Adopter cette version</button>
            )}
            {redacteur && <button type="button" onClick={() => setActe("abandonner")}>Abandonner</button>}
            {redacteur && !v.etudes && <button type="button" className="danger" onClick={() => setActe("supprimer")}>Supprimer</button>}
          </div>
          {d.role === "conseiller" && <p className="discret">L'adoption appartient à l'entreprise.</p>}
          {!!v.etudes && redacteur && (
            <p className="discret">{v.etudes} étude{v.etudes > 1 ? "s" : ""} s'appuie{v.etudes > 1 ? "nt" : ""} sur ce
              projet : il s'abandonne, il ne se supprime pas.</p>
          )}
        </div>
      )}
      {acte && <ActeVersion version={v} acte={acte} onFermer={() => setActe(null)} />}
      {(etat === "en_vigueur" || etat === "a_venir") && <PartageCatalogue version={v} />}
      <Erreur erreur={erreur} />
    </div>
  );
}

function ActeVersion({ version: v, acte, onFermer }: { version: Version; acte: "abandonner" | "supprimer"; onFermer: () => void }) {
  const d = useDossier();
  const [erreur, setErreur] = useState<unknown>(null);
  async function valider(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      if (acte === "abandonner")
        await api.post(`/organisations/${d.org.id}/regimes/versions/${v.id}/abandon`, { motif: String(f.get("motif") ?? "").trim() });
      else await api.del(`/organisations/${d.org.id}/regimes/versions/${v.id}`);
      onFermer();
      d.recharger();
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre={acte === "abandonner" ? `Abandonner la version ${v.numero}` : `Supprimer la version ${v.numero}`}
           onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={valider}>
        {acte === "abandonner" ? (
          <>
            <p>Le projet reste lisible, avec son motif, dans les versions précédentes. Il ne sert plus de base à une étude
              et ne bouge plus.</p>
            <label>Pourquoi ce projet n'est pas retenu<textarea name="motif" rows={2} maxLength={500} required /></label>
          </>
        ) : (
          <p>Aucune étude ne s'est servie de ce projet : il disparaît. Le journal garde la trace de sa création et de sa
            suppression.{" "}{d.regimes.find((r) => r.id === v.regime_id)?.versions.length === 1
              && "C'est la seule version de ce régime : le régime disparaît avec elle."}</p>
        )}
        <div className="actions">
          <button className={acte === "supprimer" ? "danger" : "principal"}>{acte === "abandonner" ? "Abandonner" : "Supprimer"}</button>
          <button type="button" onClick={onFermer}>Annuler</button>
        </div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}

function FormulaireVersion({ onValider, bouton, initial }:
  { onValider: (v: object) => Promise<void>; bouton: string; initial?: VersionProposee | null }) {
  const d = useDossier();
  const [categories, setCategories] = useState<Categorie[]>(initial?.categories?.length ? initial.categories : [categorieVide(d.org.pays)]);
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
        <label>En vigueur à partir du<input name="en_vigueur_du" type="date" required defaultValue={initial?.en_vigueur_du ?? undefined} /></label>
        <label>Fondement
          <select name="fondement" defaultValue={initial?.fondement}>{Object.entries(FONDEMENTS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        </label>
        <label>Document<input name="document_reference" required placeholder="Accord du 12/03/2015, art. 12" defaultValue={initial?.document_reference} /></label>
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
  const [initial, setInitial] = useState<{ v: VersionProposee; n: number } | null>(null);
  return (
    <Volet titre="Décrire un régime" onFermer={onFermer}>
      <ModelesTypes onReprendre={(v) => { setInitial({ v, n: (initial?.n ?? 0) + 1 }); if (!nom) setNom("Régime IFC"); }} />
      <CatalogueRegimes onReprendre={(v) => { setInitial({ v, n: (initial?.n ?? 0) + 1 }); if (!nom) setNom("Régime IFC"); }} />
      <ExtractionTexte onReprendre={(v) => { setInitial({ v, n: (initial?.n ?? 0) + 1 }); if (!nom) setNom(v.document_reference); }} />
      <label style={{ marginBottom: 12 }}>Nom<input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Accord IFC 2015" /></label>
      <FormulaireVersion key={initial?.n ?? 0} initial={initial?.v} bouton="Enregistrer pour analyse" onValider={async (v) => {
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
  const [initial, setInitial] = useState<{ v: VersionProposee; n: number } | null>(null);
  if (!ouvert) return <button onClick={() => setOuvert(true)}>Nouvelle version</button>;
  return (
    <Volet titre="Nouvelle version" onFermer={() => setOuvert(false)}>
      <ModelesTypes onReprendre={(v) => setInitial({ v, n: (initial?.n ?? 0) + 1 })} />
      <CatalogueRegimes onReprendre={(v) => setInitial({ v, n: (initial?.n ?? 0) + 1 })} />
      <ExtractionTexte onReprendre={(v) => setInitial({ v, n: (initial?.n ?? 0) + 1 })} />
      <FormulaireVersion key={initial?.n ?? 0} initial={initial?.v} bouton="Enregistrer pour analyse" onValider={async (v) => {
        await api.post(`/organisations/${d.org.id}/regimes/${regimeId}/versions`, v);
        setOuvert(false);
      }} />
    </Volet>
  );
}
