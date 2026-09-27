import { useState, type FormEvent } from "react";

import { api } from "../api";
import { t } from "../i18n";
import { useDossier } from "../pages/Dossier";
import type { Catalogue, PartageDossier, Version } from "../types";
import { Erreur, useCharge, Volet } from "./communs";

const taillePour = (effectif: number | undefined) =>
  effectif === undefined ? "50_a_250" : effectif < 50 ? "moins_de_50" : effectif <= 250 ? "50_a_250" : "plus_de_250";

/** Partager une version adoptée dans le catalogue anonyme : l'acte de l'entreprise, avec son accord. */
export default function PartageCatalogue({ version }: { version: Version }) {
  const d = useDossier();
  const { donnee: partages, recharger } = useCharge(
    () => api.get<PartageDossier[]>(`/organisations/${d.org.id}/regimes/partages`), [d.org.id]);
  const [ouvert, setOuvert] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  if (!partages) return null;
  const actif = partages.find((p) => p.actif);
  const celuiCi = actif?.version_id === version.id ? actif : null;

  async function retirer() {
    setErreur(null);
    try { await api.post(`/organisations/${d.org.id}/regimes/partages/${celuiCi!.partage_id}/retrait`); recharger(); }
    catch (e) { setErreur(e); }
  }

  return (
    <div className="partage-catalogue section">
      {celuiCi ? (
        <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
          <span>
            <span className="etat bien">{t("Partagé anonymement", "Shared anonymously")}</span>{" "}
            <span className="discret">{celuiCi.visible ? t("visible dans le catalogue.", "visible in the catalogue.")
              : t("en attente : un régime se montre quand son groupe réunit au moins cinq entreprises.",
                "pending: a plan is shown once its group has at least five companies.")}</span>
          </span>
          {d.role === "admin_client" && <button type="button" onClick={retirer}>{t("Retirer du catalogue", "Remove from the catalogue")}</button>}
        </div>
      ) : d.role === "admin_client" ? (
        !ouvert && (
          <div className="actions" style={{ marginTop: 0 }}>
            <button type="button" onClick={() => setOuvert(true)}>{t("Partager anonymement", "Share anonymously")}</button>
            <span className="discret">{t("Aider d'autres entreprises à écrire le leur, sans qu'elles sachent qui vous êtes.",
              "Help other companies write theirs, without them knowing who you are.")}</span>
          </div>
        )
      ) : null}
      {ouvert && <Formulaire version={version} remplace={Boolean(actif)} onFermer={() => setOuvert(false)}
                             onFait={() => { setOuvert(false); recharger(); }} />}
      <Erreur erreur={erreur} />
    </div>
  );
}

function Formulaire({ version, remplace, onFermer, onFait }:
  { version: Version; remplace: boolean; onFermer: () => void; onFait: () => void }) {
  const d = useDossier();
  const { donnee: listes } = useCharge(() => api.get<Catalogue>("/catalogue/regimes"), []);
  const [accord, setAccord] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  async function partager(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    setErreur(null);
    try {
      await api.post(`/organisations/${d.org.id}/regimes/versions/${version.id}/partage`,
                     { secteur: f.get("secteur"), taille: f.get("taille"), consentement: accord });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre={t("Partager anonymement", "Share anonymously")} onFermer={onFermer}>
      <form className="formulaire" onSubmit={partager}>
        <div className="grille g2">
          <div>
            <h4>{t("Ce qui part", "What is shared")}</h4>
            <ul>
              <li>{t("le barème de chaque catégorie, et ses conditions (ancienneté minimale, plafond, base de salaire) ;",
                "each category's scale and its conditions (minimum length of service, cap, salary basis);")}</li>
              <li>{t("le pays, le secteur et la tranche de taille que vous choisissez ci-dessous ;",
                "the country, the sector and the size band you choose below;")}</li>
              <li>{t("la convention collective, montrée seulement si le secteur l'est.",
                "the collective agreement, shown only if the sector is.")}</li>
            </ul>
          </div>
          <div>
            <h4>{t("Ce qui ne part pas", "What is not shared")}</h4>
            <ul>
              <li>{t("le nom de l'entreprise, ni aucun nom de personne ;", "the company's name, or anyone's name;")}</li>
              <li>{t("le document, la note, les dates ;", "the document, the notice, the dates;")}</li>
              <li>{t("un nom de catégorie inhabituel, remplacé par « Catégorie A, B… ».",
                "an unusual category name, replaced by “Category A, B…”.")}</li>
            </ul>
          </div>
        </div>
        <p className="discret">{t("Votre régime ne se montre que dans un groupe d'au moins cinq entreprises ; si le vôtre est "
          + "trop petit, le groupe s'élargit (le secteur, puis le pays s'effacent). Vous pouvez le retirer à tout moment, "
          + "pour l'avenir.",
          "Your plan is shown only within a group of at least five companies; if yours is too small, the group widens "
          + "(the sector, then the country, are dropped). You can withdraw it at any time, for the future.")}
          {remplace && t(" Il remplacera le régime que vous partagez aujourd'hui.", " It will replace the plan you share today.")}</p>
        <div className="grille g2">
          <label>{t("Secteur", "Sector")}
            <select name="secteur" defaultValue="commerce">
              {Object.entries(listes?.secteurs ?? { commerce: t("Commerce et distribution", "Retail and distribution") }).map(([k, l]) =>
                <option key={k} value={k}>{l}</option>)}
            </select>
          </label>
          <label>{t("Taille", "Size")}
            <select name="taille" defaultValue={taillePour(d.fichiers[0]?.effectif)}>
              {Object.entries(listes?.tailles ?? { moins_de_50: t("moins de 50 salariés", "fewer than 50 employees"),
                                                   "50_a_250": t("50 à 250 salariés", "50 to 250 employees"),
                                                   plus_de_250: t("plus de 250 salariés", "more than 250 employees") }).map(([k, l]) =>
                <option key={k} value={k}>{l}</option>)}
            </select>
          </label>
        </div>
        <label style={{ display: "flex", gap: 8, fontWeight: 400 }}>
          <input type="checkbox" checked={accord} onChange={(e) => setAccord(e.target.checked)} />
          <span>{t("Au nom de l'entreprise, j'accepte de partager ce régime dans le catalogue anonyme.",
            "On behalf of the company, I agree to share this plan in the anonymous catalogue.")}</span>
        </label>
        <div className="actions"><button className="principal" disabled={!accord}>{t("Partager", "Share")}</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
