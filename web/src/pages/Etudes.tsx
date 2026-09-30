import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { useConfirmation } from "../composants/Confirmer";
import { ChoixConvention } from "../composants/ChoixConvention";
import { ComparerRegimes } from "../composants/ComparerRegimes";
import { MenuActions } from "../composants/MenuActions";
import { CONVENTION_PAR_PAYS } from "../composants/EditeurCategories";
import { aEnvoyer, Hypotheses, saisieParDefaut, type SaisieHypotheses } from "../composants/Hypotheses";
import { dateFr, montant } from "../format";
import { t } from "../i18n";
import { enCours, libelleVersion, ordonner } from "../regimes";
import type { CatalogueHypotheses, Etude } from "../types";
import { demandeSuppression, raisonDeNePasSupprimer } from "../suppressionEtude";
import { useDossier } from "./Dossier";
import { raisonActivation } from "../activation";

export default function Etudes() {
  const d = useDossier();
  const naviguer = useNavigate();
  const [erreur, setErreur] = useState<unknown>(null);
  const [demander, fenetre] = useConfirmation();
  // Une hypothèse proposée par l'expérience réelle arrive ici, à confirmer : jamais appliquée sans décision.
  const [params] = useSearchParams();
  const proposee = params.get("turnover");
  // La version qui s'applique d'abord.
  const versions = d.regimes.flatMap((r) => ordonner(r.versions).map((v) => ({ ...v, nomRegime: r.nom })));
  const { donnee: catalogue } = useCharge(() => api.get<CatalogueHypotheses>("/referentiel/hypotheses"), []);
  // La dernière étude donne l'effet de chaque hypothèse mesuré sur l'entreprise.
  const derniere = d.etudes[0]?.id;
  const { donnee: precedente } = useCharge(
    () => (derniere ? api.get<Etude>(`/organisations/${d.org.id}/etudes/${derniere}`) : Promise.resolve(null)), [derniere]);
  const [saisie, setSaisie] = useState<SaisieHypotheses | null>(null);
  const [justification, setJustification] = useState(params.get("justification") ?? "");
  // La base de calcul : "" = le minimum de la convention collective ; sinon une version du régime de l'entreprise.
  const [base, setBase] = useState<string>(() => versions.find(enCours)?.id ?? "");
  const hypotheses = saisie ?? (catalogue ? saisieParDefaut(catalogue, proposee ? { taux_turnover: Number(proposee) } : {}) : null);
  const envoi = catalogue && hypotheses ? aEnvoyer(catalogue, hypotheses) : {};
  const ajustees = Object.keys(envoi).length > 0;

  async function lancer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const version = f.get("regime_version_id") as string;
    setErreur(null);
    try {
      const e = await api.post<Etude>(`/organisations/${d.org.id}/etudes`, {
        fichier_id: f.get("fichier_id"), date_evaluation: f.get("date_evaluation"),
        fonds_disponible: Number(f.get("fonds_disponible") || 0),
        ...(ajustees ? { hypotheses: envoi, justification } : {}),
        ...(version ? { regime_version_id: version } : { convention_code: f.get("convention_code") }),
      });
      d.recharger();
      naviguer(e.id);
    } catch (e) { setErreur(e); }
  }

  return (
    <>
      {fenetre}
      <h1>{t("Évaluer votre engagement", "Assess your liability")}</h1>
      <p>{t("La dette actuarielle, la charge de l'année, la cotisation à verser. Votre conseiller relit et émet le rapport, "
        + "scellé et vérifiable.", "The actuarial liability, the year's cost, the contribution payable. Your adviser reviews and "
        + "issues the report, sealed and verifiable.")}</p>
      {d.role !== "lecteur_client" && d.fichiers.length > 0 && (
        <form className="carte formulaire" onSubmit={lancer}>
          <div className="grille g4">
            <label>{t("Personnel", "Staff")}
              <select name="fichier_id">{d.fichiers.map((f) => <option key={f.id} value={f.id}>{f.nom_fichier}</option>)}</select>
            </label>
            <label>{t("Date d'évaluation (une clôture)", "Valuation date (a year-end)")}
              <input name="date_evaluation" type="date" required defaultValue={d.fichiers[0]?.date_donnees} />
            </label>
            <label>{t("Base de calcul", "Calculation basis")}
              <select name="regime_version_id" value={base} onChange={(e) => setBase(e.target.value)}>
                <option value="">{t("Le minimum de la convention collective", "The collective agreement's minimum")}</option>
                {versions.map((v) => <option key={v.id} value={v.id}>{t("Votre régime : ", "Your plan: ")}{libelleVersion(v, v.nomRegime)}</option>)}
              </select>
            </label>
            {base === "" && (
              <ChoixConvention pays={d.org.pays} libelle={t("Convention collective", "Collective agreement")} name="convention_code"
                               defaut={CONVENTION_PAR_PAYS[d.org.pays]} />
            )}
          </div>
          <p className="discret aide-base" data-base={base === "" ? "convention" : "regime"}>{base === ""
            ? t("Ce que la loi et la convention de votre branche vous obligent à verser, au minimum. C'est la base quand l'entreprise n'a rien décidé de plus ; comparez-la à votre régime pour voir ce que vos engagements propres coûtent en plus.",
                "What the law and your industry's collective agreement require you to pay, at the minimum. It is the basis when the company has decided nothing more; compare it with your plan to see what your own commitments cost on top.")
            : t("Ce que votre entreprise s'est engagée à verser : accord d'entreprise, usage ou contrats, au-dessus du minimum de la convention. Chaque catégorie de votre régime dit déjà sur quelle convention elle s'appuie ; il n'y a rien à choisir de plus.",
                "What your company has committed to pay: company agreement, practice or contracts, above the collective agreement's minimum. Each category of your plan already states the agreement it rests on; there is nothing more to choose.")}</p>
          <label style={{ maxWidth: 260 }}>{t("Fonds déjà constitué (F)", "Fund already accumulated (F)")}<input name="fonds_disponible" type="number" min={0} defaultValue={0} /></label>
          {proposee && (
            <div className="constat informe section">
              <div className="titre">{t("Rotation proposée par l'expérience réelle", "Staff turnover proposed from actual experience")}</div>
              <p>{t("Elle est reprise dans les hypothèses ci-dessous : la relire, la justifier, puis calculer.",
                "It is carried into the assumptions below: review it, justify it, then calculate.")}</p>
            </div>
          )}
          {catalogue && hypotheses && (
            <Hypotheses catalogue={catalogue} saisie={hypotheses} onChange={setSaisie} lues={precedente?.hypotheses.lues}
                        ouvert={Boolean(proposee)} />
          )}
          {ajustees && (
            <label className="section">{t("Justification des hypothèses ajustées (figurera au rapport)", "Justification for the adjusted assumptions (will appear in the report)")}
              <input name="justification" required value={justification} onChange={(e) => setJustification(e.target.value)} />
            </label>
          )}
          <div className="actions"><button className="principal">{t("Calculer", "Calculate")}</button></div>
          <Erreur erreur={erreur} />
        </form>
      )}
      {d.fichiers.length === 0 && <p>{t("Déposez d'abord le fichier de votre personnel.", "First upload your staff file.")}</p>}

      {d.fichiers.length > 0 && (
        <details className="pli section" id="comparer" open={params.has("version")}>
          <summary><span>{t("Comparer des régimes avant d'étudier", "Compare plans before the study")}</span>
            <span className="discret">{t("la convention, vos versions, une idée de barème — côte à côte", "the agreement, your versions, a scale idea — side by side")}</span></summary>
          <div className="pli-corps"><ComparerRegimes /></div>
        </details>
      )}

      <div className="section">
        <h2>{t("Vos études", "Your studies")}</h2>
        <div className="defile">
          <table>
            <thead><tr><th>{t("Évaluation au", "Valuation at")}</th><th>{t("Base", "Basis")}</th><th className="n">{t("Dette", "Liability")}</th>
              <th>{t("État", "Status")}</th><th aria-label={t("Actions", "Actions")} /></tr></thead>
            <tbody>
              {d.etudes.map((e) => (
                <tr key={e.id} className="cliquable" onClick={() => naviguer(e.id)}>
                  <td>{dateFr(e.date_evaluation)}</td>
                  <td>{e.convention_code}</td>
                  <td className="n">{montant(e.dette)}</td>
                  <td>{e.statut === "emise" ? <span className="etat bien">{t(`Émise le ${dateFr(e.emise_le)}`, `Issued on ${dateFr(e.emise_le)}`)}</span>
                    : <span className="etat attention">{t("Brouillon", "Draft")}</span>}</td>
                  <td className="n" onClick={(ev) => ev.stopPropagation()}>
                    <MenuActions libelle={t(`Actions sur l'étude au ${dateFr(e.date_evaluation)}`, `Actions on the study at ${dateFr(e.date_evaluation)}`)} actions={[
                      { libelle: t("Ouvrir", "Open"), agir: () => naviguer(e.id) },
                      { libelle: t("Rapport PDF", "PDF report"), cache: e.statut !== "emise",
                        agir: () => api.ouvrir(`/organisations/${d.org.id}/etudes/${e.id}/rapport`) },
                      { libelle: t("Exporter en Excel", "Export to Excel"), raison: raisonActivation(d.activation, "export_etude"), agir: () => { setErreur(null);
                        api.telecharger(`/organisations/${d.org.id}/etudes/${e.id}/export`, `etude-ifc-${e.date_evaluation}.xlsx`).catch(setErreur); } },
                      { libelle: e.statut === "emise" ? t("Supprimer l'étude", "Delete the study") : t("Supprimer ce brouillon", "Delete this draft"), danger: true,
                        raison: raisonDeNePasSupprimer(e, d.role) ?? undefined,
                        cache: d.role === "lecteur_client",
                        agir: () => demander(demandeSuppression(d.org.id, e, d.recharger)) },
                    ]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
