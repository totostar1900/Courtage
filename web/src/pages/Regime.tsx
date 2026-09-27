import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api";
import { Constats, Erreur, useCharge, Volet } from "../composants/communs";
import { EditeurCategories, categorieVide, resumeBareme } from "../composants/EditeurCategories";
import ExtractionTexte from "../composants/ExtractionTexte";
import CatalogueRegimes from "../composants/CatalogueRegimes";
import { MenuActions, type Action } from "../composants/MenuActions";
import ModelesTypes from "../composants/ModelesTypes";
import PartageCatalogue from "../composants/PartageCatalogue";
import { dateFr } from "../format";
import { ordonner, periode, STATUTS, zone, ZONES } from "../regimes";
import type { CandidatMenage, Categorie, Constat, Version, VersionProposee } from "../types";
import { useDossier } from "./Dossier";

const FONDEMENTS = {
  accord_entreprise: "Accord d'entreprise", contrat_travail: "Contrats de travail",
  usage: "Usage", decision_direction: "Décision de la direction",
};

type Acte = "modifier" | "analyser" | "adopter" | "supprimer";

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
              const liste = versions.filter((v) => zone(v) === z.cle);
              if (!liste.length) return z.cle === "application"
                ? <p key={z.cle} className="discret">Aucune version adoptée : les études s'appuient sur la convention seule.</p>
                : null;
              const cartes = liste.map((v) => <CarteVersion key={v.id} version={v} />);
              return z.repliee ? (
                <details key={z.cle} className="repli section zone-versions">
                  <summary>{z.titre} ({liste.length}) : versions adoptées puis remplacées</summary>
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

/** Ce que veulent dire les statuts et les niveaux de l'analyse : un seul lexique, ouvert à la demande. */
function Reperes() {
  return (
    <details className="repli reperes section">
      <summary>Que veulent dire ces repères ?</summary>
      <h3>Une version est un brouillon ou une version adoptée</h3>
      <dl className="definitions">
        {(["analyse", "adoptee"] as const).map((s) => (
          <div key={s}>
            <dt><span className={`etat ${STATUTS[s].classe}`}>{STATUTS[s].libelle}</span></dt>
            <dd>{STATUTS[s].definition}</dd>
          </div>
        ))}
      </dl>
      <p className="discret">Les dates sont une information : une version adoptée « s'applique depuis », « s'appliquera à
        partir du » ou « a été remplacée le ». Adopter communique : la version se fige, et ses notes aux salariés et aux
        assureurs se téléchargent. Les actions de chaque version sont dans son menu ⋮.</p>
      <h3>Les niveaux de l'analyse</h3>
      <dl className="definitions">
        <div><dt><span className="etat grave">Bloquant</span></dt><dd>Empêche d'adopter ou d'évaluer tant que ce n'est pas corrigé.</dd></div>
        <div><dt><span className="etat attention">Attention</span></dt><dd>À regarder avant de décider. Un régime moins favorable que la convention s'adopte quand même, en le confirmant : les salariés gardent droit au plancher.</dd></div>
        <div><dt><span className="etat neutre">Bon à savoir</span></dt><dd>Une information : un chiffre, ou un point juridique ou fiscal à examiner avec votre conseil.</dd></div>
      </dl>
    </details>
  );
}

function CarteVersion({ version: v }: { version: Version }) {
  const d = useDossier();
  const aller = useNavigate();
  const [acte, setActe] = useState<Acte | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const S = STATUTS[v.statut];
  const brouillon = v.statut === "analyse";
  const redacteur = d.role !== "lecteur_client";
  const entreprise = d.role === "admin_client";
  const sup = v.suppression;

  async function note(nature: "salaries" | "assureurs") {
    setErreur(null);
    try {
      if (!v.notes?.[nature]) await api.post(`/organisations/${d.org.id}/regimes/versions/${v.id}/notes/${nature}`);
      api.ouvrir(`/organisations/${d.org.id}/regimes/versions/${v.id}/notes/${nature}`);
      if (!v.notes?.[nature]) d.recharger();
    } catch (e) { setErreur(e); }
  }
  async function dupliquer() {
    setErreur(null);
    try { await api.post(`/organisations/${d.org.id}/regimes/versions/${v.id}/duplication`); d.recharger(); }
    catch (e) { setErreur(e); }
  }
  const pourNote = (nature: "salaries" | "assureurs") =>
    !v.notes?.[nature] && !redacteur ? "Pas encore émise." : null;
  const actions: Action[] = brouillon ? [
    { libelle: "Modifier", agir: () => setActe("modifier"), cache: !redacteur },
    { libelle: "Dupliquer", agir: dupliquer, cache: !redacteur },
    { libelle: "Analyser : légalité, pièges, coûts", agir: () => setActe("analyser") },
    { libelle: "Comparer dans Simuler", agir: () => aller(`../simulation?version=${v.id}`) },
    { libelle: "Adopter…", agir: () => setActe("adopter"), cache: !redacteur,
      raison: entreprise ? null : "L'adoption appartient à l'administrateur de l'entreprise." },
    { libelle: sup?.brouillons ? `Supprimer (et ${sup.brouillons} étude${sup.brouillons > 1 ? "s" : ""} en brouillon)` : "Supprimer",
      agir: () => setActe("supprimer"), danger: true, cache: !redacteur },
  ] : [
    { libelle: v.notes?.salaries ? "Note aux salariés (PDF)" : "Émettre la note aux salariés (PDF)",
      agir: () => note("salaries"), raison: pourNote("salaries") },
    { libelle: v.notes?.assureurs ? "Note aux assureurs (PDF)" : "Émettre la note aux assureurs (PDF)",
      agir: () => note("assureurs"), raison: pourNote("assureurs") },
    { libelle: "Dupliquer en brouillon", agir: dupliquer, cache: !redacteur },
    { libelle: "Analyser : légalité, pièges, coûts", agir: () => setActe("analyser") },
    { libelle: "Comparer dans Simuler", agir: () => aller(`../simulation?version=${v.id}`) },
    { libelle: "Supprimer…", agir: () => setActe("supprimer"), danger: true, cache: !redacteur,
      raison: !sup?.possible ? sup?.raison ?? "Elle reste." : !entreprise ? "Revenir sur une adoption appartient à l'administrateur de l'entreprise." : null },
  ];

  return (
    <div className={`carte version version-${v.statut}${zone(v) === "historique" ? " version-passee" : ""}`}
         style={{ marginBottom: 14 }} data-statut={v.statut}>
      <div className="version-tete">
        <div>
          <strong>Version {v.numero}</strong> · {periode(v)}
          <div className="discret">{FONDEMENTS[v.fondement as keyof typeof FONDEMENTS]} — {v.document_reference}</div>
        </div>
        <div className="version-coin">
          <span className={`etat ${S.classe}`} title={S.definition}>{S.libelle}</span>
          <MenuActions actions={actions} libelle={`Actions sur la version ${v.numero}`} />
        </div>
      </div>
      {!brouillon && (v.notes?.salaries || v.notes?.assureurs) && (
        <p className="discret version-impact">Communiquée : {[v.notes?.salaries && `note aux salariés ${v.notes.salaries}`,
          v.notes?.assureurs && `note aux assureurs ${v.notes.assureurs}`].filter(Boolean).join(" · ")}.</p>
      )}
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
      {brouillon && d.role === "conseiller" && <p className="discret">L'adoption appartient à l'entreprise.</p>}
      {acte && <ActeVersion version={v} acte={acte} onFermer={() => setActe(null)} />}
      {!brouillon && zone(v) === "application" && entreprise && <PartageCatalogue version={v} />}
      <Erreur erreur={erreur} />
    </div>
  );
}

function ActeVersion({ version: v, acte, onFermer }: { version: Version; acte: Acte; onFermer: () => void }) {
  const d = useDossier();
  const [erreur, setErreur] = useState<unknown>(null);
  const [fichier, setFichier] = useState(d.fichiers[0]?.id ?? "");
  const [analyse, setAnalyse] = useState<Constat[] | null>(null);
  const [accepte, setAccepte] = useState(false);
  const nonConforme = v.constats.some((c) => c.code === "sous_le_plancher");
  const titre = { modifier: `Modifier la version ${v.numero}`, analyser: `Analyser la version ${v.numero}`,
                  adopter: `Adopter la version ${v.numero}`, supprimer: `Supprimer la version ${v.numero}` }[acte];

  if (acte === "modifier")
    return (
      <Volet titre={titre} onFermer={onFermer} className="section">
        <p className="discret">Un brouillon se corrige sur place : aucune version ne s'ajoute. Les études en brouillon qui
          s'appuient sur lui sont à recalculer.</p>
        <FormulaireVersion initial={v} bouton="Enregistrer les corrections" onValider={async (corps) => {
          await api.put(`/organisations/${d.org.id}/regimes/versions/${v.id}`, corps);
          onFermer();
        }} />
      </Volet>
    );

  if (acte === "analyser") {
    async function analyser() {
      setErreur(null);
      try {
        const params = fichier ? `?fichier_id=${fichier}` : "";
        setAnalyse((await api.get<{ constats: Constat[] }>(`/organisations/${d.org.id}/regimes/versions/${v.id}/analyse${params}`)).constats);
      } catch (e) { setErreur(e); }
    }
    return (
      <Volet titre={titre} onFermer={onFermer} className="section">
        <div className="actions">
          <select value={fichier} onChange={(e) => setFichier(e.target.value)} aria-label="Personnel pour l'analyse">
            <option value="">sans personnel (légalité seule)</option>
            {d.fichiers.map((f) => <option key={f.id} value={f.id}>{f.nom_fichier} ({dateFr(f.date_donnees)})</option>)}
          </select>
          <button className="principal" onClick={analyser}>Analyser</button>
        </div>
        {analyse && <><Constats constats={analyse} />
          <p className="discret">Les points juridiques et fiscaux sont des repères pour décider, à examiner avec votre
            conseil ; les chiffres sont calculés sur votre personnel.</p></>}
        <Erreur erreur={erreur} />
      </Volet>
    );
  }

  async function valider(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const motif = String(new FormData(ev.currentTarget).get("motif") ?? "").trim();
    setErreur(null);
    try {
      if (acte === "adopter")
        await api.post(`/organisations/${d.org.id}/regimes/versions/${v.id}/adoption`, { accepte_non_conformite: accepte });
      else await api.del(`/organisations/${d.org.id}/regimes/versions/${v.id}${motif ? `?motif=${encodeURIComponent(motif)}` : ""}`);
      onFermer();
      d.recharger();
    } catch (e) { setErreur(e); }
  }
  const reservee = !!v.suppression?.reservee_entreprise;
  const seule = d.regimes.find((r) => r.id === v.regime_id)?.versions.length === 1;
  const n = v.suppression?.brouillons ?? 0;
  return (
    <Volet titre={titre} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={valider}>
        {acte === "adopter" ? (
          <>
            <p>Adopter, c'est communiquer : la version se fige, puis ses deux notes se téléchargent depuis son menu ⋮
              — aux salariés (ce que le régime leur verse) et aux assureurs (le régime à assurer). Pour la changer
              ensuite, on la duplique en brouillon.</p>
            {nonConforme && (
              <label style={{ display: "flex", gap: 8, fontWeight: 400 }}>
                <input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)} />
                J'ai vu que ce régime donne moins que la convention ; mes salariés gardent droit au plancher.
              </label>
            )}
          </>
        ) : (
          <>
            <p>{reservee ? "Cette version est adoptée, mais rien ne la cite encore : la supprimer revient sur la décision "
              + "de l'entreprise. " : "Le brouillon disparaît. "}
              {n > 0 && `${n} étude${n > 1 ? "s" : ""} en brouillon qui s'appuie${n > 1 ? "nt" : ""} dessus ${n > 1 ? "partiront" : "partira"} avec. `}
              Le journal garde la trace de sa création et de sa suppression.{seule && " C'est la seule version de ce régime : le régime disparaît avec elle."}</p>
            <label>{reservee ? "Pourquoi revenir sur cette adoption" : "Motif (facultatif)"}
              <textarea name="motif" rows={2} maxLength={500} required={reservee} /></label>
          </>
        )}
        <div className="actions">
          <button className={acte === "supprimer" ? "danger" : "principal"}
                  disabled={acte === "adopter" && nonConforme && !accepte}>{acte === "adopter" ? "Adopter cette version" : "Supprimer"}</button>
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
          <p className="discret">Tout ce qui peut partir. Coché d'office : les brouillons sans décision depuis
            {" "}{donnee.jours_sans_decision} jours. Une version adoptée que rien ne cite est proposée, jamais cochée :
            la supprimer revient sur une décision.</p>
          <ul className="menage">
            {donnee.candidats.map((c) => (
              <li key={c.version_id}>
                <label>
                  <input type="checkbox" checked={coches.has(c.version_id)} onChange={() => basculer(c.version_id)} />
                  <span><b>{c.regime}, version {c.numero}</b>{" "}
                    <span className={`etat ${STATUTS[c.statut].classe}`}>{STATUTS[c.statut].libelle}</span>
                    <span className="discret menage-raison">{c.raison}</span></span>
                </label>
              </li>
            ))}
          </ul>
          {motifRequis && (
            <label>Pourquoi revenir sur l'adoption<textarea rows={2} maxLength={500} value={motif}
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
