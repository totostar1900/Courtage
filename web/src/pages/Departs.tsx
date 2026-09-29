import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { Anomalies, Cle, Constats, Erreur, Tiroir, useCharge, Volet } from "../composants/communs";
import { Terme } from "../composants/Terme";
import { dateFr, millions, montant } from "../format";
import { t } from "../i18n";
import { ExpliquerCalcul } from "../composants/Calcul";
import type { ApercuImport, CalculPrestation, Constat, ContratsDossier, MotifDepart, Prestation, Prestations } from "../types";
import { useDossier } from "./Dossier";
import { DemandePriseEnCharge, EtatDossier } from "./DossierPEC";
import { DepartHorsMandat } from "./HorsMandat";
import { DepotFichier } from "../composants/DepotFichier";

/** Les libellés des motifs, lus au rendu (la langue peut changer). */
export const motifs = (): Record<MotifDepart, string> => ({
  retraite: t("Retraite", "Retirement"), demission: t("Démission", "Resignation"), licenciement: t("Licenciement", "Dismissal"),
  deces: t("Décès", "Death"), autre: t("Autre", "Other"),
});

/** Les départs : ceux qui arrivent, ceux d'avant. Un matricule, jamais un nom. */
export default function Departs() {
  const d = useDossier();
  const { donnee, erreur, recharger } = useCharge(() => api.get<Prestations>(`/organisations/${d.org.id}/prestations`), []);
  const { donnee: contrat } = useCharge(() => api.get<ContratsDossier>(`/organisations/${d.org.id}/contrats`), []);
  const [volet, setVolet] = useState<null | "declarer" | "importer" | { corriger: Prestation } | { demander: Prestation } | { orienter: Prestation }>(null);
  const [ouverte, setOuverte] = useState<string | null>(null);
  // Les départs s'ouvrent une fois le contrat d'assurance signé et en vigueur (le serveur le contrôle aussi).
  const ouverts = d.activation?.capacites.departs !== false;
  const peutEcrire = d.role !== "lecteur_client" && ouverts;
  const detail = donnee?.prestations.find((p) => p.id === ouverte) ?? null;
  const fait = () => { setVolet(null); recharger(); };

  if (erreur) return <Erreur erreur={erreur} />;
  if (!donnee) return <p className="discret">{t("Chargement…", "Loading…")}</p>;
  const tot = donnee.totaux;
  const MOTIFS = motifs();

  return (
    <>
      <h1>{t("Départs et prestations", "Departures and benefit payments")}</h1>
      <p>{t("Chaque départ de l'entreprise, par matricule — jamais par nom. La plateforme recalcule le montant dû selon la règle en vigueur ce jour-là ; vous déclarez ce qui a été versé. Les départs hors retraite ne coûtent pas d'IFC mais mesurent la",
        "Every departure from the company, by staff number — never by name. The platform recalculates the amount due under the rule in force on that day; you report what was paid. Departures other than retirement cost no IFC but measure the")}{" "}
        <Terme cle="turnover">{t("rotation réelle", "actual turnover")}</Terme>.</p>
      {contrat && (
        <p className="discret">
          {contrat.service === "courtage"
            ? t("En courtage, nous porterons la prise en charge auprès de votre assureur.", "Under brokerage, we will handle the benefit payment with your insurer.")
            : t("Sans mandat, la prise en charge reste entre vous et votre assureur. Signez un mandat pour que nous la portions.",
                "Without a mandate, the benefit payment stays between you and your insurer. Sign a mandate for us to handle it.")}{" "}
          <Link to={contrat.service === "courtage" ? "../contrat" : "../accompagnement"}>
            {contrat.service === "courtage" ? t("Votre contrat", "Your contract") : t("Demander un accompagnement", "Request brokerage support")}</Link>
        </p>
      )}

      {!ouverts && <DepartsFermes />}

      <div className="grille g4 section">
        <Cle etiquette={t("Départs enregistrés", "Departures recorded")} valeur={String(tot.nombre)}
             sous={t(`${tot.retraites} en retraite · ${tot.autres_departs} autres`, `${tot.retraites} retirements · ${tot.autres_departs} other`)} />
        <Cle etiquette={t("Dû selon le régime", "Due under the plan")} valeur={millions(tot.du)} sous={montant(tot.du)} />
        <Cle etiquette={t("Versé aux salariés", "Paid to employees")} valeur={millions(tot.verse)} sous={montant(tot.verse)} />
        <Cle etiquette={t("Payé par le fonds", "Paid by the fund")} valeur={millions(tot.part_fonds_payee)} sous={montant(tot.part_fonds_payee)} terme="fonds" />
      </div>

      {peutEcrire && (
        <div className="actions section">
          <button className="principal" onClick={() => { setOuverte(null); setVolet("declarer"); }}>{t("Déclarer un départ", "Report a departure")}</button>
          <button onClick={() => { setOuverte(null); setVolet("importer"); }}>{t("Reprendre l'historique (tableur)", "Import past departures (spreadsheet)")}</button>
        </div>
      )}
      {volet && (
        <Tiroir etiquette={t("Départs", "Departures")} onFermer={() => setVolet(null)}>
          {volet === "declarer" && <FormulaireDepart onFermer={() => setVolet(null)} onFait={fait} />}
          {volet === "importer" && <ImportHistorique onFermer={() => setVolet(null)} onFait={fait} />}
          {typeof volet === "object" && "corriger" in volet && (
            <FormulaireDepart onFermer={() => setVolet(null)} onFait={fait} corriger={volet.corriger} />
          )}
          {typeof volet === "object" && "demander" in volet && (
            <DemandePriseEnCharge p={volet.demander} onFermer={() => setVolet(null)} />
          )}
          {typeof volet === "object" && "orienter" in volet && (
            <DepartHorsMandat p={volet.orienter} onFermer={() => setVolet(null)} onFait={fait} />
          )}
        </Tiroir>
      )}
      {detail && !volet && (
        <Tiroir etiquette={t(`Départ du matricule ${detail.matricule}`, `Departure of staff number ${detail.matricule}`)} onFermer={() => setOuverte(null)}>
          <Volet titre={t(`Départ du matricule ${detail.matricule}`, `Departure of staff number ${detail.matricule}`)} onFermer={() => setOuverte(null)}>
            <Detail p={detail} />
            <PriseEnCharge p={detail} role={d.role} onDemander={() => setVolet({ demander: detail })}
              onOrienter={() => setVolet({ orienter: detail })} />
            {peutEcrire && <Actions p={detail} onCorriger={() => setVolet({ corriger: detail })} onFait={recharger} />}
          </Volet>
        </Tiroir>
      )}

      <div className="section">
        <h2>{t("Départs", "Departures")}</h2>
        {donnee.prestations.length === 0 ? <p className="discret">{t("Aucun départ enregistré.", "No departures recorded.")}</p> : (
          <div className="defile">
            <table>
              <thead><tr><th>{t("Départ", "Departure")}</th><th>{t("Matricule", "Staff number")}</th><th>{t("Motif", "Reason")}</th><th className="n">{t("Ancienneté", "Length of service")}</th>
                <th className="n">{t("Dû", "Due")}</th><th className="n">{t("Versé", "Paid")}</th><th className="n">{t("Fonds", "Fund")}</th><th>{t("À regarder", "To check")}</th></tr></thead>
              <tbody>
                {donnee.prestations.map((p) => (
                  <tr key={p.id} className={`cliquable${ouverte === p.id ? " choisie" : ""}`} aria-selected={ouverte === p.id} data-prestation={p.matricule} onClick={() => { setVolet(null); setOuverte(ouverte === p.id ? null : p.id); }}>
                      <td>{dateFr(p.date_depart)}</td>
                      <td>{p.matricule}{p.categorie && <div className="discret">{p.categorie}</div>}</td>
                      <td>{MOTIFS[p.motif]}{p.soldee && <div className="discret">{t("soldé", "settled")}</div>}</td>
                      <td className="n">{t(`${String(p.calcul.anciennete).replace(".", ",")} ans`, `${p.calcul.anciennete} years`)}</td>
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

/** Qui s'occupe de la prestation : nous (sous mandat, un dossier), ou l'entreprise avec son assureur (sans mandat). */
function PriseEnCharge({ p, role, onDemander, onOrienter }:
  { p: Prestation; role: string; onDemander: () => void; onOrienter: () => void }) {
  if (p.motif !== "retraite") return null;
  if (p.dossier) {
    return <p>{t("Prise en charge :", "Benefit payment:")} <EtatDossier statut={p.dossier.statut} />{p.dossier.numero && <> · {p.dossier.numero}</>}{" "}
      <Link to={`../dossiers/${p.dossier.id}`}>{t("Ouvrir le dossier", "Open the claim file")}</Link></p>;
  }
  if (p.service === "courtage") {
    return role === "admin_client"
      ? <div className="actions"><button className="principal" onClick={onDemander}>{t("Demander la prise en charge", "Request the benefit payment")}</button></div>
      : <p className="discret">{t("En courtage : l'entreprise ouvre le dossier de prise en charge, le conseiller le vérifie et le transmet.", "Under brokerage: the company opens the claim file, the adviser checks it and sends it on.")}</p>;
  }
  return (
    <div>
      <p className="discret">{t("Sans mandat au jour de ce départ : la prise en charge s'est faite entre l'entreprise et son assureur. Aucune identité n'est recueillie ici.",
        "No mandate on the day of this departure: the benefit payment was handled between the company and its insurer. No identity is collected here.")}</p>
      <div className="actions"><button className="principal" onClick={onOrienter}>
        {p.part_fonds_payee !== null ? t("Revoir le paiement déclaré", "Review the reported payment") : t("Fiche de calcul et paiement", "Calculation sheet and payment")}</button></div>
    </div>
  );
}

function Pastilles({ constats }: { constats: Constat[] }) {
  if (!constats.length) return <span className="etat bien">{t("RAS", "OK")}</span>;
  const graves = constats.filter((c) => c.niveau !== "informe").length;
  return <span className={`etat ${graves ? "attention" : "neutre"}`}>{t(`${constats.length} point${constats.length > 1 ? "s" : ""}`, `${constats.length} issue${constats.length > 1 ? "s" : ""}`)}</span>;
}

function Detail({ p }: { p: Prestation }) {
  return (
    <div>
      <ExpliquerCalcul calcul={p.calcul} du={p.du} salaire={p.salaire_mensuel_reference} />
      <div className="lignes-offre">
        <div><span>{t("Embauche · départ", "Hired · left")}</span><span>{dateFr(p.date_embauche)} · {dateFr(p.date_depart)}</span></div>
        <div><span>{t("Salaire mensuel de référence", "Reference monthly salary")}</span><span>{montant(p.salaire_mensuel_reference)}</span></div>
        {p.part_fonds_demandee !== null && <div><span>{t("Demandé au fonds", "Requested from the fund")}</span><span>{montant(p.part_fonds_demandee)}</span></div>}
        {p.payee_le && <div><span>{t("Payé par le fonds le", "Paid by the fund on")}</span><span>{dateFr(p.payee_le)}</span></div>}
        <div><span>{t("Service au jour du départ", "Service on the day of departure")}</span><span>{p.service === "courtage" ? t("Courtage (sous mandat)", "Brokerage (under mandate)") : t("Sans mandat", "No mandate")}</span></div>
        <div><span>{t("Origine", "Source")}</span><span>{p.origine === "import" ? t("Reprise d'historique (tableur)", "Imported history (spreadsheet)") : t("Saisie", "Entered by hand")}</span></div>
        {p.motif_correction && <div><span>{t("Corrige une ligne précédente", "Corrects an earlier line")}</span><span>{p.motif_correction}</span></div>}
        {p.note && <div><span>{t("Note", "Note")}</span><span>{p.note}</span></div>}
      </div>
      <div className="section"><Constats constats={p.constats} vide={t("Rien à signaler.", "Nothing to report.")} /></div>
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
      <button onClick={onCorriger}>{t("Corriger", "Correct")}</button>
      {!annuler ? <button onClick={() => setAnnuler(true)}>{t("Annuler cette ligne", "Cancel this line")}</button> : (
        <>
          <input aria-label={t("Motif de l'annulation", "Reason for cancelling")} placeholder={t("Pourquoi ? (doublon, erreur…)", "Why? (duplicate, error…)")} value={motif}
                 onChange={(e) => setMotif(e.target.value)} />
          <button className="principal" disabled={!motif.trim()} onClick={async () => {
            setErreur(null);
            try { await api.post(`/organisations/${d.org.id}/prestations/${p.id}/annulation`, { motif_correction: motif }); onFait(); }
            catch (e) { setErreur(e); }
          }}>{t("Confirmer l'annulation", "Confirm the cancellation")}</button>
        </>
      )}
      <span className="discret">{t("Rien ne s'efface : une correction ou une annulation ajoute une ligne qui dit pourquoi.", "Nothing is erased: a correction or a cancellation adds a line that says why.")}</span>
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
    const s = (k: string) => String(f.get(k) ?? "").trim() || null;
    return {
      matricule: s("matricule"), motif: f.get("motif"), date_embauche: s("date_embauche"), date_depart: s("date_depart"),
      salaire_mensuel_reference: n("salaire_mensuel_reference") ?? 0, categorie: s("categorie"),
      date_naissance: s("date_naissance"), verse: n("verse"), part_fonds_demandee: n("part_fonds_demandee"),
      part_fonds_payee: n("part_fonds_payee"), payee_le: s("payee_le"), soldee: f.get("soldee") === "on",
      note: s("note"), convention_code: s("convention_code"),
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
    <Volet titre={c ? t(`Corriger le départ du matricule ${c.matricule}`, `Correct the departure of staff number ${c.matricule}`) : t("Déclarer un départ", "Report a departure")} onFermer={onFermer} className="section">
      <form className="formulaire" onSubmit={enregistrer} onChange={() => setApercu(null)}>
        <p className="discret">{t("Aucun nom : le matricule suffit, comme dans le fichier du personnel.", "No names: the staff number is enough, as in the staff file.")}</p>
        <div className="grille g3">
          <label>{t("Matricule", "Staff number")}<input name="matricule" required defaultValue={c?.matricule} /></label>
          <label>{t("Motif", "Reason")}<select name="motif" defaultValue={c?.motif ?? "retraite"}>
            {Object.entries(motifs()).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
          <label>{t("Catégorie (facultatif)", "Category (optional)")}<input name="categorie" defaultValue={c?.categorie ?? ""} /></label>
          <label>{t("Date d'embauche", "Hiring date")}<input name="date_embauche" type="date" required defaultValue={c?.date_embauche} /></label>
          <label>{t("Date de départ", "Departure date")}<input name="date_depart" type="date" required defaultValue={c?.date_depart} /></label>
          <label>{t("Date de naissance (facultatif)", "Date of birth (optional)")}<input name="date_naissance" type="date" defaultValue={c?.date_naissance ?? ""} /></label>
          <label>{t("Salaire mensuel de référence (F)", "Reference monthly salary (F)")}<input name="salaire_mensuel_reference" type="number" min={0} required
                 defaultValue={c?.salaire_mensuel_reference} /></label>
          <label>{t("Montant versé au salarié (F)", "Amount paid to the employee (F)")}<input name="verse" type="number" min={0} defaultValue={c?.verse ?? ""} /></label>
          <label>{t("Convention (sans régime adopté)", "Collective agreement (if no scheme adopted)")}<input name="convention_code" placeholder={t("par défaut : celle de la dernière étude", "default: the one from the latest study")}
                 defaultValue={c?.calcul.source?.type === "convention" ? c.calcul.source.convention_code : ""} /></label>
          <label>{t("Demandé au fonds (F)", "Requested from the fund (F)")}<input name="part_fonds_demandee" type="number" min={0} defaultValue={c?.part_fonds_demandee ?? ""} /></label>
          <label>{t("Payé par le fonds (F)", "Paid by the fund (F)")}<input name="part_fonds_payee" type="number" min={0} defaultValue={c?.part_fonds_payee ?? ""} /></label>
          <label>{t("Payé le", "Paid on")}<input name="payee_le" type="date" defaultValue={c?.payee_le ?? ""} /></label>
        </div>
        <label style={{ display: "flex", gap: 8, fontWeight: 400 }}>
          <input type="checkbox" name="soldee" defaultChecked={c?.soldee} /> {t("Départ déjà réglé (rien ne reste à payer)", "Departure already settled (nothing left to pay)")}</label>
        <label>{t("Note", "Note")}<input name="note" defaultValue={c?.note ?? ""} /></label>
        {c && <label>{t("Pourquoi cette correction ?", "Why this correction?")}<input name="motif_correction" required /></label>}
        {apercu && (
          <div className="carte section" data-apercu>
            <ExpliquerCalcul calcul={apercu.calcul} du={apercu.du} salaire={apercu.salaire} />
            <Constats constats={apercu.constats} vide={t("Rien à signaler.", "Nothing to report.")} />
          </div>
        )}
        <div className="actions">
          <button type="button" onClick={(e) => calculer(e.currentTarget.form!)}>{t("Calculer le dû", "Calculate the amount due")}</button>
          <button className="principal">{c ? t("Enregistrer la correction", "Save the correction") : t("Enregistrer le départ", "Save the departure")}</button>
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
    <Volet titre={t("Reprendre l'historique des départs", "Import past departures")} onFermer={onFermer} className="section">
      <p>{t("Un tableur, une ligne par départ : matricule, date d'embauche, date de départ, motif, salaire mensuel de référence ; et si vous les avez, le montant versé, ce que le fonds a payé et quand. Cinq ans suffisent. Une colonne de noms est ignorée.",
        "A spreadsheet, one line per departure: staff number, hiring date, departure date, reason, reference monthly salary; and if you have them, the amount paid, what the fund paid and when. Five years is enough. A column of names is ignored.")}</p>
      <div className="grille g3" style={{ alignItems: "end" }}>
        <DepotFichier libelle={t("Fichier (xlsx ou csv)", "File (xlsx or csv)")} accept=".xlsx,.csv" fichier={fichier} onChange={(f) => { setFichier(f); setApercu(null); }} />
        <label>{t("Convention (sans régime adopté)", "Collective agreement (if no scheme adopted)")}<input value={convention} onChange={(e) => setConvention(e.target.value)} placeholder={t("celle de la dernière étude", "the one from the latest study")} /></label>
        <div className="actions"><button type="button" disabled={!fichier} onClick={() => envoyer(false)}>{t("Lire le fichier", "Read the file")}</button></div>
      </div>
      <Erreur erreur={erreur} />
      {apercu && (
        <div className="section">
          {apercu.colonnes_ignorees.length > 0 && <p className="discret">{t(`Colonnes ignorées : ${apercu.colonnes_ignorees.join(", ")}.`, `Columns ignored: ${apercu.colonnes_ignorees.join(", ")}.`)}</p>}
          <Anomalies anomalies={apercu.anomalies} />
          <div className="defile"><table>
            <thead><tr><th>{t("Ligne", "Line")}</th><th>{t("Matricule", "Staff number")}</th><th>{t("Départ", "Departure")}</th><th>{t("Motif", "Reason")}</th><th className="n">{t("Dû", "Due")}</th><th className="n">{t("Versé", "Paid")}</th><th>{t("À regarder", "To check")}</th></tr></thead>
            <tbody>{apercu.lignes.map((l) => (
              <tr key={l.numero}><td>{l.numero}</td><td>{l.matricule}</td><td>{dateFr(l.date_depart)}</td><td>{motifs()[l.motif]}</td>
                <td className="n">{montant(l.du)}</td><td className="n">{montant(l.verse)}</td><td><Pastilles constats={l.constats} /></td></tr>
            ))}</tbody>
          </table></div>
          <div className="actions">
            <button className="principal" disabled={bloquants > 0 || apercu.lignes.length === 0} onClick={() => envoyer(true)}>
              {t(`Enregistrer les ${apercu.lignes.length} départs`, `Save the ${apercu.lignes.length} departures`)}</button>
            {bloquants > 0 && <span className="etat grave">{t(`${bloquants} point(s) bloquant(s) : corrigez le fichier, rien n'est enregistré`, `${bloquants} blocking issue(s): correct the file, nothing is saved`)}</span>}
          </div>
        </div>
      )}
    </Volet>
  );
}

/** Avant le contrat : ce qui ouvre les départs, et où en est le chemin. */
function DepartsFermes() {
  const pas: [string, string, string][] = [
    [t("Le mandat de courtage", "The brokerage mandate"), t("Demandé, proposé, signé en ligne.", "Requested, proposed, signed online."), "../accompagnement"],
    [t("Les offres des assureurs", "The insurers' offers"), t("Votre conseiller les apporte ; vous choisissez.", "Your adviser brings them; you choose."), "../financement"],
    [t("Le contrat signé et en vigueur", "The contract signed and in force"), t("Police reçue, signée, première prime encaissée.", "Policy received, signed, first premium received."), "../placement"],
  ];
  return (
    <section className="carte section verrou" aria-labelledby="departs-fermes">
      <p className="surtitre">{t("Pas encore ouvert", "Not open yet")}</p>
      <h2 id="departs-fermes">{t("Les départs s'ouvrent avec votre contrat", "Departures open with your contract")}</h2>
      <p>{t("Déclarer un départ et demander une prise en charge n'ont de sens qu'une fois le contrat d'assurance signé et en vigueur : c'est l'assureur qui paie, et votre conseiller qui porte le dossier.",
        "Reporting a departure and requesting a benefit payment only make sense once the insurance contract is signed and in force: the insurer pays, and your adviser handles the claim.")}</p>
      <ol className="frise frise-3">
        {pas.map(([titre, texte, vers], i) => (
          <li key={titre}><span className="frise-num">{i + 1}</span><strong><Link to={vers}>{titre}</Link></strong><span>{texte}</span></li>
        ))}
      </ol>
    </section>
  );
}
