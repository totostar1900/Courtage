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
import { raisonActivation } from "../activation";
import { dateFr } from "../format";
import { t } from "../i18n";
import { ordonner, periode, STATUTS, zone, ZONES } from "../regimes";
import type { CandidatMenage, Categorie, Constat, Version, VersionProposee } from "../types";
import { useDossier } from "./Dossier";

const fondements = () => ({
  accord_entreprise: t("Accord d'entreprise", "Company agreement"), contrat_travail: t("Contrats de travail", "Employment contracts"),
  usage: t("Usage", "Custom and practice"), decision_direction: t("Décision de la direction", "Management decision"),
});

type Acte = "modifier" | "analyser" | "adopter" | "supprimer";

export default function Regime() {
  const d = useDossier();
  const [nouveau, setNouveau] = useState(false);
  return (
    <>
      <h1>{t("Votre régime", "Your plan")}</h1>
      <p>{t("Ce que votre entreprise verse à ses salariés au départ en retraite. La convention collective en est le "
        + "plancher : un régime moins favorable est enregistré tel quel et signalé, et vos salariés gardent droit à la "
        + "convention. Sans régime propre, l'étude s'appuie sur la convention seule.",
        "What your company pays its employees when they retire. The collective agreement is its floor: a less "
        + "favourable plan is recorded as is and flagged, and your employees remain entitled to the agreement. Without a "
        + "plan of its own, the study relies on the collective agreement alone.")}</p>
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
                ? <p key={z.cle} className="discret">{t("Aucune version adoptée : les études s'appuient sur la convention seule.",
                  "No adopted version: studies rely on the collective agreement alone.")}</p>
                : null;
              const cartes = liste.map((v) => <CarteVersion key={v.id} version={v} />);
              return z.repliee ? (
                <details key={z.cle} className="repli section zone-versions">
                  <summary>{z.titre} ({liste.length}){t(" : versions adoptées puis remplacées", ": versions adopted, then replaced")}</summary>
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
                <span className="discret">{t("Pour essayer un barème sans l'enregistrer : ", "To try a scale without saving it: ")}
                  <Link to="../simulation">{t("Simuler", "Simulate")}</Link>.</span>
              </div>
            )}
          </div>
        );
      })}
      {d.role !== "lecteur_client" && (
        <div className="section">
          {nouveau ? <NouveauRegime onFini={() => setNouveau(false)} onFermer={() => setNouveau(false)} />
            : <button className="principal" onClick={() => setNouveau(true)}>{t("Décrire un régime", "Describe a plan")}</button>}
        </div>
      )}
    </>
  );
}

