import { useState, type FormEvent, type ReactNode } from "react";

import { api } from "../api";
import { raisonActivation } from "../activation";
import { Erreur, useCharge, Volet } from "../composants/communs";
import { dateFr, montant } from "../format";
import { t } from "../i18n";
import { useDossier } from "./Dossier";

interface Piece { id: string; nature: string; nom_fichier: string; depose_le: string; appel_id: string | null;
  releve_le: string | null; montant_fonds: number | null }
interface Appel {
  id: string; reference: string; montant: number; echeance: string; premiere: boolean;
  etat: "a_payer" | "en_retard" | "declare" | "encaisse";
  coordonnees: { banque: string; titulaire: string; iban: string; bic: string | null };
  controle: "conforme" | "modifie" | "non_enregistre"; ne_pas_payer: boolean; a_confirmer: boolean;
  contre_appel: { aupres: string; telephone: string; le: string; par: string } | null;
  virement: { le: string; montant: number; reference: string | null; ecart: number } | null;
  encaisse_le: string | null; pieces: Piece[];
}
interface Police {
  id: string; assureur: string; numero_police: string | null; date_effet: string; periodicite: string;
  signee_le: string | null; choix_id: string | null;
  statut: { code: string; libelle: string; etapes: { code: string; libelle: string; fait: boolean; le: string | null }[] };
  pieces: Piece[]; appels: Appel[];
  releves: { releves: (Piece & { primes_encaissees: number })[];
             etude: { date_evaluation: string; fonds_disponible: number; ecart: number | null } | null };
}
interface Tableau { polices: Police[]; offres_a_placer: { id: string; assureur: string; choisi_le: string }[]; periodicites: string[] }

const periodicites = (): Record<string, string> => ({ annuelle: t("Annuelle", "Annual"),
  semestrielle: t("Semestrielle", "Half-yearly"), trimestrielle: t("Trimestrielle", "Quarterly"),
  mensuelle: t("Mensuelle", "Monthly"), unique: t("Prime unique", "Single premium") });
const natures = (): Record<string, string> => ({ police: t("Police", "Policy"), police_signee: t("Police signée", "Signed policy"),
  avenant: t("Avenant", "Rider"), appel: t("Appel de prime", "Premium call"), avis_virement: t("Avis de virement", "Transfer advice"),
  quittance: t("Quittance", "Receipt"), releve: t("Relevé", "Statement") });
const etats = (): Record<Appel["etat"], [string, string]> => ({ a_payer: [t("À payer", "To pay"), "neutre"],
  en_retard: [t("En retard", "Overdue"), "grave"], declare: [t("Payé (déclaré)", "Paid (declared)"), "attention"],
  encaisse: [t("Encaissé (confirmé)", "Received (confirmed)"), "bien"] });
const aujourdHui = () => new Date().toISOString().slice(0, 10);

/** La police placée chez l'assureur, ses appels de prime, les virements déclarés, les quittances, les relevés.
 *  La plateforme ne paie rien : les primes partent par virement, de votre banque au compte de l'assureur. */
