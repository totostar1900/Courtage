import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge, Volet } from "../composants/communs";
import { dateFr, millions, pct } from "../format";
import type { CritereConformite, ReponseAssureur, ReponsesFiche } from "../types";
import { useDossier } from "./Dossier";
import { Comparaison } from "./Financement";

const valeur = (c: CritereConformite, x: number | boolean | null) =>
  x === null ? "non renseigné" : typeof x === "boolean" ? (x ? "oui" : "non")
    : c.critere.endsWith("_jours") || c.critere.endsWith("_mois") ? String(x) : pct(x);

/** Les réponses des assureurs à un cahier des charges : confrontées, classées ; l'entreprise choisit. */
export default function Reponses() {
  const d = useDossier();
  const { fiche } = useParams();
  const base = `/organisations/${d.org.id}/fiches/${fiche}`;
  const { donnee: x, erreur, recharger } = useCharge(() => api.get<ReponsesFiche>(`${base}/reponses`), [fiche]);
  const [volet, setVolet] = useState<null | "saisir" | { corriger: ReponseAssureur }>(null);
  const [erreurExport, setErreurExport] = useState<unknown>(null);
  const numero = d.fiches.find((f) => f.id === fiche)?.numero;
  if (erreur) return <Erreur erreur={erreur} />;
  if (!x) return <p className="discret">Chargement…</p>;
  const ecrit = d.role !== "lecteur_client" && !x.choix;

  return (
    <>
      <p><Link to="..">← Cahiers des charges</Link></p>
      <h1>Réponses des assureurs</h1>
      <p className="discret">Cahier {numero} · réponses attendues avant le {dateFr(x.date_limite_reponse)}. Chaque réponse est
        confrontée aux conditions demandées, puis classée par son coût net actualisé ; la recommandée est la moins chère des
        conformes. Le choix appartient à l'entreprise.</p>
      {x.reponses.length > 0 && (
        <div className="actions" style={{ marginTop: 0 }}>
          <button type="button" onClick={() => { setErreurExport(null);
            api.telecharger(`${base}/reponses/export`, `reponses-assureurs-${numero ?? "cahier"}.xlsx`).catch(setErreurExport); }}>
            Exporter en Excel</button>
          <span className="discret">La comparaison, la conformité critère par critère et les trois scénarios de rendement.</span>
        </div>
      )}
      <Erreur erreur={erreurExport} />

      {x.choix && (
        <div className="carte section" style={{ borderColor: "var(--bien)" }} data-choix>
          <h2 style={{ marginBottom: 4 }}>Attribué à {x.choix.assureur}</h2>
          <p>Le {dateFr(x.choix.choisi_le)}{x.choix.recommandee ? ", l'offre recommandée." : "."}
            {x.choix.motif && <> Motif : « {x.choix.motif} ».</>}</p>
          {d.role === "conseiller" && <Link to={`../../contrat?assureur=${encodeURIComponent(x.choix.assureur)}`}>
            Enregistrer le contrat avec {x.choix.assureur}</Link>}
        </div>
      )}

      {ecrit && !volet && (
        <div className="actions section"><button className="principal" onClick={() => setVolet("saisir")}>Saisir une réponse</button></div>
      )}
      {volet === "saisir" && <FormulaireReponse base={base} onFermer={() => setVolet(null)} onFait={() => { setVolet(null); recharger(); }} />}
      {volet && typeof volet === "object" && (
        <FormulaireReponse base={base} corriger={volet.corriger} onFermer={() => setVolet(null)} onFait={() => { setVolet(null); recharger(); }} />
      )}

      {x.reponses.length === 0 ? <p className="section">Aucune réponse pour l'instant.</p> : (
        <div className="grille g2 section">
          {x.reponses.map((r) => (
            <CarteReponse key={r.id} r={r} base={base} recommandee={r.id === x.recommandee} ecrit={ecrit}
                          peutChoisir={d.role === "admin_client" && !x.choix}
                          onCorriger={() => setVolet({ corriger: r })} onFait={recharger} />
          ))}
        </div>
      )}

      {x.comparaison && (
        <details className="carte section repli">
          <summary>Le détail des projections (sous les trois scénarios)</summary>
          <Comparaison r={x.comparaison} />
        </details>
      )}
    </>
  );
}

