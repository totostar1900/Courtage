import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { Anomalies, Cle, Echeancier, Erreur, libelleMotif, useCharge } from "../composants/communs";
import { dateFr, millions, montant, pct } from "../format";
import { langue, t } from "../i18n";
import type { Etude } from "../types";
import { useConfirmation } from "../composants/Confirmer";
import { demandeSuppression, raisonDeNePasSupprimer } from "../suppressionEtude";
import { useDossier } from "./Dossier";
import Experience from "../composants/Experience";
import Rapprochement, { sousCotisation } from "../composants/Rapprochement";
import { raisonActivation } from "../activation";

const sensibilites = (): Record<string, string> => ({
  taux_actualisation_moins_1pt: t("Taux d'actualisation − 1 point", "Discount rate − 1 point"),
  taux_actualisation_plus_1pt: t("Taux d'actualisation + 1 point", "Discount rate + 1 point"),
  croissance_salaires_moins_1pt: t("Salaires − 1 point par an", "Salary growth − 1 point a year"),
  croissance_salaires_plus_1pt: t("Salaires + 1 point par an", "Salary growth + 1 point a year"),
  rotation_moins_1pt: t("Rotation − 1 point", "Staff turnover − 1 point"),
  rotation_plus_1pt: t("Rotation + 1 point", "Staff turnover + 1 point"),
});

const rang = (k: string) => { const i = Object.keys(sensibilites()).indexOf(k); return i < 0 ? 99 : i; };