export default function Placement() {
  const d = useDossier();
  const { donnee, erreur, recharger } = useCharge(() => api.get<Tableau>(`/organisations/${d.org.id}/placement`), []);
  const [nouvelle, setNouvelle] = useState<{ choix?: { id: string; assureur: string } } | null>(null);
  const horsMandat = raisonActivation(d.activation, "cahier");
  const conseiller = d.role === "conseiller";
  if (erreur) return <Erreur erreur={erreur} />;
  if (!donnee) return <p className="discret">{t("Chargement…", "Loading…")}</p>;
  return (
    <>
      <h1>{t("Placement", "Placement")}</h1>
      <p>{t("La police placée chez l'assureur retenu, ses appels de prime, vos virements et les quittances de l'assureur. La plateforme ne paie rien : les primes se paient par virement, depuis votre banque, sur le compte de l'assureur ; ici, on range l'appel, on vérifie ses coordonnées bancaires et on garde la preuve.",
        "The policy placed with the chosen insurer, its premium calls, your transfers and the insurer's receipts. The platform pays nothing: premiums are paid by bank transfer, from your bank, to the insurer's account; here, the call is filed, its bank details checked and the proof kept.")}</p>
      {horsMandat && <p className="constat informe">{horsMandat}</p>}

      {conseiller && !horsMandat && (
        <section className="section">
          {donnee.offres_a_placer.map((o) => (
            <div key={o.id} className="constat informe">
              <div className="titre">{t(`Offre retenue : ${o.assureur}`, `Chosen offer: ${o.assureur}`)}</div>
              <p>{t(`Choisie le ${dateFr(o.choisi_le)}. Créer la police pour suivre sa mise en vigueur.`,
                `Chosen on ${dateFr(o.choisi_le)}. Create the policy to follow it until it is in force.`)}</p>
              <div className="actions"><button className="principal" onClick={() => setNouvelle({ choix: o })}>
                {t("Créer la police", "Create the policy")}</button></div>
            </div>
          ))}
          <button type="button" onClick={() => setNouvelle({})}>{t("Police placée autrement", "Policy placed otherwise")}</button>
        </section>
      )}
      {nouvelle && <NouvellePolice orgId={d.org.id} choix={nouvelle.choix} periodicites={donnee.periodicites}
                                   onFermer={() => setNouvelle(null)} onFait={() => { setNouvelle(null); recharger(); }} />}

      {donnee.polices.length === 0 && (
        <p className="carte section discret">{t("Aucune police pour l'instant : elle se crée une fois l'offre choisie.",
          "No policy yet: it is created once the offer is chosen.")}</p>
      )}
      {donnee.polices.map((p) => <FichePolice key={p.id} orgId={d.org.id} role={d.role} p={p} onFait={recharger} />)}
    </>
  );
}

function NouvellePolice({ orgId, choix, periodicites: codes, onFermer, onFait }: { orgId: string;
  choix?: { id: string; assureur: string }; periodicites: string[]; onFermer: () => void; onFait: () => void }) {
  const [erreur, setErreur] = useState<unknown>(null);
  async function creer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await api.post(`/organisations/${orgId}/polices`, { choix_id: choix?.id ?? null,
        assureur: choix ? null : String(f.get("assureur") ?? ""), date_effet: String(f.get("date_effet")),
        periodicite: String(f.get("periodicite")), numero_police: String(f.get("numero_police") ?? "").trim() || null });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre={t("Nouvelle police", "New policy")} onFermer={onFermer}>
      <form className="formulaire" onSubmit={creer}>
        {choix ? <p>{t(`Assureur : ${choix.assureur} (offre retenue).`, `Insurer: ${choix.assureur} (chosen offer).`)}</p>
          : <label>{t("Assureur", "Insurer")}<input name="assureur" required minLength={2} /></label>}
        <div className="grille-2">
          <label>{t("Date d'effet", "Effective date")}<input type="date" name="date_effet" required /></label>
          <label>{t("Périodicité des primes", "Premium frequency")}
            <select name="periodicite" defaultValue="annuelle">
              {codes.map((c) => <option key={c} value={c}>{periodicites()[c] ?? c}</option>)}</select></label>
        </div>
        <label>{t("Numéro de police (s'il est connu)", "Policy number (if known)")}<input name="numero_police" /></label>
        <div className="actions"><button className="principal">{t("Créer", "Create")}</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}