function CarteReponse({ r, base, recommandee, ecrit, peutChoisir, onCorriger, onFait }: {
  r: ReponseAssureur; base: string; recommandee: boolean; ecrit: boolean; peutChoisir: boolean;
  onCorriger: () => void; onFait: () => void;
}) {
  const [motif, setMotif] = useState("");
  const [retrait, setRetrait] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  const ecarts = r.conformite.filter((c) => c.conforme === false);
  const nonDits = r.conformite.filter((c) => c.conforme === null);
  async function agir(chemin: string, corps: object) {
    setErreur(null);
    try { await api.post(`${base}/${chemin}`, corps); onFait(); } catch (e) { setErreur(e); }
  }
  return (
    <div className={`carte offre ${recommandee ? "meilleure" : ""}`} data-reponse={r.assureur}>
      {recommandee && <span className="badge">Recommandée</span>}
      <div className="actions" style={{ marginTop: recommandee ? 6 : 0, justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>{r.rang}. {r.assureur}</h3>
        {r.conforme ? <span className="etat bien">Conforme</span> : <span className="etat attention">
          {ecarts.length ? `${ecarts.length} écart${ecarts.length > 1 ? "s" : ""}` : "À compléter"}</span>}
      </div>
      <div className="discret">Reçue le {dateFr(r.recue_le)}{r.tardive && " · après la date limite"}</div>
      <div className="discret section" style={{ marginTop: 8 }}>Coût net actualisé (scénario central)</div>
      <div className="gros">{r.cout_net_actualise === null ? "—" : millions(r.cout_net_actualise)}</div>
      <table className="section"><tbody>
        {r.conformite.map((c) => (
          <tr key={c.critere}><td>{c.libelle}</td>
            <td className="n">{valeur(c, c.offert)}</td>
            <td className="n discret">{c.sens === "oui" ? "exigé" : `${c.sens === "min" ? "≥" : "≤"} ${valeur(c, c.demande as number)}`}</td>
            <td>{c.conforme === true ? <span className="etat bien">✓</span> : c.conforme === false
              ? <span className="etat grave">écart</span> : <span className="etat attention">?</span>}</td></tr>
        ))}
      </tbody></table>
      {nonDits.length > 0 && <p className="discret">Non renseigné : {nonDits.map((c) => c.libelle.toLowerCase()).join(", ")} — à demander à l'assureur.</p>}
      {r.commentaire && <p className="discret">« {r.commentaire} »</p>}
      <div className="actions">
        {r.offre && <button className="lien" onClick={() => api.ouvrir(`${base}/reponses/${r.id}/offre`)}>L'offre (PDF)</button>}
        {ecrit && <button onClick={onCorriger}>Corriger</button>}
        {ecrit && !retrait && <button onClick={() => setRetrait(true)}>Retirer</button>}
      </div>
      {retrait && (
        <div className="actions">
          <input aria-label="Motif du retrait" placeholder="L'assureur retire son offre…" value={motif} onChange={(e) => setMotif(e.target.value)} />
          <button disabled={!motif.trim()} onClick={() => agir(`reponses/${r.id}/retrait`, { motif_correction: motif })}>Confirmer le retrait</button>
        </div>
      )}
      {peutChoisir && !retrait && (
        <div className="section">
          {!recommandee && <input aria-label={`Pourquoi ${r.assureur}`} placeholder="Pourquoi cette offre plutôt que la recommandée ?"
            value={motif} onChange={(e) => setMotif(e.target.value)} style={{ width: "100%", marginBottom: 8 }} />}
          <button className="principal" disabled={!recommandee && !motif.trim()}
                  onClick={() => agir("choix", { reponse_id: r.id, motif: motif || null })}>Retenir {r.assureur}</button>
        </div>
      )}
      <Erreur erreur={erreur} />
    </div>
  );
}

function FormulaireReponse({ base, corriger, onFermer, onFait }: {
  base: string; corriger?: ReponseAssureur; onFermer: () => void; onFait: () => void;
}) {
  const [erreur, setErreur] = useState<unknown>(null);
  const [offre, setOffre] = useState<File | null>(null);
  const c = corriger;
  const pc = (v: number | null | undefined) => (v === null || v === undefined ? "" : Math.round(v * 10000) / 100);
  async function envoyer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    // Un taux saisi en % se garde tel quel : 2,8 % vaut 0,028, pas 0,027999…
    const taux = (k: string) => (String(f.get(k) ?? "") === "" ? null : Number((Number(f.get(k)) / 100).toFixed(6)));
    const entier = (k: string) => (String(f.get(k) ?? "") === "" ? null : Number(f.get(k)));
    const oui = (k: string) => (f.get(k) === "" ? null : f.get(k) === "oui");
    const donnees = {
      assureur: f.get("assureur"), recue_le: f.get("recue_le"), taux_garanti: taux("taux_garanti") ?? 0,
      participation_benefices: taux("participation_benefices") ?? 0, frais_sur_cotisations: taux("frais_sur_cotisations") ?? 0,
      frais_sur_encours: taux("frais_sur_encours") ?? 0, delai_paiement_jours: entier("delai_paiement_jours"),
      transfert_preavis_mois: entier("transfert_preavis_mois"), transfert_penalite: taux("transfert_penalite"),
      accepte_etude_plateforme: oui("accepte_etude_plateforme"), reporting_annuel: oui("reporting_annuel"),
      historique_participation: String(f.get("historique_participation") ?? "") || null,
      commentaire: String(f.get("commentaire") ?? "") || null,
      ...(c ? { motif_correction: f.get("motif_correction") } : {}),
    };
    const envoi = new FormData();
    envoi.append("donnees", JSON.stringify(donnees));
    if (offre) envoi.append("offre", offre);
    setErreur(null);
    try { await api.post(c ? `${base}/reponses/${c.id}/correction` : `${base}/reponses`, envoi); onFait(); }
    catch (e) { setErreur(e); }
  }
  const choixOui = (nom: string, v: boolean | null | undefined) => (
    <select name={nom} defaultValue={v === null || v === undefined ? "" : v ? "oui" : "non"}>
      <option value="">non renseigné</option><option value="oui">oui</option><option value="non">non</option></select>
  );
  return (
    <Volet titre={c ? `Corriger la réponse de ${c.assureur}` : "Saisir une réponse"} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={envoyer}>
        <p className="discret">La grille du cahier des charges, telle que l'assureur l'a remplie. Laissez vide ce qu'il n'a pas dit :
          c'est signalé, pas deviné.</p>
        <div className="grille g4">
          <label>Assureur<input name="assureur" required defaultValue={c?.assureur} /></label>
          <label>Reçue le<input name="recue_le" type="date" required defaultValue={c?.recue_le ?? new Date().toISOString().slice(0, 10)} /></label>
          <label>Taux garanti (%)<input name="taux_garanti" type="number" step={0.01} required defaultValue={pc(c?.taux_garanti)} /></label>
          <label>Participation (%)<input name="participation_benefices" type="number" step={0.1} required defaultValue={pc(c?.participation_benefices)} /></label>
          <label>Frais sur cotisations (%)<input name="frais_sur_cotisations" type="number" step={0.01} required defaultValue={pc(c?.frais_sur_cotisations)} /></label>
          <label>Frais sur encours (%/an)<input name="frais_sur_encours" type="number" step={0.01} required defaultValue={pc(c?.frais_sur_encours)} /></label>
          <label>Délai de paiement (jours)<input name="delai_paiement_jours" type="number" min={1} defaultValue={c?.delai_paiement_jours ?? ""} /></label>
          <label>Préavis de transfert (mois)<input name="transfert_preavis_mois" type="number" min={0} defaultValue={c?.transfert_preavis_mois ?? ""} /></label>
          <label>Pénalité de transfert (%)<input name="transfert_penalite" type="number" step={0.1} min={0} defaultValue={pc(c?.transfert_penalite)} /></label>
          <label>Accepte l'étude de la plateforme{choixOui("accepte_etude_plateforme", c?.accepte_etude_plateforme)}</label>
          <label>Relevé annuel du fonds{choixOui("reporting_annuel", c?.reporting_annuel)}</label>
          <label>Participation servie (5 ans)<input name="historique_participation" defaultValue={c?.historique_participation ?? ""} placeholder="3,1 % ; 3,4 % ; …" /></label>
        </div>
        <label>Commentaire<input name="commentaire" defaultValue={c?.commentaire ?? ""} /></label>
        <label>L'offre de l'assureur (PDF, facultatif)<input type="file" accept=".pdf" onChange={(e) => setOffre(e.target.files?.[0] ?? null)} /></label>
        {c && <label>Pourquoi cette correction ?<input name="motif_correction" required /></label>}
        <div className="actions"><button className="principal">{c ? "Enregistrer la correction" : "Enregistrer la réponse"}</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
