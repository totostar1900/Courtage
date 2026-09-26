// Portage fidèle de courtage.financement (Python) pour la démonstration statique :
// mêmes étapes, même ordre, mêmes arrondis à la sortie. Vérifié contre la sortie Python (financement.test.ts).

export interface Engagement { annee_evaluation: number; dette: number; charge: number; fonds_initial: number; prestations: Record<number, number> }
export interface OffreF { nom: string; taux_garanti?: number; participation_benefices?: number; frais_sur_cotisations?: number; frais_sur_encours?: number; interne?: boolean }
export interface ScenarioF { nom: string; rendement: number }
export interface ParametresF { horizon: number; amortissement_annees: number; taux_actualisation: number; croissance_salaires: number; scenario_de_reference?: string }

export const SCENARIOS: ScenarioF[] = [
  { nom: "prudent", rendement: 0.035 }, { nom: "central", rendement: 0.05 }, { nom: "favorable", rendement: 0.065 }];

export function projeter(e: Engagement, offres: OffreF[], scenarios: ScenarioF[], p: ParametresF) {
  const deficit = Math.max(e.dette - e.fonds_initial, 0);
  const annuite = deficit / p.amortissement_annees;
  const reference = scenarios.find((s) => s.nom === (p.scenario_de_reference ?? "central"))?.nom ?? scenarios[0].nom;
  const resultats = offres.map((o) => ({
    nom: o.nom, interne: !!o.interne,
    conditions: { taux_garanti: o.taux_garanti ?? 0, participation_benefices: o.participation_benefices ?? 0,
                  frais_sur_cotisations: o.frais_sur_cotisations ?? 0, frais_sur_encours: o.frais_sur_encours ?? 0 },
    scenarios: scenarios.map((s) => une(e, o, s, p, annuite)),
  }));
  const cout = (o: (typeof resultats)[number]) => o.scenarios.find((s) => s.scenario === reference)!.cout_net_actualise;
  return {
    plan_amortissement: { deficit_initial: deficit, annees: p.amortissement_annees, annuite },
    scenario_de_reference: reference,
    offres: resultats,
    classement: [...resultats].sort((a, b) => cout(a) - cout(b)).map((o) => o.nom),
  };
}

function une(e: Engagement, o: OffreF, s: ScenarioF, p: ParametresF, annuite: number) {
  const garanti = o.taux_garanti ?? 0;
  const taux = garanti + (o.participation_benefices ?? 0) * Math.max(s.rendement - garanti, 0);
  let fonds = e.fonds_initial, coutTotal = 0, coutActualise = 0, frais = 0;
  const annees = [], decouverts: number[] = [];
  for (let t = 1; t <= p.horizon; t++) {
    const annee = e.annee_evaluation + t;
    const charge = e.charge * (1 + p.croissance_salaires) ** (t - 1);
    const amortissement = t <= p.amortissement_annees ? annuite : 0;
    const cotisation = charge + amortissement;
    const fraisCot = cotisation * (o.frais_sur_cotisations ?? 0);
    const debut = fonds;
    fonds += cotisation - fraisCot;
    const interets = fonds * taux;
    fonds += interets;
    const fraisEnc = fonds * (o.frais_sur_encours ?? 0);
    fonds -= fraisEnc;
    let prestations = 0;
    for (const [a, v] of Object.entries(e.prestations)) if (t === 1 ? Number(a) <= annee : Number(a) === annee) prestations += v;
    const payees = Math.min(prestations, Math.max(fonds, 0));
    fonds -= payees;
    const decouvert = prestations - payees;
    if (decouvert > 1e-9) decouverts.push(annee);
    const cout = cotisation + decouvert;
    coutTotal += cout;
    coutActualise += cout / (1 + p.taux_actualisation) ** t;
    frais += fraisCot + fraisEnc;
    annees.push({ annee, fonds_debut: debut, cotisation, prestations, payees_par_le_fonds: payees, decouvert, fonds_fin: fonds, taux_credite: taux });
  }
  const derniere = e.annee_evaluation + p.horizon;
  let restant = 0;
  for (const [a, v] of Object.entries(e.prestations)) if (Number(a) > derniere) restant += v / (1 + p.taux_actualisation) ** (Number(a) - derniere);
  return {
    scenario: s.nom, rendement: s.rendement, annees, cout_total: coutTotal, frais_totaux: frais,
    annees_decouvert: decouverts, fonds_final: fonds, prestations_restantes_actualisees: restant,
    couverture_des_departs_restants: restant > 0 ? fonds / restant : null,
    cout_net_actualise: coutActualise - fonds / (1 + p.taux_actualisation) ** p.horizon,
  };
}

const TAUX = new Set(["couverture_des_departs_restants", "taux_credite", "rendement", "taux_garanti",
  "participation_benefices", "frais_sur_cotisations", "frais_sur_encours"]);

/** Les montants en francs entiers, les taux restent des taux (comme services/financement.py). */
export function arrondir(x: unknown, cle = ""): unknown {
  if (Array.isArray(x)) return x.map((v) => arrondir(v));
  if (x && typeof x === "object") return Object.fromEntries(Object.entries(x).map(([k, v]) => [k, TAUX.has(k) ? v : arrondir(v, k)]));
  if (typeof x === "number" && !Number.isInteger(x) && !TAUX.has(cle)) return Math.round(x);
  return x;
}