/** Déposer une pièce : un fichier, envoyé tel quel ; rien ne s'enregistre sans lui. */
function Depot({ libelle, envoyer, children }: { libelle: string; envoyer: (fichier: File, f: FormData) => Promise<void>;
  children?: ReactNode }) {
  const [fichier, setFichier] = useState<File | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  async function soumettre(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    if (!fichier) { setErreur(new Error(t("Choisir un fichier (PDF, JPEG ou PNG).", "Choose a file (PDF, JPEG or PNG)."))); return; }
    setErreur(null);
    try { await envoyer(fichier, new FormData(ev.currentTarget)); setFichier(null); ev.currentTarget?.reset?.(); }
    catch (e) { setErreur(e); }
  }
  return (
    <form className="formulaire depot" onSubmit={soumettre}>
      {children}
      <label>{libelle}<input type="file" accept="application/pdf,image/jpeg,image/png"
                             onChange={(e) => setFichier(e.target.files?.[0] ?? null)} /></label>
      <div className="actions"><button>{t("Déposer", "Upload")}</button></div>
      <Erreur erreur={erreur} />
    </form>
  );
}

function Pieces({ orgId, policeId, pieces }: { orgId: string; policeId: string; pieces: Piece[] }) {
  if (!pieces.length) return null;
  return (
    <ul className="liste-simple">
      {pieces.map((x) => (
        <li key={x.id}><button className="lien" type="button"
          onClick={() => api.ouvrir(`/organisations/${orgId}/polices/${policeId}/pieces/${x.id}`)}>
          {natures()[x.nature] ?? x.nature} — {x.nom_fichier}</button>
          <span className="discret"> · {dateFr(x.depose_le)}</span></li>
      ))}
    </ul>
  );
}

