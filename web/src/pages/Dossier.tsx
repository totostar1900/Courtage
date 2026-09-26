import { createContext, useContext } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { etapes, type EtatDossier } from "../parcours";
import type { EtudeResume, Fiche, Fichier, Moi, Regime, Role } from "../types";

interface Membre { id: string; nom: string; email: string | null; telephone: string | null; role: Role }

export interface ContexteDossier {
  org: { id: string; nom: string; pays: string };
  role: Role;
  fichiers: Fichier[];
  regimes: Regime[];
  etudes: EtudeResume[];
  fiches: Fiche[];
  equipe: Membre[];
  etat: EtatDossier;
  recharger: () => void;
}

const Contexte = createContext<ContexteDossier | null>(null);

export function useDossier(): ContexteDossier {
  const c = useContext(Contexte);
  if (!c) throw new Error("hors d'un dossier");
  return c;
}

export default function Dossier() {
  const { org } = useParams();
  const { donnee, erreur, recharger } = useCharge(async () => {
    const [moi, fichiers, regimes, etudes, fiches, equipe] = await Promise.all([
      api.get<Moi>("/moi"),
      api.get<Fichier[]>(`/organisations/${org}/fichiers`),
      api.get<Regime[]>(`/organisations/${org}/regimes`),
      api.get<EtudeResume[]>(`/organisations/${org}/etudes`),
      api.get<Fiche[]>(`/organisations/${org}/fiches`),
      api.get<Membre[]>(`/organisations/${org}/equipe`),
    ]);
    const o = moi.organisations.find((x) => x.id === org)!;
    const versions = regimes.flatMap((r) => r.versions);
    const etat: EtatDossier = {
      fichiers: fichiers.length, versions: versions.length,
      versionsAdoptees: versions.filter((v) => v.statut === "adoptee").length,
      etudesEmises: etudes.filter((e) => e.statut === "emise").length,
      etudesBrouillon: etudes.filter((e) => e.statut === "brouillon").length,
      fiches: fiches.length,
    };
    return { org: o, role: o.role, fichiers, regimes, etudes, fiches, equipe, etat };
  }, [org]);

  if (erreur) return <Erreur erreur={erreur} />;
  if (!donnee) return <p className="discret">Chargement du dossier…</p>;
  const contexte: ContexteDossier = { ...donnee, recharger };
  const conseiller = donnee.equipe.find((m) => m.role === "conseiller");

  return (
    <Contexte.Provider value={contexte}>
      <div className="dossier">
        <aside>
          <NavLink to="." end className="discret" style={{ textDecoration: "none" }}>
            <h2 style={{ marginBottom: 2 }}>{donnee.org.nom}</h2>
          </NavLink>
          <div className="discret" style={{ marginBottom: 16 }}>Tableau de bord du dossier</div>
          <ol className="parcours">
            {etapes(donnee.etat).map((e, i) => (
              <li key={e.cle} className={e.fait ? "fait" : e.suivant ? "suivant" : ""}>
                <NavLink to={e.cle} className={({ isActive }) => (isActive ? "actif" : "")}>
                  <span className="pastille">{e.fait ? "✓" : i + 1}</span>{e.libelle}
                </NavLink>
              </li>
            ))}
          </ol>
          <ol className="parcours" style={{ marginTop: 14 }}>
            <li><NavLink to="simulation" className={({ isActive }) => (isActive ? "actif" : "")}>
              <span className="pastille">≈</span>Simuler</NavLink></li>
            <li><NavLink to="remuneration" className={({ isActive }) => (isActive ? "actif" : "")}>
              <span className="pastille">F</span>Rémunération</NavLink></li>
          </ol>
          {conseiller && (
            <div className="carte" style={{ marginTop: 20 }}>
              <div className="discret" style={{ marginBottom: 8 }}>
                {donnee.role === "conseiller" ? "Vous suivez ce dossier" : "Votre conseiller"}
              </div>
              <div className="conseiller">
                <div className="avatar">{conseiller.nom.slice(0, 1)}</div>
                <div>
                  <strong>{conseiller.nom}</strong>
                  <div className="discret">{conseiller.email ?? conseiller.telephone}</div>
                </div>
              </div>
            </div>
          )}
        </aside>
        <section><Outlet /></section>
      </div>
    </Contexte.Provider>
  );
}
