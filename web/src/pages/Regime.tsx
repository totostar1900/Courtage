import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Constats, Erreur, useCharge, Volet } from "../composants/communs";
import { EditeurCategories, categorieVide, resumeBareme } from "../composants/EditeurCategories";
import ExtractionTexte from "../composants/ExtractionTexte";
import CatalogueRegimes from "../composants/CatalogueRegimes";
import ModelesTypes from "../composants/ModelesTypes";
import PartageCatalogue from "../composants/PartageCatalogue";
import { dateFr } from "../format";
import { Link } from "react-router-dom";

import { ETATS_VERSION, etatVersion, ordonner, ZONES } from "../regimes";
import type { CandidatMenage, Categorie, Constat, EtatVersion, Version, VersionProposee } from "../types";
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
      {d.regimes.length > 0 && d.role !== "lecteur_client" && <Menage />}
      {d.regimes.map((r) => {
        const versions = ordonner(r.versions);
        return (
          <div key={r.id} className="section">
            <h2>{r.nom}</h2>
            {ZONES.map((z) => {
              const liste = versions.filter((v) => z.etats.includes(etatVersion(v)));
              if (!liste.length) return z.cle === "application"
                ? <p key={z.cle} className="discret">Aucune version en application : les études s'appuient sur la convention seule.</p>
                : null;
              const cartes = liste.map((v) => <CarteVersion key={v.id} version={v} />);
              return z.repliee ? (
                <details key={z.cle} className="repli section zone-versions">
                  <summary>{z.titre} ({liste.length}) : versions remplacées ou abandonnées</summary>
                  {cartes}
                </details>
              ) : (
                <div key={z.cle} className="zone-versions">
                  <h3 className="zone-titre">{z.titre}</h3>
                  {cartes}
                </div>
              );
            })}
            {d.role !== "lecteur_client" && (
              <div className="actions">
                <NouvelleVersion regimeId={r.id} />
                <span className="discret">Pour essayer un barème sans l'enregistrer : <Link to="../simulation">Simuler</Link>.</span>
              </div>
            )}
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
        récente. Une version qui ne s'est jamais appliquée (projet, abandonnée, adoptée à venir) se supprime si rien ne la
        cite ; une version en vigueur ou remplacée reste toujours. « Faire le ménage » propose ce qui peut partir.</p>
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
  const [acte, setActe] = useState<"abandonner" | "supprimer" | "modifier" | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const etat = etatVersion(v);
  const E = ETATS_VERSION[etat];
  const nonConforme = v.constats.some((c) => c.code === "sous_le_plancher");
  const redacteur = d.role !== "lecteur_client";
  const supprimable = redacteur && !!v.suppression?.possible
    && (!v.suppression.reservee_entreprise || d.role === "admin_client");

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
            {redacteur && <button type="button" onClick={() => setActe("modifier")}>Modifier</button>}
            {redacteur && <button type="button" onClick={() => setActe("abandonner")}>Abandonner</button>}
            {supprimable && <button type="button" className="danger" onClick={() => setActe("supprimer")}>Supprimer</button>}
          </div>
          {d.role === "conseiller" && <p className="discret">L'adoption appartient à l'entreprise.</p>}
        </div>
      )}
      {etat !== "projet" && supprimable && (
        <div className="actions">
          <button type="button" className="danger" onClick={() => setActe("supprimer")}>
            {etat === "a_venir" ? "Annuler l'adoption et supprimer" : "Supprimer"}</button>
        </div>
      )}
      {redacteur && v.suppression?.bloquee_par_brouillons && <p className="discret">{v.suppression.raison}</p>}
      {acte && <ActeVersion version={v} acte={acte} onFermer={() => setActe(null)} />}
      {(etat === "en_vigueur" || etat === "a_venir") && <PartageCatalogue version={v} />}
      <Erreur erreur={erreur} />
    </div>
  );
}