function FichePolice({ orgId, role, p, onFait }: { orgId: string; role: string; p: Police; onFait: () => void }) {
  const conseiller = role === "conseiller";
  const [erreur, setErreur] = useState<unknown>(null);
  const [nouvelAppel, setNouvelAppel] = useState(false);
  const deposer = (nature: string, extra: Record<string, string> = {}) => async (fichier: File) => {
    const f = new FormData();
    f.set("nature", nature);
    f.set("fichier", fichier);
    for (const [k, v] of Object.entries(extra)) f.set(k, v);
    await api.post(`/organisations/${orgId}/polices/${p.id}/pieces`, f);
    onFait();
  };
  const recue = p.pieces.some((x) => x.nature === "police");
  async function agir(action: () => Promise<unknown>) {
    setErreur(null);
    try { await action(); onFait(); } catch (e) { setErreur(e); }
  }
  return (
    <section className="carte section police" aria-label={t(`Police ${p.assureur}`, `${p.assureur} policy`)}>
      <div className="actions" style={{ justifyContent: "space-between", marginTop: 0 }}>
        <h2 style={{ margin: 0 }}>{p.assureur}</h2>
        <span className={`etat ${p.statut.code === "en_vigueur" ? "bien" : "attention"}`}>{p.statut.libelle}</span>
      </div>
      <p className="discret">{p.numero_police ? t(`Police n° ${p.numero_police}`, `Policy no. ${p.numero_police}`) : t("Numéro à venir", "Number to come")}
        {" · "}{t(`effet au ${dateFr(p.date_effet)}`, `effective ${dateFr(p.date_effet)}`)} · {periodicites()[p.periodicite] ?? p.periodicite}</p>
      <ol className="frise-police" aria-label={t("Étapes", "Steps")}>
        {p.statut.etapes.map((e) => (
          <li key={e.code} data-fait={e.fait}><span className="rond" aria-hidden="true">{e.fait ? "✓" : ""}</span>
            <span>{e.libelle}</span>{e.le && <span className="discret">{dateFr(e.le)}</span>}</li>
        ))}
      </ol>

      <h3>{t("Documents", "Documents")}</h3>
      <Pieces orgId={orgId} policeId={p.id} pieces={p.pieces} />
      {conseiller && (
        <Depot libelle={t("Déposer la police, un avenant ou la copie signée", "Upload the policy, a rider or the signed copy")}
          envoyer={async (fichier, f) => deposer(String(f.get("nature") || "police"))(fichier)}>
          <label>{t("Nature", "Type")}<select name="nature" defaultValue={recue ? "avenant" : "police"}>
            {["police", "avenant", "police_signee"].map((n) => <option key={n} value={n}>{natures()[n]}</option>)}</select></label>
        </Depot>
      )}
      {role === "admin_client" && recue && (
        <Depot libelle={t("Déposer la copie signée de la police", "Upload the signed copy of the policy")} envoyer={deposer("police_signee")} />
      )}
      {conseiller && !p.numero_police && (
        <form className="formulaire en-ligne" onSubmit={(ev) => { ev.preventDefault();
          const numero = String(new FormData(ev.currentTarget).get("numero") ?? "");
          agir(() => api.put(`/organisations/${orgId}/polices/${p.id}/numero`, { numero_police: numero })); }}>
          <label>{t("Numéro de police", "Policy number")}<input name="numero" required /></label>
          <button>{t("Enregistrer", "Save")}</button>
        </form>
      )}
      {recue && !p.signee_le && (role === "admin_client" || conseiller) && (
        <form className="formulaire en-ligne" onSubmit={(ev) => { ev.preventDefault();
          const le = String(new FormData(ev.currentTarget).get("signee_le") ?? "");
          agir(() => api.post(`/organisations/${orgId}/polices/${p.id}/signature`, { signee_le: le })); }}>
          <label>{t("Signée avec l'assureur le", "Signed with the insurer on")}
            <input type="date" name="signee_le" required max={aujourdHui()} /></label>
          <button className="principal">{t("Déclarer la signature", "Record the signature")}</button>
        </form>
      )}
      <Erreur erreur={erreur} />

      <h3>{t("Appels de prime", "Premium calls")}</h3>
      {p.appels.length === 0 ? <p className="discret">{t("Aucun appel de prime pour l'instant.", "No premium call yet.")}</p>
        : p.appels.map((a) => <FicheAppel key={a.id} orgId={orgId} policeId={p.id} role={role} a={a} onFait={onFait} />)}
      {conseiller && (nouvelAppel
        ? <NouvelAppelForm orgId={orgId} policeId={p.id} onFermer={() => setNouvelAppel(false)} onFait={() => { setNouvelAppel(false); onFait(); }} />
        : <div className="actions"><button type="button" onClick={() => setNouvelAppel(true)}>{t("Enregistrer un appel de prime", "Record a premium call")}</button></div>)}

      <h3>{t("Relevés du fonds", "Fund statements")}</h3>
      <Releves orgId={orgId} p={p} />
      {conseiller && (
        <Depot libelle={t("Relevé de l'assureur", "Insurer's statement")} envoyer={async (fichier, f) =>
          deposer("releve", { releve_le: String(f.get("releve_le")), montant_fonds: String(f.get("montant_fonds")) })(fichier)}>
          <div className="grille-2">
            <label>{t("Date du relevé", "Statement date")}<input type="date" name="releve_le" required max={aujourdHui()} /></label>
            <label>{t("Fonds au relevé (F CFA)", "Fund on the statement (CFA F)")}<input type="number" name="montant_fonds" min={0} required /></label>
          </div>
        </Depot>
      )}
    </section>
  );
}