export default function EtudeDetail() {
  const d = useDossier();
  const { etude: id } = useParams();
  const { donnee: e, erreur, recharger } = useCharge(() => api.get<Etude>(`/organisations/${d.org.id}/etudes/${id}`), [id]);
  const [erreurAction, setErreurAction] = useState<unknown>(null);
  const aller = useNavigate();
  const [demander, fenetre] = useConfirmation();

  if (erreur) return <Erreur erreur={erreur} />;
  if (!e) return <p className="discret">{t("Chargement…", "Loading…")}</p>;

  async function emettre() {
    setErreurAction(null);
    try { await api.post(`/organisations/${d.org.id}/etudes/${e!.id}/emission`); recharger(); d.recharger(); }
    catch (x) { setErreurAction(x); }
  }

  const attenteEmission = raisonActivation(d.activation, "rapport_scelle");
  const attenteExport = raisonActivation(d.activation, "export_etude");
  const retenue = raisonDeNePasSupprimer({ statut: e.statut, raison_de_garder: e.suppression?.raison_de_garder }, d.role);
  return (
    <>
      {fenetre}
      <div className="actions" style={{ justifyContent: "space-between", marginTop: 0 }}>
        <h1 style={{ margin: 0 }}>{t(`Évaluation au ${dateFr(e.date_evaluation)}`, `Valuation at ${dateFr(e.date_evaluation)}`)}</h1>
        {e.statut === "emise" ? <span className="etat bien">{t("Émise", "Issued")} · {e.rapport?.numero}</span>
          : <span className="etat attention">{t("Brouillon", "Draft")}</span>}
      </div>
      <p className="discret">
        {e.regime ? `${e.regime.nom}, version ${e.regime.numero}` : e.convention.libelle} · {e.totaux.effectif} {t("salariés", "employees")}
      </p>

      <div className={`grille g4 section${e.statut === "brouillon" ? " resultats-brouillon" : ""}`}
           data-filigrane={t("Estimation — non scellée", "Estimate — not sealed")}>
        <Cle etiquette={t("Dette actuarielle", "Actuarial liability")} terme="dette" valeur={millions(e.totaux.dette)} sous={montant(e.totaux.dette)} />
        <Cle etiquette={t("Charge annuelle", "Annual cost")} terme="charge" valeur={millions(e.totaux.charge)} sous={montant(e.totaux.charge)} />
        <Cle etiquette={t("Fonds constitué", "Accumulated fund")} terme="fonds" valeur={millions(e.fonds_disponible)} sous={montant(e.fonds_disponible)} />
        <Cle etiquette={t("Cotisation à verser", "Contribution payable")} terme="cotisation" valeur={millions(e.totaux.cotisation_totale ?? 0)} sous={sousCotisation(e)} />
      </div>
      <div className="carte section"><Rapprochement etude={e} /></div>
      {e.experience && <Experience x={e.experience} peutProposer={d.role !== "lecteur_client"} />}
      {e.totaux_convention && (
        langue() === "en"
          ? <p className="section">Your plan accounts for <strong>{montant(e.totaux.dette - e.totaux_convention.dette)}</strong> of
            liability beyond the collective agreement alone ({montant(e.totaux_convention.dette)}).</p>
          : <p className="section">Votre régime représente <strong>{montant(e.totaux.dette - e.totaux_convention.dette)}</strong> de
          dette au-delà de la seule convention ({montant(e.totaux_convention.dette)}).</p>
      )}

      <div className="carte section">
        {e.statut === "brouillon" && (
          e.emission.possible
            ? <p><span className="etat bien">{t("Prête", "Ready")}</span> {t("L'étude peut être émise.", "The study can be issued.")}</p>
            : <p><span className="etat grave">{t("Pas encore", "Not yet")}</span> {t("Avant l'émission :", "Before issuing:")} {e.emission.motifs.map(libelleMotif).join(" · ")}.</p>
        )}
        <div className="actions">
          {e.statut === "brouillon" && d.role === "conseiller" && (
            <button className="principal" onClick={emettre} disabled={!e.emission.possible || !!attenteEmission}
                    title={attenteEmission ?? undefined}>{t("Émettre et sceller le rapport", "Issue and seal the report")}</button>
          )}
          {e.statut === "brouillon" && d.role !== "conseiller" && (
            <span className="discret">{t("Votre conseiller relit puis émet le rapport.", "Your adviser reviews and then issues the report.")}</span>
          )}
          {e.rapport && (
            <button onClick={() => api.ouvrir(`/organisations/${d.org.id}/etudes/${e.id}/rapport`)}>{t("Ouvrir le rapport PDF", "Open the PDF report")}</button>
          )}
          <button disabled={!!attenteExport} title={attenteExport ?? undefined} onClick={() => { setErreurAction(null);
            api.telecharger(`/organisations/${d.org.id}/etudes/${e.id}/export`, `etude-ifc-${e.date_evaluation}.xlsx`)
              .catch(setErreurAction); }}>{t("Exporter en Excel", "Export to Excel")}</button>
          {d.role !== "lecteur_client" && (
            <button className="danger" disabled={!!retenue} title={retenue ?? undefined}
                    onClick={() => demander(demandeSuppression(d.org.id, e, () => { d.recharger(); aller(".."); }))}>
              {e.statut === "emise" ? t("Supprimer l'étude", "Delete the study") : t("Supprimer ce brouillon", "Delete this draft")}</button>
          )}
          <Link to={`/dossier/${d.org.id}/financement`}><button>{t("Voir les offres des assureurs", "See the insurers' offers")}</button></Link>
        </div>
        {(attenteExport || (attenteEmission && e.statut === "brouillon" && d.role === "conseiller")) && (
          <p className="discret">{t("Émission et export Excel — ", "Issuing and Excel export — ")}{attenteExport ?? attenteEmission}</p>
        )}
        <Erreur erreur={erreurAction} />
      </div>

      <div className="carte section">
        <h3>{t("Départs prévus", "Expected departures")}</h3>
        <Echeancier annees={e.echeancier} fonds={e.fonds_disponible} />
      </div>
      <div className="grille g2 section">
        <div className="carte">
          <h3>{t("Sensibilités", "Sensitivities")}</h3>
          <div className="defile"><table><tbody>
            {Object.entries(e.sensibilites).sort(([a], [b]) => rang(a) - rang(b)).map(([k, v]) => (
              <tr key={k}><td>{sensibilites()[k] ?? k}</td><td className="n">{montant(v.dette)}</td>
                <td className="n">{pct((v.dette - e.totaux.dette) / e.totaux.dette)}</td></tr>
            ))}
          </tbody></table></div>
        </div>
        {e.hypotheses.lues && (
          <div className="carte">
            <h3>{t("Hypothèses retenues", "Assumptions used")}</h3>
            <div className="defile"><table>
              <thead><tr><th>{t("Hypothèse", "Assumption")}</th><th className="n">{t("Retenue", "Used")}</th>
                <th className="n">{t("Par défaut", "Default")}</th></tr></thead>
              <tbody>{e.hypotheses.lues.map((h) => (
                <tr key={h.champ} title={`${h.role} ${h.effet}`}>
                  <td>{h.libelle}{h.ecarte && <span className="etat attention" style={{ marginLeft: 6 }}>{t("ajustée", "adjusted")}</span>}</td>
                  <td className="n">{h.retenu}</td><td className="n discret">{h.defaut}</td></tr>))}</tbody>
            </table></div>
            {e.hypotheses.justification && <p className="discret">{t("Justification :", "Justification:")} {e.hypotheses.justification}</p>}
            <details className="repli">
              <summary>{t("Ce que fait chaque hypothèse", "What each assumption does")}</summary>
              {e.hypotheses.lues.map((h) => (
                <p key={h.champ}><b>{h.libelle}.</b> {h.role} {h.effet}</p>))}
            </details>
          </div>
        )}
      </div>

      {e.par_categorie && (
        <div className="carte section">
          <h3>{t("Par catégorie", "By category")}</h3>
          <div className="defile"><table><thead><tr><th>{t("Catégorie", "Category")}</th><th className="n">{t("Effectif", "Headcount")}</th>
            <th className="n">{t("Dette", "Liability")}</th><th className="n">{t("Charge", "Cost")}</th></tr></thead>
            <tbody>{Object.entries(e.par_categorie).map(([k, c]) => (
              <tr key={k}><td>{k === "*" ? t("Autres", "Others") : k}</td><td className="n">{c.effectif}</td>
                <td className="n">{montant(c.dette)}</td><td className="n">{montant(c.charge)}</td></tr>))}</tbody></table></div>
        </div>
      )}

      <div className="section">
        <h2>{t("Points d'attention", "Points to watch")}</h2>
        <Anomalies anomalies={e.anomalies} />
      </div>
    </>
  );
}