function ActeVersion({ version: v, acte, onFermer }: { version: Version; acte: "abandonner" | "supprimer" | "modifier"; onFermer: () => void }) {
  const d = useDossier();
  const [erreur, setErreur] = useState<unknown>(null);
  const reservee = !!v.suppression?.reservee_entreprise;
  if (acte === "modifier")
    return (
      <Volet titre={`Modifier la version ${v.numero}`} onFermer={onFermer} className="section">
        <p className="discret">Un projet se corrige sur place : aucune version ne s'ajoute. Les études en brouillon qui
          s'appuient sur lui sont à recalculer.</p>
        <FormulaireVersion initial={v} bouton="Enregistrer les corrections" onValider={async (corps) => {
          await api.put(`/organisations/${d.org.id}/regimes/versions/${v.id}`, corps);
          onFermer();
        }} />
      </Volet>
    );
  async function valider(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const motif = String(f.get("motif") ?? "").trim();
    setErreur(null);
    try {
      if (acte === "abandonner")
        await api.post(`/organisations/${d.org.id}/regimes/versions/${v.id}/abandon`, { motif });
      else await api.del(`/organisations/${d.org.id}/regimes/versions/${v.id}${motif ? `?motif=${encodeURIComponent(motif)}` : ""}`);
      onFermer();
      d.recharger();
    } catch (e) { setErreur(e); }
  }
  const seule = d.regimes.find((r) => r.id === v.regime_id)?.versions.length === 1;
  return (
    <Volet titre={acte === "abandonner" ? `Abandonner la version ${v.numero}` : `Supprimer la version ${v.numero}`}
           onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={valider}>
        {acte === "abandonner" ? (
          <>
            <p>Le projet reste lisible, avec son motif, dans l'historique. Il ne sert plus de base à une étude et ne
              bouge plus ; il pourra être supprimé si rien ne le cite.</p>
            <label>Pourquoi ce projet n'est pas retenu<textarea name="motif" rows={2} maxLength={500} required /></label>
          </>
        ) : (
          <>
            <p>{reservee ? "Cette version est adoptée mais ne s'est jamais appliquée, et rien ne la cite : la supprimer "
              + "annule la décision de l'entreprise. " : "Elle ne s'est jamais appliquée et rien ne la cite : elle disparaît. "}
              Le journal garde la trace de sa création et de sa suppression.{seule && " C'est la seule version de ce régime : le régime disparaît avec elle."}</p>
            <label>{reservee ? "Pourquoi l'adoption est annulée" : "Motif (facultatif)"}
              <textarea name="motif" rows={2} maxLength={500} required={reservee} /></label>
          </>
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

/** « Faire le ménage » : tout ce qui peut partir, avec sa raison, coché par la plateforme quand c'est sans regret. */
function Menage() {
  const d = useDossier();
  const [ouvert, setOuvert] = useState(false);
  if (!ouvert) return (
    <div className="actions"><button type="button" onClick={() => setOuvert(true)}>Faire le ménage</button></div>
  );
  return <VoletMenage onFermer={() => setOuvert(false)} onFait={() => { setOuvert(false); d.recharger(); }} />;
}

function VoletMenage({ onFermer, onFait }: { onFermer: () => void; onFait: () => void }) {
  const d = useDossier();
  const { donnee, erreur: erreurLecture } = useCharge(
    () => api.get<{ jours_sans_decision: number; candidats: CandidatMenage[] }>(`/organisations/${d.org.id}/regimes/menage`), []);
  const [choix, setChoix] = useState<Set<string> | null>(null);
  const [motif, setMotif] = useState("");
  const [erreur, setErreur] = useState<unknown>(null);
  const [fait, setFait] = useState<{ versions: number; brouillons: number } | null>(null);
  if (erreurLecture) return <Erreur erreur={erreurLecture} />;
  if (!donnee) return null;
  const coches = choix ?? new Set(donnee.candidats.filter((c) => c.coche).map((c) => c.version_id));
  const retenus = donnee.candidats.filter((c) => coches.has(c.version_id));
  const brouillons = retenus.reduce((t, c) => t + c.brouillons.length, 0);
  const motifRequis = retenus.some((c) => c.motif_requis);
  const basculer = (id: string) => {
    const s = new Set(coches);
    if (s.has(id)) s.delete(id); else s.add(id);
    setChoix(s);
  };
  async function valider() {
    setErreur(null);
    try {
      setFait(await api.post(`/organisations/${d.org.id}/regimes/menage`,
                             { versions: retenus.map((c) => c.version_id), motif: motif.trim() || null }));
    } catch (e) { setErreur(e); }
  }
  if (fait) return (
    <Volet titre="Faire le ménage" onFermer={onFait} className="section">
      <p>{fait.versions} version{fait.versions > 1 ? "s" : ""} supprimée{fait.versions > 1 ? "s" : ""}
        {fait.brouillons ? `, avec ${fait.brouillons} étude${fait.brouillons > 1 ? "s" : ""} en brouillon` : ""}.
        Le journal en garde la trace.</p>
      <div className="actions"><button className="principal" onClick={onFait}>Fermer</button></div>
    </Volet>
  );
  return (
    <Volet titre="Faire le ménage" onFermer={onFermer} className="section">
      {donnee.candidats.length === 0 ? <p>Rien à supprimer : chaque version sert, ou attend une décision récente.</p> : (
        <>
          <p className="discret">Ce qui ne s'est jamais appliqué et que seules des études en brouillon retiennent. Coché
            d'office : les versions abandonnées et les projets sans décision depuis {donnee.jours_sans_decision} jours.
            Une adoption à venir ne l'est jamais : l'annuler est une décision.</p>
          <ul className="menage">
            {donnee.candidats.map((c) => (
              <li key={c.version_id}>
                <label>
                  <input type="checkbox" checked={coches.has(c.version_id)} onChange={() => basculer(c.version_id)} />
                  <span><b>{c.regime}, version {c.numero}</b>{" "}
                    <span className={`etat ${ETATS_VERSION[c.etat].classe}`}>{ETATS_VERSION[c.etat].libelle}</span>
                    <span className="discret menage-raison">{c.raison}</span></span>
                </label>
              </li>
            ))}
          </ul>
          {motifRequis && (
            <label>Pourquoi annuler l'adoption<textarea rows={2} maxLength={500} value={motif}
              onChange={(e) => setMotif(e.target.value)} /></label>
          )}
          <div className="actions">
            <button className="danger" onClick={valider} disabled={!retenus.length || (motifRequis && !motif.trim())}>
              {retenus.length ? `Supprimer ${retenus.length} version${retenus.length > 1 ? "s" : ""}` : "Cocher ce qui doit partir"}
              {brouillons ? ` et ${brouillons} brouillon${brouillons > 1 ? "s" : ""}` : ""}</button>
            <button type="button" onClick={onFermer}>Annuler</button>
          </div>
        </>
      )}
      <Erreur erreur={erreur} />
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