function Coordonnees({ a, role }: { a: Appel; role: string }) {
  const c = a.coordonnees;
  return (
    <div className={`coordonnees ${a.a_confirmer ? "a-confirmer" : "confirmees"}`}>
      {a.ne_pas_payer && role !== "conseiller" && (
        <p className="constat bloquant"><strong>{t("Ne pas payer : coordonnées bancaires à confirmer par votre conseiller.",
          "Do not pay: bank details to be confirmed by your adviser.")}</strong></p>
      )}
      <dl className="inscription-faits">
        <dt>{t("Banque", "Bank")}</dt><dd>{c.banque}</dd>
        <dt>{t("Titulaire", "Account holder")}</dt><dd>{c.titulaire}</dd>
        <dt>{t("IBAN / RIB", "IBAN / account")}</dt><dd className="chiffre">{c.iban}</dd>
        {c.bic && <><dt>BIC</dt><dd>{c.bic}</dd></>}
      </dl>
      <p className="discret">
        {a.controle === "conforme" ? t("✓ Conforme au compte que le courtier a enregistré pour cet assureur.",
            "✓ Matches the account the broker registered for this insurer.")
          : a.contre_appel ? t(`✓ Confirmées par contre-appel le ${dateFr(a.contre_appel.le)} auprès de ${a.contre_appel.aupres} (${a.contre_appel.par}).`,
            `✓ Confirmed by call-back on ${dateFr(a.contre_appel.le)} with ${a.contre_appel.aupres} (${a.contre_appel.par}).`)
          : a.controle === "modifie" ? t("⚠ Différentes du compte enregistré pour cet assureur.", "⚠ Different from the account registered for this insurer.")
          : t("⚠ Cet assureur n'a pas de compte au registre du courtier.", "⚠ This insurer has no account in the broker's register.")}
        {" "}{t("Les coordonnées ne sont jamais envoyées par courriel.", "Bank details are never sent by email.")}</p>
    </div>
  );
}