/** Ce que veulent dire les statuts et les niveaux de l'analyse : un seul lexique, ouvert à la demande. */
function Reperes() {
  return (
    <details className="repli reperes section">
      <summary>{t("Que veulent dire ces repères ?", "What do these markers mean?")}</summary>
      <h3>{t("Une version est un brouillon ou une version adoptée", "A version is either a draft or an adopted version")}</h3>
      <dl className="definitions">
        {(["analyse", "adoptee"] as const).map((s) => (
          <div key={s}>
            <dt><span className={`etat ${STATUTS[s].classe}`}>{STATUTS[s].libelle}</span></dt>
            <dd>{STATUTS[s].definition}</dd>
          </div>
        ))}
      </dl>
      <p className="discret">{t("Les dates sont une information : une version adoptée « s'applique depuis », « s'appliquera à "
        + "partir du » ou « a été remplacée le ». Adopter communique : la version se fige, et ses notes aux salariés et aux "
        + "assureurs se téléchargent. Les actions de chaque version sont dans son menu ⋮.",
        "Dates are information: an adopted version “applies since”, “will apply from” or “was replaced on”. Adopting "
        + "communicates: the version is frozen, and its notices to employees and insurers can be downloaded. Each "
        + "version's actions are in its ⋮ menu.")}</p>
      <h3>{t("Les niveaux de l'analyse", "Review levels")}</h3>
      <dl className="definitions">
        <div><dt><span className="etat grave">{t("Bloquant", "Blocking")}</span></dt><dd>{t("Empêche d'adopter ou d'évaluer tant que ce n'est pas corrigé.", "Prevents adoption or valuation until it is fixed.")}</dd></div>
        <div><dt><span className="etat attention">{t("Attention", "Warning")}</span></dt><dd>{t("À regarder avant de décider. Un régime moins favorable que la convention s'adopte quand même, en le confirmant : les salariés gardent droit au plancher.", "To review before deciding. A plan less favourable than the collective agreement can still be adopted, by confirming it: employees remain entitled to the floor.")}</dd></div>
        <div><dt><span className="etat neutre">{t("Bon à savoir", "Good to know")}</span></dt><dd>{t("Une information : un chiffre, ou un point juridique ou fiscal à examiner avec votre conseil.", "Information: a figure, or a legal or tax point to review with your adviser.")}</dd></div>
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
    !v.notes?.[nature] && !redacteur ? t("Pas encore émise.", "Not issued yet.")
      : !v.notes?.[nature] ? raisonActivation(d.activation, "notes_regime") : null;
  const actions: Action[] = brouillon ? [
    { libelle: t("Modifier", "Edit"), agir: () => setActe("modifier"), cache: !redacteur },
    { libelle: t("Dupliquer", "Duplicate"), agir: dupliquer, cache: !redacteur },
    { libelle: t("Analyser : légalité, pièges, coûts", "Review: legality, pitfalls, costs"), agir: () => setActe("analyser") },
    { libelle: t("Comparer dans Simuler", "Compare in Simulate"), agir: () => aller(`../simulation?version=${v.id}`) },
    { libelle: t("Adopter…", "Adopt…"), agir: () => setActe("adopter"), cache: !redacteur,
      raison: entreprise ? null : t("L'adoption appartient à l'administrateur de l'entreprise.", "Adoption is for the company administrator.") },
    { libelle: sup?.brouillons ? t(`Supprimer (et ${sup.brouillons} étude${sup.brouillons > 1 ? "s" : ""} en brouillon)`,
        `Delete (and ${sup.brouillons} draft stud${sup.brouillons > 1 ? "ies" : "y"})`) : t("Supprimer", "Delete"),
      agir: () => setActe("supprimer"), danger: true, cache: !redacteur },
  ] : [
    { libelle: v.notes?.salaries ? t("Note aux salariés (PDF)", "Notice to employees (PDF)") : t("Émettre la note aux salariés (PDF)", "Issue the notice to employees (PDF)"),
      agir: () => note("salaries"), raison: pourNote("salaries") },
    { libelle: v.notes?.assureurs ? t("Note aux assureurs (PDF)", "Notice to insurers (PDF)") : t("Émettre la note aux assureurs (PDF)", "Issue the notice to insurers (PDF)"),
      agir: () => note("assureurs"), raison: pourNote("assureurs") },
    { libelle: t("Dupliquer en brouillon", "Duplicate as a draft"), agir: dupliquer, cache: !redacteur },
    { libelle: t("Analyser : légalité, pièges, coûts", "Review: legality, pitfalls, costs"), agir: () => setActe("analyser") },
    { libelle: t("Comparer dans Simuler", "Compare in Simulate"), agir: () => aller(`../simulation?version=${v.id}`) },
    { libelle: t("Supprimer…", "Delete…"), agir: () => setActe("supprimer"), danger: true, cache: !redacteur,
      raison: !sup?.possible ? sup?.raison ?? t("Elle reste.", "It stays.") : !entreprise ? t("Revenir sur une adoption appartient à l'administrateur de l'entreprise.", "Reversing an adoption is for the company administrator.") : null },
  ];

  return (
    <div className={`carte version version-${v.statut}${zone(v) === "historique" ? " version-passee" : ""}`}
         style={{ marginBottom: 14 }} data-statut={v.statut}>
      <div className="version-tete">
        <div>
          <strong>Version {v.numero}</strong> · {periode(v)}
          <div className="discret">{fondements()[v.fondement as keyof ReturnType<typeof fondements>]} — {v.document_reference}</div>
        </div>
        <div className="version-coin">
          <span className={`etat ${S.classe}`} title={S.definition}>{S.libelle}</span>
          <MenuActions actions={actions} libelle={t(`Actions sur la version ${v.numero}`, `Actions on version ${v.numero}`)} />
        </div>
      </div>
      {!brouillon && (v.notes?.salaries || v.notes?.assureurs) && (
        <p className="discret version-impact">{t("Communiquée : ", "Communicated: ")}{[v.notes?.salaries && t(`note aux salariés ${v.notes.salaries}`, `notice to employees ${v.notes.salaries}`),
          v.notes?.assureurs && t(`note aux assureurs ${v.notes.assureurs}`, `notice to insurers ${v.notes.assureurs}`)].filter(Boolean).join(" · ")}.</p>
      )}
      <div className="defile" style={{ marginTop: 8 }}>
        <table>
          <thead><tr><th>{t("Catégorie", "Category")}</th><th>{t("Plancher", "Floor")}</th><th>{t("Barème", "Scale")}</th>
            <th>{t("Conditions", "Conditions")}</th></tr></thead>
          <tbody>
            {v.categories.map((c: Categorie) => (
              <tr key={c.categorie}>
                <td>{c.categorie === "*" ? t("Tout le personnel", "All staff") : c.categorie}</td>
                <td>{c.convention_code}</td>
                <td>{resumeBareme(c)}</td>
                <td className="discret">
                  {c.anciennete_minimale ? t(`${c.anciennete_minimale} ans minimum · `, `${c.anciennete_minimale} years minimum · `) : ""}
                  {c.plafond_mois ? t(`plafond ${c.plafond_mois} mois · `, `cap ${c.plafond_mois} months · `) : ""}
                  {c.base_salaire === "moyenne_12_mois" ? t("moyenne 12 mois", "12-month average") : t("dernier salaire", "last salary")}
                  {c.avec_primes ? t(" avec primes", " with bonuses") : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h4 className="version-rubrique">{t("Conformité à la convention", "Compliance with the collective agreement")}</h4>
      <Constats constats={v.constats} vide={t("Conforme à la convention collective.", "Complies with the collective agreement.")} />
      {v.non_conformite_acceptee && (
        <p className="discret">{t("À l'adoption, l'entreprise a confirmé avoir vu cette non-conformité.", "On adoption, the company confirmed it had seen this non-compliance.")}</p>
      )}
      {brouillon && d.role === "conseiller" && <p className="discret">{t("L'adoption appartient à l'entreprise.", "Adoption is for the company.")}</p>}
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
  const titre = { modifier: t(`Modifier la version ${v.numero}`, `Edit version ${v.numero}`),
                  analyser: t(`Analyser la version ${v.numero}`, `Review version ${v.numero}`),
                  adopter: t(`Adopter la version ${v.numero}`, `Adopt version ${v.numero}`),
                  supprimer: t(`Supprimer la version ${v.numero}`, `Delete version ${v.numero}`) }[acte];

  if (acte === "modifier")
    return (
      <Volet titre={titre} onFermer={onFermer} className="section">
        <p className="discret">{t("Un brouillon se corrige sur place : aucune version ne s'ajoute. Les études en brouillon qui "
          + "s'appuient sur lui sont à recalculer.",
          "A draft is corrected in place: no version is added. Draft studies based on it need to be recalculated.")}</p>
        <FormulaireVersion initial={v} bouton={t("Enregistrer les corrections", "Save the corrections")} onValider={async (corps) => {
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
          <select value={fichier} onChange={(e) => setFichier(e.target.value)} aria-label={t("Personnel pour l'analyse", "Staff for the review")}>
            <option value="">{t("sans personnel (légalité seule)", "no staff (legality only)")}</option>
            {d.fichiers.map((f) => <option key={f.id} value={f.id}>{f.nom_fichier} ({dateFr(f.date_donnees)})</option>)}
          </select>
          <button className="principal" onClick={analyser}>{t("Analyser", "Review")}</button>
        </div>
        {analyse && <><Constats constats={analyse} />
          <p className="discret">{t("Les points juridiques et fiscaux sont des repères pour décider, à examiner avec votre "
            + "conseil ; les chiffres sont calculés sur votre personnel.",
            "Legal and tax points are guides for the decision, to review with your adviser; the figures are calculated on your staff.")}</p></>}
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
            <p>{t("Adopter, c'est communiquer : la version se fige, puis ses deux notes se téléchargent depuis son menu ⋮ "
              + "— aux salariés (ce que le régime leur verse) et aux assureurs (le régime à assurer). Pour la changer "
              + "ensuite, on la duplique en brouillon.",
              "Adopting means communicating: the version is frozen, then its two notices can be downloaded from its ⋮ menu "
              + "— to employees (what the plan pays them) and to insurers (the plan to insure). To change it later, "
              + "duplicate it as a draft.")}</p>
            {nonConforme && (
              <label style={{ display: "flex", gap: 8, fontWeight: 400 }}>
                <input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)} />
                {t("J'ai vu que ce régime donne moins que la convention ; mes salariés gardent droit au plancher.",
                  "I have seen that this plan gives less than the collective agreement; my employees remain entitled to the floor.")}
              </label>
            )}
          </>
        ) : (
          <>
            <p>{reservee ? t("Cette version est adoptée, mais rien ne la cite encore : la supprimer revient sur la décision "
              + "de l'entreprise. ", "This version is adopted, but nothing refers to it yet: deleting it reverses the "
              + "company's decision. ") : t("Le brouillon disparaît. ", "The draft disappears. ")}
              {n > 0 && t(`${n} étude${n > 1 ? "s" : ""} en brouillon qui s'appuie${n > 1 ? "nt" : ""} dessus ${n > 1 ? "partiront" : "partira"} avec. `,
                `${n} draft stud${n > 1 ? "ies" : "y"} based on it will go with it. `)}
              {t("Le journal garde la trace de sa création et de sa suppression.", "The log keeps a record of its creation and deletion.")}
              {seule && t(" C'est la seule version de ce régime : le régime disparaît avec elle.",
                " This is the plan's only version: the plan disappears with it.")}</p>
            <label>{reservee ? t("Pourquoi revenir sur cette adoption", "Why reverse this adoption") : t("Motif (facultatif)", "Reason (optional)")}
              <textarea name="motif" rows={2} maxLength={500} required={reservee} /></label>
          </>
        )}
        <div className="actions">
          <button className={acte === "supprimer" ? "danger" : "principal"}
                  disabled={acte === "adopter" && nonConforme && !accepte}>{acte === "adopter" ? t("Adopter cette version", "Adopt this version") : t("Supprimer", "Delete")}</button>
          <button type="button" onClick={onFermer}>{t("Annuler", "Cancel")}</button>
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
    <div className="actions"><button type="button" onClick={() => setOuvert(true)}>{t("Faire le ménage", "Clean up")}</button></div>
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
  const brouillons = retenus.reduce((n, c) => n + c.brouillons.length, 0);
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
    <Volet titre={t("Faire le ménage", "Clean up")} onFermer={onFait} className="section">
      <p>{t(`${fait.versions} version${fait.versions > 1 ? "s" : ""} supprimée${fait.versions > 1 ? "s" : ""}`,
        `${fait.versions} version${fait.versions > 1 ? "s" : ""} deleted`)}
        {fait.brouillons ? t(`, avec ${fait.brouillons} étude${fait.brouillons > 1 ? "s" : ""} en brouillon`,
          `, with ${fait.brouillons} draft stud${fait.brouillons > 1 ? "ies" : "y"}`) : ""}.
        {" "}{t("Le journal en garde la trace.", "The log keeps a record of it.")}</p>
      <div className="actions"><button className="principal" onClick={onFait}>{t("Fermer", "Close")}</button></div>
    </Volet>
  );
  return (
    <Volet titre={t("Faire le ménage", "Clean up")} onFermer={onFermer} className="section">
      {donnee.candidats.length === 0 ? <p>{t("Rien à supprimer : chaque version sert, ou attend une décision récente.",
        "Nothing to delete: every version is in use, or awaits a recent decision.")}</p> : (
        <>
          <p className="discret">{t(`Tout ce qui peut partir. Coché d'office : les brouillons sans décision depuis ${donnee.jours_sans_decision} jours. `
            + "Une version adoptée que rien ne cite est proposée, jamais cochée : la supprimer revient sur une décision.",
            `Everything that can go. Ticked by default: drafts with no decision for ${donnee.jours_sans_decision} days. `
            + "An adopted version that nothing refers to is offered, never ticked: deleting it reverses a decision.")}</p>
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
            <label>{t("Pourquoi revenir sur l'adoption", "Why reverse the adoption")}<textarea rows={2} maxLength={500} value={motif}
              onChange={(e) => setMotif(e.target.value)} /></label>
          )}
          <div className="actions">
            <button className="danger" onClick={valider} disabled={!retenus.length || (motifRequis && !motif.trim())}>
              {retenus.length ? t(`Supprimer ${retenus.length} version${retenus.length > 1 ? "s" : ""}`,
                `Delete ${retenus.length} version${retenus.length > 1 ? "s" : ""}`) : t("Cocher ce qui doit partir", "Tick what should go")}
              {brouillons ? t(` et ${brouillons} brouillon${brouillons > 1 ? "s" : ""}`, ` and ${brouillons} draft${brouillons > 1 ? "s" : ""}`) : ""}</button>
            <button type="button" onClick={onFermer}>{t("Annuler", "Cancel")}</button>
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
        <label>{t("En vigueur à partir du", "In force from")}<input name="en_vigueur_du" type="date" required defaultValue={initial?.en_vigueur_du ?? undefined} /></label>
        <label>{t("Fondement", "Legal basis")}
          <select name="fondement" defaultValue={initial?.fondement}>{Object.entries(fondements()).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        </label>
        <label>{t("Document", "Document")}<input name="document_reference" required placeholder={t("Accord du 12/03/2015, art. 12", "Agreement of 12/03/2015, art. 12")} defaultValue={initial?.document_reference} /></label>
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
    <Volet titre={t("Décrire un régime", "Describe a plan")} onFermer={onFermer}>
      <ModelesTypes onReprendre={(v) => { setInitial({ v, n: (initial?.n ?? 0) + 1 }); if (!nom) setNom(t("Régime IFC", "IFC plan")); }} />
      <CatalogueRegimes onReprendre={(v) => { setInitial({ v, n: (initial?.n ?? 0) + 1 }); if (!nom) setNom(t("Régime IFC", "IFC plan")); }} />
      <ExtractionTexte onReprendre={(v) => { setInitial({ v, n: (initial?.n ?? 0) + 1 }); if (!nom) setNom(v.document_reference); }} />
      <label style={{ marginBottom: 12 }}>{t("Nom", "Name")}<input value={nom} onChange={(e) => setNom(e.target.value)} placeholder={t("Accord IFC 2015", "IFC agreement 2015")} /></label>
      <FormulaireVersion key={initial?.n ?? 0} initial={initial?.v} bouton={t("Enregistrer pour analyse", "Save for review")} onValider={async (v) => {
        const r = await api.post<{ id: string }>(`/organisations/${d.org.id}/regimes`, { nom: nom || t("Régime IFC", "IFC plan") });
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
  if (!ouvert) return <button onClick={() => setOuvert(true)}>{t("Nouvelle version", "New version")}</button>;
  return (
    <Volet titre={t("Nouvelle version", "New version")} onFermer={() => setOuvert(false)}>
      <ModelesTypes onReprendre={(v) => setInitial({ v, n: (initial?.n ?? 0) + 1 })} />
      <CatalogueRegimes onReprendre={(v) => setInitial({ v, n: (initial?.n ?? 0) + 1 })} />
      <ExtractionTexte onReprendre={(v) => setInitial({ v, n: (initial?.n ?? 0) + 1 })} />
      <FormulaireVersion key={initial?.n ?? 0} initial={initial?.v} bouton={t("Enregistrer pour analyse", "Save for review")} onValider={async (v) => {
        await api.post(`/organisations/${d.org.id}/regimes/${regimeId}/versions`, v);
        setOuvert(false);
      }} />
    </Volet>
  );
}
