import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { Anomalies, Cle, Constats, Erreur, Tiroir, useCharge, Volet } from "../composants/communs";
import { Terme } from "../composants/Terme";
import { dateFr, millions, montant } from "../format";
import { ExpliquerCalcul } from "../composants/Calcul";
import type { ApercuImport, CalculPrestation, Constat, ContratsDossier, MotifDepart, Prestation, Prestations } from "../types";
import { useDossier } from "./Dossier";
import { DemandePriseEnCharge, EtatDossier } from "./DossierPEC";
import { OrientationAssureur } from "./Orientation";

export const MOTIFS: Record<MotifDepart, string> = {
  retraite: "Retraite", demission: "Démission", licenciement: "Licenciement", deces: "Décès", autre: "Autre",
};

/** Les départs : ceux qui arrivent, ceux d'avant. Un matricule, jamais un nom. */
export default function Departs() {
  const d = useDossier();
  const { donnee, erreur, recharger } = useCharge(() => api.get<Prestations>(`/organisations/${d.org.id}/prestations`), []);
  const { donnee: contrat } = useCharge(() => api.get<ContratsDossier>(`/organisations/${d.org.id}/contrats`), []);
  const [volet, setVolet] = useState<null | "declarer" | "importer" | { corriger: Prestation } | { demander: Prestation } | { orienter: Prestation }>(null);
  const [ouverte, setOuverte] = useState<string | null>(null);
  const peutEcrire = d.role !== "lecteur_client";
  const detail = donnee?.prestations.find((p) => p.id === ouverte) ?? null;
  const fait = () => { setVolet(null); recharger(); };

  if (erreur) return <Erreur erreur={erreur} />;
  if (!donnee) return <p className="discret">Chargement…</p>;
  const t = donnee.totaux;

  return (
    <>
      <h1>Départs et prestations</h1>
      <p>Chaque départ de l'entreprise, par matricule — jamais par nom. La plateforme recalcule le montant dû selon la
        règle en vigueur ce jour-là ; vous déclarez ce qui a été versé. Les départs hors retraite ne coûtent pas d'IFC
        mais mesurent la <Terme cle="turnover">rotation réelle</Terme>.</p>
      {contrat && (
        <p className="discret">
          {contrat.service === "courtage"
            ? "En courtage, nous porterons la prise en charge auprès de votre assureur."
            : "En comparaison, la prise en charge se demande directement à votre assureur."}{" "}
          <Link to="../contrat">Votre contrat</Link>
        </p>
      )}

      <div className="grille g4 section">
        <Cle etiquette="Départs enregistrés" valeur={String(t.nombre)} sous={`${t.retraites} en retraite · ${t.autres_departs} autres`} />
        <Cle etiquette="Dû selon le régime" valeur={millions(t.du)} sous={montant(t.du)} />
        <Cle etiquette="Versé aux salariés" valeur={millions(t.verse)} sous={montant(t.verse)} />
        <Cle etiquette="Payé par le fonds" valeur={millions(t.part_fonds_payee)} sous={montant(t.part_fonds_payee)} terme="fonds" />
      </div>

      {peutEcrire && (
        <div className="actions section">
          <button className="principal" onClick={() => { setOuverte(null); setVolet("declarer"); }}>Déclarer un départ</button>
          <button onClick={() => { setOuverte(null); setVolet("importer"); }}>Reprendre l'historique (tableur)</button>
        </div>
      )}
      {volet && (
        <Tiroir etiquette="Départs" onFermer={() => setVolet(null)}>
          {volet === "declarer" && <FormulaireDepart onFermer={() => setVolet(null)} onFait={fait} />}
          {volet === "importer" && <ImportHistorique onFermer={() => setVolet(null)} onFait={fait} />}
          {typeof volet === "object" && "corriger" in volet && (
            <FormulaireDepart onFermer={() => setVolet(null)} onFait={fait} corriger={volet.corriger} />
          )}
          {typeof volet === "object" && "demander" in volet && (
            <DemandePriseEnCharge p={volet.demander} onFermer={() => setVolet(null)} />
          )}
          {typeof volet === "object" && "orienter" in volet && (
            <OrientationAssureur p={volet.orienter} onFermer={() => setVolet(null)} onFait={fait} />
          )}
        </Tiroir>
      )}
      {detail && !volet && (
        <Tiroir etiquette={`Départ du matricule ${detail.matricule}`} onFermer={() => setOuverte(null)}>
          <Volet titre={`Départ du matricule ${detail.matricule}`} onFermer={() => setOuverte(null)}>
            <Detail p={detail} />
            <PriseEnCharge p={detail} role={d.role} onDemander={() => setVolet({ demander: detail })}
              onOrienter={() => setVolet({ orienter: detail })} />
            {peutEcrire && <Actions p={detail} onCorriger={() => setVolet({ corriger: detail })} onFait={recharger} />}
          </Volet>
        </Tiroir>
      )}

      <div className="section">
        <h2>Départs</h2>
        {donnee.prestations.length === 0 ? <p className="discret">Aucun départ enregistré.</p> : (
          <div className="defile">
            <table>
              <thead><tr><th>Départ</th><th>Matricule</th><th>Motif</th><th className="n">Ancienneté</th>
                <th className="n">Dû</th><th className="n">Versé</th><th className="n">Fonds</th><th>À regarder</th></tr></thead>
              <tbody>
                {donnee.prestations.map((p) => (
                  <tr key={p.id} className={`cliquable${ouverte === p.id ? " choisie" : ""}`} aria-selected={ouverte === p.id} data-prestation={p.matricule} onClick={() => { setVolet(null); setOuverte(ouverte === p.id ? null : p.id); }}>
                      <td>{dateFr(p.date_depart)}</td>
                      <td>{p.matricule}{p.categorie && <div className="discret">{p.categorie}</div>}</td>
                      <td>{MOTIFS[p.motif]}{p.soldee && <div className="discret">soldé</div>}</td>
                      <td className="n">{String(p.calcul.anciennete).replace(".", ",")} ans</td>
                      <td className="n">{montant(p.du)}</td>
                      <td className="n">{montant(p.verse)}</td>
                      <td className="n">{montant(p.part_fonds_payee)}</td>
                      <td><Pastilles constats={p.constats} />{p.dossier && <div><EtatDossier statut={p.dossier.statut} /></div>}</td>
                    </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

/** Qui s'occupe de la prestation : nous (courtage, un dossier), ou l'assureur directement (comparaison). */
function PriseEnCharge({ p, role, onDemander, onOrienter }:
  { p: Prestation; role: string; onDemander: () => void; onOrienter: () => void }) {
  if (p.motif !== "retraite") return null;
  if (p.dossier) {
    return <p>Prise en charge : <EtatDossier statut={p.dossier.statut} />{p.dossier.numero && <> · {p.dossier.numero}</>}{" "}
      <Link to={`../dossiers/${p.dossier.id}`}>Ouvrir le dossier</Link></p>;
  }
  if (p.service === "courtage") {
    return role === "admin_client"
      ? <div className="actions"><button className="principal" onClick={onDemander}>Demander la prise en charge</button></div>
      : <p className="discret">En courtage : l'entreprise ouvre le dossier de prise en charge, le conseiller le vérifie et le transmet.</p>;
  }
  return (
    <div>
      <p className="discret">Au jour de ce départ, le service était la comparaison : la prise en charge se demande
        directement à votre assureur. Aucune identité n'est recueillie ici.</p>
      <div className="actions"><button className="principal" onClick={onOrienter}>
        {p.part_fonds_payee !== null ? "Revoir la demande à l'assureur" : "Préparer la demande à l'assureur"}</button></div>
    </div>
  );
}

function Pastilles({ constats }: { constats: Constat[] }) {
  if (!constats.length) return <span className="etat bien">RAS</span>;
  const graves = constats.filter((c) => c.niveau !== "informe").length;
  return <span className={`etat ${graves ? "attention" : "neutre"}`}>{constats.length} point{constats.length > 1 ? "s" : ""}</span>;
}

function Detail({ p }: { p: Prestation }) {
  return (
    <div>
      <ExpliquerCalcul calcul={p.calcul} du={p.du} salaire={p.salaire_mensuel_reference} />
      <div className="lignes-offre">
        <div><span>Embauche · départ</span><span>{dateFr(p.date_embauche)} · {dateFr(p.date_depart)}</span></div>
        <div><span>Salaire mensuel de référence</span><span>{montant(p.salaire_mensuel_reference)}</span></div>
        {p.part_fonds_demandee !== null && <div><span>Demandé au fonds</span><span>{montant(p.part_fonds_demandee)}</span></div>}
        {p.payee_le && <div><span>Payé par le fonds le</span><span>{dateFr(p.payee_le)}</span></div>}
        <div><span>Service au jour du départ</span><span>{p.service === "courtage" ? "Courtage" : "Comparaison"}</span></div>
        <div><span>Origine</span><span>{p.origine === "import" ? "Reprise d'historique (tableur)" : "Saisie"}</span></div>
        {p.motif_correction && <div><span>Corrige une ligne précédente</span><span>{p.motif_correction}</span></div>}
        {p.note && <div><span>Note</span><span>{p.note}</span></div>}
      </div>
      <div className="section"><Constats constats={p.constats} vide="Rien à signaler." /></div>
    </div>
  );
}

function Actions({ p, onCorriger, onFait }: { p: Prestation; onCorriger: () => void; onFait: () => void }) {
  const d = useDossier();
  const [annuler, setAnnuler] = useState(false);
  const [motif, setMotif] = useState("");
  const [erreur, setErreur] = useState<unknown>(null);
  return (
    <div className="actions">
      <button onClick={onCorriger}>Corriger</button>
      {!annuler ? <button onClick={() => setAnnuler(true)}>Annuler cette ligne</button> : (
        <>
          <input aria-label="Motif de l'annulation" placeholder="Pourquoi ? (doublon, erreur…)" value={motif}
                 onChange={(e) => setMotif(e.target.value)} />
          <button className="principal" disabled={!motif.trim()} onClick={async () => {
            setErreur(null);
            try { await api.post(`/organisations/${d.org.id}/prestations/${p.id}/annulation`, { motif_correction: motif }); onFait(); }
            catch (e) { setErreur(e); }
          }}>Confirmer l'annulation</button>
        </>
      )}
      <span className="discret">Rien ne s'efface : une correction ou une annulation ajoute une ligne qui dit pourquoi.</span>
      <Erreur erreur={erreur} />
    </div>
  );
}

// --- Déclarer ou corriger ------------------------------------------------------------

function FormulaireDepart({ onFermer, onFait, corriger }: { onFermer: () => void; onFait: () => void; corriger?: Prestation }) {
  const d = useDossier();
  const [apercu, setApercu] = useState<{ du: number; calcul: CalculPrestation; constats: Constat[]; salaire: number } | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const c = corriger;

  function corps(f: FormData) {
    const n = (k: string) => (String(f.get(k) ?? "").trim() === "" ? null : Number(f.get(k)));
    const t = (k: string) => String(f.get(k) ?? "").trim() || null;
    return {
      matricule: t("matricule"), motif: f.get("motif"), date_embauche: t("date_embauche"), date_depart: t("date_depart"),
      salaire_mensuel_reference: n("salaire_mensuel_reference") ?? 0, categorie: t("categorie"),
      date_naissance: t("date_naissance"), verse: n("verse"), part_fonds_demandee: n("part_fonds_demandee"),
      part_fonds_payee: n("part_fonds_payee"), payee_le: t("payee_le"), soldee: f.get("soldee") === "on",
      note: t("note"), convention_code: t("convention_code"),
    };
  }
  async function calculer(form: HTMLFormElement) {
    setErreur(null);
    const saisie = corps(new FormData(form));
    try {
      const r = await api.post<{ du: number; calcul: CalculPrestation; constats: Constat[] }>(
        `/organisations/${d.org.id}/prestations/apercu`, saisie);
      setApercu({ ...r, salaire: saisie.salaire_mensuel_reference });
    }
    catch (e) { setApercu(null); setErreur(e); }
  }
  async function enregistrer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      if (c) await api.post(`/organisations/${d.org.id}/prestations/${c.id}/correction`, { ...corps(f), motif_correction: f.get("motif_correction") });
      else await api.post(`/organisations/${d.org.id}/prestations`, corps(f));
      onFait();
    } catch (e) { setErreur(e); }
  }

  return (
    <Volet titre={c ? `Corriger le départ du matricule ${c.matricule}` : "Déclarer un départ"} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={enregistrer} onChange={() => setApercu(null)}>
        <p className="discret">Aucun nom : le matricule suffit, comme dans le fichier du personnel.</p>
        <div className="grille g3">
          <label>Matricule<input name="matricule" required defaultValue={c?.matricule} /></label>
          <label>Motif<select name="motif" defaultValue={c?.motif ?? "retraite"}>
            {Object.entries(MOTIFS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
          <label>Catégorie (facultatif)<input name="categorie" defaultValue={c?.categorie ?? ""} /></label>
          <label>Date d'embauche<input name="date_embauche" type="date" required defaultValue={c?.date_embauche} /></label>
          <label>Date de départ<input name="date_depart" type="date" required defaultValue={c?.date_depart} /></label>
          <label>Date de naissance (facultatif)<input name="date_naissance" type="date" defaultValue={c?.date_naissance ?? ""} /></label>
          <label>Salaire mensuel de référence (F)<input name="salaire_mensuel_reference" type="number" min={0} required
                 defaultValue={c?.salaire_mensuel_reference} /></label>
          <label>Montant versé au salarié (F)<input name="verse" type="number" min={0} defaultValue={c?.verse ?? ""} /></label>
          <label>Convention (sans régime adopté)<input name="convention_code" placeholder="par défaut : celle de la dernière étude"
                 defaultValue={c?.calcul.source?.type === "convention" ? c.calcul.source.convention_code : ""} /></label>
          <label>Demandé au fonds (F)<input name="part_fonds_demandee" type="number" min={0} defaultValue={c?.part_fonds_demandee ?? ""} /></label>
          <label>Payé par le fonds (F)<input name="part_fonds_payee" type="number" min={0} defaultValue={c?.part_fonds_payee ?? ""} /></label>
          <label>Payé le<input name="payee_le" type="date" defaultValue={c?.payee_le ?? ""} /></label>
        </div>
        <label style={{ display: "flex", gap: 8, fontWeight: 400 }}>
          <input type="checkbox" name="soldee" defaultChecked={c?.soldee} /> Départ déjà réglé (rien ne reste à payer)</label>
        <label>Note<input name="note" defaultValue={c?.note ?? ""} /></label>
        {c && <label>Pourquoi cette correction ?<input name="motif_correction" required /></label>}
        {apercu && (
          <div className="carte section" data-apercu>
            <ExpliquerCalcul calcul={apercu.calcul} du={apercu.du} salaire={apercu.salaire} />
            <Constats constats={apercu.constats} vide="Rien à signaler." />
          </div>
        )}
        <div className="actions">
          <button type="button" onClick={(e) => calculer(e.currentTarget.form!)}>Calculer le dû</button>
          <button className="principal">{c ? "Enregistrer la correction" : "Enregistrer le départ"}</button>
        </div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}

// --- L'historique par tableur -------------------------------------------------------

function ImportHistorique({ onFermer, onFait }: { onFermer: () => void; onFait: () => void }) {
  const d = useDossier();
  const [fichier, setFichier] = useState<File | null>(null);
  const [convention, setConvention] = useState("");
  const [apercu, setApercu] = useState<ApercuImport | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);

  async function envoyer(enregistrer: boolean) {
    if (!fichier) return;
    const f = new FormData();
    f.append("fichier", fichier);
    if (convention) f.append("convention_code", convention);
    f.append("enregistrer", String(enregistrer));
    setErreur(null);
    try {
      const r = await api.post<ApercuImport>(`/organisations/${d.org.id}/prestations/import`, f);
      if (enregistrer) onFait(); else setApercu(r);
    } catch (e) { setErreur(e); }
  }
  const bloquants = apercu?.anomalies.filter((a) => a.niveau === "bloquant").length ?? 0;

  return (
    <Volet titre="Reprendre l'historique des départs" onFermer={onFermer} className="section">
      <p>Un tableur, une ligne par départ : matricule, date d'embauche, date de départ, motif, salaire mensuel de
        référence ; et si vous les avez, le montant versé, ce que le fonds a payé et quand. Cinq ans suffisent.
        Une colonne de noms est ignorée.</p>
      <div className="grille g3" style={{ alignItems: "end" }}>
        <label>Fichier (xlsx ou csv)<input type="file" accept=".xlsx,.csv" onChange={(e) => { setFichier(e.target.files?.[0] ?? null); setApercu(null); }} /></label>
        <label>Convention (sans régime adopté)<input value={convention} onChange={(e) => setConvention(e.target.value)} placeholder="celle de la dernière étude" /></label>
        <div className="actions"><button type="button" disabled={!fichier} onClick={() => envoyer(false)}>Lire le fichier</button></div>
      </div>
      <Erreur erreur={erreur} />
      {apercu && (
        <div className="section">
          {apercu.colonnes_ignorees.length > 0 && <p className="discret">Colonnes ignorées : {apercu.colonnes_ignorees.join(", ")}.</p>}
          <Anomalies anomalies={apercu.anomalies} />
          <div className="defile"><table>
            <thead><tr><th>Ligne</th><th>Matricule</th><th>Départ</th><th>Motif</th><th className="n">Dû</th><th className="n">Versé</th><th>À regarder</th></tr></thead>
            <tbody>{apercu.lignes.map((l) => (
              <tr key={l.numero}><td>{l.numero}</td><td>{l.matricule}</td><td>{dateFr(l.date_depart)}</td><td>{MOTIFS[l.motif]}</td>
                <td className="n">{montant(l.du)}</td><td className="n">{montant(l.verse)}</td><td><Pastilles constats={l.constats} /></td></tr>
            ))}</tbody>
          </table></div>
          <div className="actions">
            <button className="principal" disabled={bloquants > 0 || apercu.lignes.length === 0} onClick={() => envoyer(true)}>
              Enregistrer les {apercu.lignes.length} départs</button>
            {bloquants > 0 && <span className="etat grave">{bloquants} point(s) bloquant(s) : corrigez le fichier, rien n'est enregistré</span>}
          </div>
        </div>
      )}
    </Volet>
  );
}