function FicheAppel({ orgId, policeId, role, a, onFait }: { orgId: string; policeId: string; role: string; a: Appel; onFait: () => void }) {
  const [erreur, setErreur] = useState<unknown>(null);
  const [etat, style] = etats()[a.etat];
  const conseiller = role === "conseiller";
  const entreprise = role === "admin_client" || role === "contributeur_client";
  async function envoyer(chemin: string, corps: unknown) {
    setErreur(null);
    try { await api.post(`/organisations/${orgId}${chemin}`, corps); onFait(); } catch (e) { setErreur(e); }
  }
  const piece = (nature: string) => async (fichier: File) => {
    const f = new FormData();
    f.set("nature", nature); f.set("fichier", fichier); f.set("appel_id", a.id);
    await api.post(`/organisations/${orgId}/polices/${policeId}/pieces`, f);
    onFait();
  };
  const quittance = a.pieces.some((x) => x.nature === "quittance");
  // Tant que les coordonnées ne sont pas confirmées, le formulaire ne s'offre pas à côté de « Ne pas payer » :
  // un virement déjà fait se déclare quand même (c'est un fait), mais il faut le demander.
  const [declarerQuandMeme, setDeclarerQuandMeme] = useState(false);
  return (
    <details className="appel" open={a.ne_pas_payer || a.etat === "en_retard"}>
      <summary>
        <strong>{a.reference}</strong>{a.premiere && <span className="discret"> · {t("première prime", "first premium")}</span>}
        <span className="chiffre"> · {montant(a.montant)}</span>
        <span className="discret"> · {t(`échéance ${dateFr(a.echeance)}`, `due ${dateFr(a.echeance)}`)}</span>{" "}
        <span className={`etat ${style}`}>{etat}</span>
        {a.a_confirmer && <>{" "}<span className="etat grave">{t("coordonnées à confirmer", "details to confirm")}</span></>}
      </summary>
      <Coordonnees a={a} role={role} />
      {conseiller && a.a_confirmer && (
        <form className="formulaire" onSubmit={(ev) => { ev.preventDefault(); const f = new FormData(ev.currentTarget);
          envoyer(`/appels/${a.id}/contre-appel`, { aupres: String(f.get("aupres")), telephone: String(f.get("telephone")), le: String(f.get("le")) }); }}>
          <p className="discret">{t("Rappeler l'assureur au numéro que vous connaissez — jamais celui de l'appel reçu — et faire confirmer ces coordonnées.",
            "Call the insurer back on the number you know — never the one on the call received — and have these details confirmed.")}</p>
          <div className="grille-2">
            <label>{t("Confirmé par (nom, service)", "Confirmed by (name, department)")}<input name="aupres" required /></label>
            <label>{t("Au numéro", "On the number")}<input name="telephone" required /></label>
            <label>{t("Le", "On")}<input type="date" name="le" required max={aujourdHui()} /></label>
          </div>
          <div className="actions"><button className="principal">{t("Enregistrer le contre-appel", "Record the call-back")}</button></div>
        </form>
      )}
      <Pieces orgId={orgId} policeId={policeId} pieces={a.pieces} />
      {a.virement && (
        <p>{t(`Virement déclaré le ${dateFr(a.virement.le)} : ${montant(a.virement.montant)}`, `Transfer declared on ${dateFr(a.virement.le)}: ${montant(a.virement.montant)}`)}
          {a.virement.reference && ` · ${a.virement.reference}`}
          {a.virement.ecart !== 0 && <>{" "}<span className="etat attention">{t(`écart ${montant(a.virement.ecart)}`, `difference ${montant(a.virement.ecart)}`)}</span></>}</p>
      )}
      {a.encaisse_le && <p>{t(`Encaissement confirmé par l'assureur le ${dateFr(a.encaisse_le)}.`, `Receipt confirmed by the insurer on ${dateFr(a.encaisse_le)}.`)}</p>}
      {conseiller && !a.pieces.some((x) => x.nature === "appel") && (
        <Depot libelle={t("Joindre l'appel de prime reçu", "Attach the premium call received")} envoyer={piece("appel")} />
      )}
      {entreprise && !a.virement && !a.encaisse_le && a.ne_pas_payer && !declarerQuandMeme && (
        <p className="discret"><button type="button" className="lien" onClick={() => setDeclarerQuandMeme(true)}>
          {t("Un virement a déjà été fait ? Le déclarer", "Already made a transfer? Declare it")}</button></p>
      )}
      {entreprise && !a.virement && !a.encaisse_le && (!a.ne_pas_payer || declarerQuandMeme) && (
        <form className="formulaire" onSubmit={(ev) => { ev.preventDefault(); const f = new FormData(ev.currentTarget);
          envoyer(`/appels/${a.id}/virement`, { vire_le: String(f.get("vire_le")), montant: Number(f.get("montant")),
            reference: String(f.get("reference") ?? "").trim() || null }); }}>
          <h4>{t("Déclarer le virement fait depuis votre banque", "Declare the transfer made from your bank")}</h4>
          <div className="grille-2">
            <label>{t("Viré le", "Transferred on")}<input type="date" name="vire_le" required max={aujourdHui()} /></label>
            <label>{t("Montant viré (F CFA)", "Amount transferred (CFA F)")}<input type="number" name="montant" min={1} required defaultValue={a.montant} /></label>
            <label>{t("Référence bancaire", "Bank reference")}<input name="reference" /></label>
          </div>
          <div className="actions"><button className="principal">{t("Déclarer le virement", "Declare the transfer")}</button></div>
        </form>
      )}
      {entreprise && a.virement && !a.pieces.some((x) => x.nature === "avis_virement") && (
        <Depot libelle={t("Joindre l'avis de virement de votre banque", "Attach your bank's transfer advice")} envoyer={piece("avis_virement")} />
      )}
      {conseiller && !a.encaisse_le && (quittance ? (
        <form className="formulaire en-ligne" onSubmit={(ev) => { ev.preventDefault();
          envoyer(`/appels/${a.id}/encaissement`, { encaisse_le: String(new FormData(ev.currentTarget).get("encaisse_le")) }); }}>
          <label>{t("Encaissée par l'assureur le", "Received by the insurer on")}<input type="date" name="encaisse_le" required max={aujourdHui()} /></label>
          <button className="principal">{t("Confirmer l'encaissement", "Confirm receipt")}</button>
        </form>
      ) : <Depot libelle={t("Déposer la quittance de l'assureur", "Upload the insurer's receipt")} envoyer={piece("quittance")} />)}
      <Erreur erreur={erreur} />
    </details>
  );
}

