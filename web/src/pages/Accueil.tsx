import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api";
import { DecompteAlertes } from "../composants/Alertes";
import { Erreur, useCharge, Volet } from "../composants/communs";
import FileInscriptions from "../composants/FileInscriptions";
import { ilYa, lireReprise } from "../reprise";
import type { Alerte, Moi } from "../types";
import { t } from "../i18n";

type Decomptes = Record<string, Record<Alerte["niveau"], number>>;

const roles = () => ({
  admin_client: t("Votre entreprise", "Your company"),
  contributeur_client: t("Votre entreprise (contribution)", "Your company (contributor)"),
  lecteur_client: t("En lecture", "Read-only"), conseiller: t("Vous conseillez", "You advise") });

/** Les pays que la plateforme couvre : ceux de la CEMAC, dont elle connaît les conventions. Une fonction : les noms
 *  suivent la langue du moment. */
export const paysCemac = () => ({
  CM: t("Cameroun", "Cameroon"), GA: t("Gabon", "Gabon"), CG: t("Congo", "Congo"), TD: t("Tchad", "Chad"),
  CF: t("Centrafrique", "Central African Republic"), GQ: t("Guinée équatoriale", "Equatorial Guinea") });

export default function Accueil() {
  const { donnee: moi, erreur, recharger: relireMoi } = useCharge(() => api.get<Moi>("/moi"), []);
  const [ouvrir, setOuvrir] = useState(false);
  const { donnee: decomptes } = useCharge(
    () => api.get<Decomptes>("/alertes").catch((): Decomptes => ({})), []);
  return (
    <>
      <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>{t("Vos dossiers", "Your files")}</h1>
        {moi?.admin_plateforme && !ouvrir && (
          <button type="button" className="principal" onClick={() => setOuvrir(true)}>{t("Ouvrir un dossier client", "Open a client file")}</button>
        )}
      </div>
      <Erreur erreur={erreur} />
      {moi && <Reprendre moi={moi} />}
      {ouvrir && <NouveauDossier onFermer={() => setOuvrir(false)} />}
      {moi?.admin_plateforme && <FileInscriptions onDecision={relireMoi} />}
      {moi && moi.organisations.length === 0 && (
        <p>{t("Aucun dossier pour l'instant.", "No files yet.")}{moi.admin_plateforme
          && t(" En tant que plateforme, vous ouvrez les dossiers des clients : « Ouvrir un dossier client », puis inscrivez la DRH par son numéro.",
               " As the platform, you open client files: “Open a client file”, then register the HR director by their phone number.")}</p>
      )}
      <div className="grille g3">
        {moi?.organisations.map((o) => (
          <Link key={o.id} to={`/dossier/${o.id}`} className="carte lien">
            <h2 style={{ marginBottom: 4 }}>{o.nom}</h2>
            <div className="discret">{paysCemac()[o.pays as keyof ReturnType<typeof paysCemac>] ?? o.pays} · {roles()[o.role]}</div>
            {o.etat === "suspendu" && <div style={{ marginTop: 8 }}><span className="etat attention">{t("Suspendu", "Suspended")}</span></div>}
            {o.etat === "cloture" && <div style={{ marginTop: 8 }}><span className="etat neutre">{t("Clôturé · lecture seule", "Closed · read-only")}</span></div>}
            <div style={{ marginTop: 8 }}><DecompteAlertes decompte={decomptes?.[o.id]} /></div>
          </Link>
        ))}
      </div>
    </>
  );
}

/** La dernière page ouverte, si son dossier est toujours le vôtre : un clic pour y revenir. */
function Reprendre({ moi }: { moi: Moi }) {
  const reprise = lireReprise(moi.id);
  const org = reprise && moi.organisations.find((o) => o.id === reprise.org);
  if (!reprise || !org) return null;
  return (
    <section className="carte reprendre section" aria-label={t("Reprendre où vous en étiez", "Pick up where you left off")}>
      <div>
        <div className="discret">{t("Reprendre où vous en étiez", "Pick up where you left off")} · {ilYa(reprise.quand)}</div>
        <strong>{[org.nom, ...reprise.pages].join(" › ")}</strong>
      </div>
      <Link to={reprise.chemin} className="bouton principal">{t("Reprendre", "Resume")}</Link>
    </section>
  );
}

function NouveauDossier({ onFermer }: { onFermer: () => void }) {
  const aller = useNavigate();
  const [erreur, setErreur] = useState<unknown>(null);
  async function ouvrir(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      const org = await api.post<{ id: string }>("/organisations", {
        nom: String(f.get("nom") ?? "").trim(), pays: f.get("pays"),
        secteur: String(f.get("secteur") ?? "").trim() || null, suivre: true });
      aller(`/dossier/${org.id}/equipe`);
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre={t("Ouvrir un dossier client", "Open a client file")} onFermer={onFermer}>
      <form className="formulaire" onSubmit={ouvrir}>
        <p className="discret">{t("Le dossier d'une entreprise cliente. Vous en devenez le conseiller ; vous y inscrivez "
          + "ensuite sa DRH, qui se connectera avec son numéro.",
          "A client company's file. You become its adviser; you then register its HR director, who will sign in with "
          + "their phone number.")}</p>
        <div className="grille g3">
          <label>{t("Entreprise", "Company")}<input name="nom" required /></label>
          <label>{t("Pays", "Country")}
            <select name="pays" defaultValue="CM">
              {Object.entries(paysCemac()).map(([code, nom]) => <option key={code} value={code}>{nom}</option>)}
            </select>
          </label>
          <label>{t("Secteur", "Sector")}<input name="secteur" placeholder={t("facultatif", "optional")} /></label>
        </div>
        <div className="actions"><button className="principal">{t("Ouvrir le dossier", "Open the file")}</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
