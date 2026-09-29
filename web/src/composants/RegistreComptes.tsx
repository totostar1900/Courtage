import { useState, type FormEvent } from "react";

import { api } from "../api";
import { dateFr } from "../format";
import { t } from "../i18n";
import { Erreur, useCharge, Volet } from "./communs";

interface Compte { id: string; assureur: string; banque: string; titulaire: string; iban: string; bic: string | null;
  note: string | null; contre_appel: { aupres: string; telephone: string; le: string }; enregistre_par: string;
  enregistre_le: string }
interface Ligne { assureur: string; en_vigueur: Compte | null; historique: Compte[] }

/** Le registre des comptes bancaires des assureurs, tenu par le courtier : chaque appel de prime y est confronté.
 *  Un compte s'enregistre après un contre-appel ; un changement remplace sans effacer. */
export default function RegistreComptes() {
  const { donnee, erreur, recharger } = useCharge(() => api.get<{ assureurs: Ligne[] }>("/assureurs/comptes"), []);
  const [ouvert, setOuvert] = useState<{ assureur?: string } | null>(null);
  return (
    <section className="section" aria-labelledby="registre-comptes">
      <div className="actions" style={{ justifyContent: "space-between", marginTop: 0 }}>
        <h2 id="registre-comptes" style={{ margin: 0 }}>{t("Comptes bancaires des assureurs", "Insurers' bank accounts")}</h2>
        <button type="button" onClick={() => setOuvert({})}>{t("Enregistrer un compte", "Record an account")}</button>
      </div>
      <p className="discret">{t("Chaque appel de prime est confronté à ce registre : un compte différent ou inconnu est signalé au client, qui ne paie pas avant votre contre-appel.",
        "Each premium call is checked against this register: a different or unknown account is flagged to the client, who does not pay before your call-back.")}</p>
      <Erreur erreur={erreur} />
      {donnee && donnee.assureurs.length === 0 && <p className="discret">{t("Aucun compte enregistré.", "No account recorded.")}</p>}
      {donnee && donnee.assureurs.length > 0 && (
        <div className="defile"><table>
          <thead><tr><th>{t("Assureur", "Insurer")}</th><th>{t("Compte en vigueur", "Current account")}</th>
            <th>{t("Contre-appel", "Call-back")}</th><th aria-label={t("Actions", "Actions")} /></tr></thead>
          <tbody>{donnee.assureurs.map((l) => (
            <tr key={l.assureur}>
              <td>{l.assureur}{l.historique.length > 0 && <div className="discret">
                {t(`${l.historique.length} compte(s) remplacé(s)`, `${l.historique.length} replaced account(s)`)}</div>}</td>
              <td>{l.en_vigueur && <>{l.en_vigueur.banque}<div className="chiffre">{l.en_vigueur.iban}</div></>}</td>
              <td>{l.en_vigueur && <>{l.en_vigueur.contre_appel.aupres}<div className="discret">
                {l.en_vigueur.contre_appel.telephone} · {dateFr(l.en_vigueur.contre_appel.le)}</div></>}</td>
              <td className="n"><button className="lien" type="button" onClick={() => setOuvert({ assureur: l.assureur })}>
                {t("Changer de compte", "Change account")}</button></td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
      {ouvert && <NouveauCompte assureur={ouvert.assureur} onFermer={() => setOuvert(null)}
                                onFait={() => { setOuvert(null); recharger(); }} />}
    </section>
  );
}

function NouveauCompte({ assureur, onFermer, onFait }: { assureur?: string; onFermer: () => void; onFait: () => void }) {
  const [erreur, setErreur] = useState<unknown>(null);
  async function enregistrer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const x = (k: string) => String(f.get(k) ?? "").trim();
    setErreur(null);
    try {
      await api.post("/assureurs/comptes", { assureur: x("assureur"), banque: x("banque"), titulaire: x("titulaire"),
        iban: x("iban"), bic: x("bic") || null, verifie_aupres: x("verifie_aupres"),
        verifie_telephone: x("verifie_telephone"), verifie_le: x("verifie_le"), note: x("note") || null });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre={assureur ? t(`Nouveau compte : ${assureur}`, `New account: ${assureur}`) : t("Enregistrer un compte", "Record an account")} onFermer={onFermer}>
      <form className="formulaire" onSubmit={enregistrer}>
        <label>{t("Assureur", "Insurer")}<input name="assureur" required minLength={2} defaultValue={assureur} readOnly={!!assureur} /></label>
        <div className="grille-2">
          <label>{t("Banque", "Bank")}<input name="banque" required /></label>
          <label>{t("Titulaire", "Account holder")}<input name="titulaire" required /></label>
          <label>{t("IBAN / RIB", "IBAN / account")}<input name="iban" required minLength={10} /></label>
          <label>BIC<input name="bic" /></label>
        </div>
        <fieldset>
          <legend>{t("Contre-appel", "Call-back")}</legend>
          <p className="discret">{t("Appeler l'assureur au numéro que vous connaissez — jamais celui d'un courriel reçu — et faire confirmer ces coordonnées.",
            "Call the insurer on the number you know — never one from an email received — and have these details confirmed.")}</p>
          <div className="grille-2">
            <label>{t("Confirmé par (nom, service)", "Confirmed by (name, department)")}<input name="verifie_aupres" required /></label>
            <label>{t("Au numéro", "On the number")}<input name="verifie_telephone" required /></label>
            <label>{t("Le", "On")}<input type="date" name="verifie_le" required /></label>
          </div>
        </fieldset>
        <label>{t("Note", "Note")}<input name="note" /></label>
        <div className="actions"><button className="principal">{t("Enregistrer", "Save")}</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