function NouvelAppelForm({ orgId, policeId, onFermer, onFait }: { orgId: string; policeId: string; onFermer: () => void; onFait: () => void }) {
  const [erreur, setErreur] = useState<unknown>(null);
  async function creer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const texte = (k: string) => String(f.get(k) ?? "").trim();
    setErreur(null);
    try {
      await api.post(`/organisations/${orgId}/polices/${policeId}/appels`, {
        reference: texte("reference"), montant: Number(f.get("montant")), echeance: texte("echeance"),
        premiere: f.get("premiere") === "on", banque: texte("banque"), titulaire: texte("titulaire"),
        iban: texte("iban"), bic: texte("bic") || null });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <form className="formulaire carte" onSubmit={creer} aria-label={t("Nouvel appel de prime", "New premium call")}>
      <h4 style={{ marginTop: 0 }}>{t("Nouvel appel de prime", "New premium call")}</h4>
      <div className="grille-2">
        <label>{t("Référence de l'appel", "Call reference")}<input name="reference" required /></label>
        <label>{t("Montant appelé (F CFA)", "Amount called (CFA F)")}<input type="number" name="montant" min={1} required /></label>
        <label>{t("Échéance", "Due date")}<input type="date" name="echeance" required /></label>
        <label className="case"><input type="checkbox" name="premiere" /> {t("Première prime", "First premium")}</label>
      </div>
      <p className="discret">{t("Les coordonnées bancaires telles qu'elles figurent SUR L'APPEL : elles seront confrontées au registre du courtier.",
        "The bank details as they appear ON THE CALL: they will be checked against the broker's register.")}</p>
      <div className="grille-2">
        <label>{t("Banque", "Bank")}<input name="banque" required /></label>
        <label>{t("Titulaire du compte", "Account holder")}<input name="titulaire" required /></label>
        <label>{t("IBAN / RIB", "IBAN / account")}<input name="iban" required minLength={10} /></label>
        <label>BIC<input name="bic" /></label>
      </div>
      <div className="actions"><button className="principal">{t("Enregistrer l'appel", "Record the call")}</button>
        <button type="button" onClick={onFermer}>{t("Annuler", "Cancel")}</button></div>
      <Erreur erreur={erreur} />
    </form>
  );
}

function Releves({ orgId, p }: { orgId: string; p: Police }) {
  const { releves, etude } = p.releves;
  if (!releves.length) return <p className="discret">{t("Aucun relevé déposé.", "No statement uploaded.")}</p>;
  return (
    <>
      <div className="defile"><table>
        <thead><tr><th>{t("Relevé du", "Statement of")}</th><th className="n">{t("Fonds au relevé", "Fund on statement")}</th>
          <th className="n">{t("Primes encaissées à cette date", "Premiums received to that date")}</th><th aria-label={t("Document", "Document")} /></tr></thead>
        <tbody>{releves.map((r) => (
          <tr key={r.id}><td>{dateFr(r.releve_le)}</td><td className="n chiffre">{montant(r.montant_fonds)}</td>
            <td className="n chiffre">{montant(r.primes_encaissees)}</td>
            <td className="n"><button className="lien" type="button"
              onClick={() => api.ouvrir(`/organisations/${orgId}/polices/${p.id}/pieces/${r.id}`)}>{t("Ouvrir", "Open")}</button></td></tr>
        ))}</tbody>
      </table></div>
      {etude && <p className="discret">{t(`La dernière étude émise (au ${dateFr(etude.date_evaluation)}) retient un fonds de ${montant(etude.fonds_disponible)}`,
        `The latest issued study (as at ${dateFr(etude.date_evaluation)}) uses a fund of ${montant(etude.fonds_disponible)}`)}
        {etude.ecart !== null && t(` ; écart avec le dernier relevé : ${montant(etude.ecart)}.`, `; difference with the latest statement: ${montant(etude.ecart)}.`)}</p>}
    </>
  );
}
