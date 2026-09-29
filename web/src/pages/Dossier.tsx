import { createContext, useContext, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useParams } from "react-router-dom";

import { api } from "../api";
import { Erreur, useCharge } from "../composants/communs";
import { AidePage } from "../composants/AidePage";
import { BarreMobile, BoutonAller, FilAriane, niveauxDe, PaletteAller } from "../composants/Navigation";
import Visite, { lancerVisite } from "../composants/Visite";
import { VISITE_DOSSIER } from "../guide/visite";
import { etapes, type EtatDossier } from "../parcours";
import { Icone } from "../composants/Icones";
import { noterReprise } from "../reprise";
import type { Equipe, EtatCycle, EtudeResume, Fiche, Fichier, Membre, Moi, Regime, Role } from "../types";
import { BandeauCycle } from "../composants/CycleDossier";
import { BandeauActivation } from "../composants/BandeauActivation";
import { t } from "../i18n";
import { CONFIRMEE, type Activation } from "../activation";


export interface ContexteDossier {
  org: { id: string; nom: string; pays: string; etat?: EtatCycle; etat_depuis?: string };
  role: Role;
  fichiers: Fichier[];
  regimes: Regime[];
  etudes: EtudeResume[];
  fiches: Fiche[];
  equipe: Membre[];
  etat: EtatDossier;
  activation: Activation;
  nonLus: number;
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
    const [moi, fichiers, regimes, etudes, fiches, equipe, activation, nonLus, mandat] = await Promise.all([
      api.get<Moi>("/moi"),
      api.get<Fichier[]>(`/organisations/${org}/fichiers`),
      api.get<Regime[]>(`/organisations/${org}/regimes`),
      api.get<EtudeResume[]>(`/organisations/${org}/etudes`),
      api.get<Fiche[]>(`/organisations/${org}/fiches`),
      api.get<Equipe>(`/organisations/${org}/equipe`).then((e) => e.membres),
      api.get<Activation>(`/organisations/${org}/activation`).catch(() => CONFIRMEE),
      api.get<{ non_lus: number }>(`/organisations/${org}/messages/non-lus`).then((r) => r.non_lus).catch(() => 0),
      api.get<{ mandats: { statut: string }[] }>(`/organisations/${org}/mandats`)
        .then((r) => {
          const s = r.mandats.map((m) => m.statut);
          return s.includes("signe") ? "signe" : s.includes("propose") ? "propose" : s.includes("demande") ? "demande" : "aucun";
        }).catch(() => null),
    ]);
    const o = moi.organisations.find((x) => x.id === org)!;
    const versions = regimes.flatMap((r) => r.versions);
    const etat: EtatDossier = {
      fichiers: fichiers.length, versions: versions.length,
      versionsAdoptees: versions.filter((v) => v.statut === "adoptee").length,     // en vigueur, à venir ou remplacée
      etudesEmises: etudes.filter((e) => e.statut === "emise").length,
      etudesBrouillon: etudes.filter((e) => e.statut === "brouillon").length,
      fiches: fiches.length, mandat: mandat as EtatDossier["mandat"], offreRetenue: fiches.some((f) => f.attribuee),
      sousMandat: activation.etat === "confirmee" && activation.capacites.cahier,
    };
    return { org: o, role: o.role, fichiers, regimes, etudes, fiches, equipe, etat, activation, nonLus, moiId: moi.id };
  }, [org]);

  const { pathname } = useLocation();
  const [menu, setMenu] = useState(false);
  useEffect(() => { setMenu(false); }, [pathname]);     // une page choisie referme le menu (téléphone)
  // Chaque page ouverte devient l'endroit où reprendre (« Vos dossiers » le proposera à la prochaine visite).
  useEffect(() => {
    if (!donnee) return;
    noterReprise(donnee.moiId, { org: donnee.org.id, chemin: pathname, quand: Date.now(),
                                 pages: niveauxDe(pathname, donnee).slice(2).map((n) => n.libelle) });
  }, [donnee, pathname]);

  if (erreur) return <Erreur erreur={erreur} />;
  if (!donnee) return <p className="discret">{t("Chargement du dossier…", "Loading the file…")}</p>;
  const contexte: ContexteDossier = { ...donnee, recharger };
  const conseiller = donnee.equipe.find((m) => m.role === "conseiller");

  return (
    <Contexte.Provider value={contexte}>
      <div className={donnee.activation.etat !== "confirmee" ? "dossier non-confirmee" : "dossier"}
           data-impression={donnee.activation.etat !== "confirmee"
             ? t("L'impression s'ouvre après confirmation de votre inscription", "Printing opens once your sign-up is confirmed")
             : undefined}>
        <aside>
          <div className="dossier-tete">
            <div>
              <NavLink to="." end className="discret" style={{ textDecoration: "none" }}>
                <h2 style={{ marginBottom: 2 }}>{donnee.org.nom}</h2>
              </NavLink>
              <div className="discret" style={{ marginBottom: 12 }}>{t("Tableau de bord du dossier", "File dashboard")}</div>
            </div>
            <button type="button" className="bouton-menu" aria-expanded={menu} aria-controls="menu-dossier"
                    onClick={() => setMenu(!menu)}>{menu ? t("Fermer", "Close") : t("Menu", "Menu")}</button>
          </div>
          <div id="menu-dossier" className="dossier-menu" data-ouvert={menu}>
          <BoutonAller />
          <ol className="parcours" data-visite="parcours">
            <li><NavLink to="." end className={({ isActive }) => (isActive ? "actif" : "")}>
              <Icone nom="tableau" />{t("Tableau de bord", "Dashboard")}</NavLink></li>
            {etapes(donnee.etat).map((e) => (
              <li key={e.cle} className={e.suivant ? "suivant" : ""}>
                <NavLink to={e.cle} className={({ isActive }) => (isActive ? "actif" : "")}
                         title={e.suivant ? t(`Étape suivante : ${e.aide}`, `Next step: ${e.aide}`) : undefined}>
                  <Icone nom={e.cle} />{e.libelle}
                  {e.suivant && <span className="point-suivant" aria-label={t("étape suivante", "next step")} />}
                </NavLink>
              </li>
            ))}
          </ol>
          <ol className="parcours" style={{ marginTop: 14 }} data-visite="outils">
            <li><NavLink to="contrat" className={({ isActive }) => (isActive ? "actif" : "")}>
              <Icone nom="contrat" />{t("Contrat", "Contract")}</NavLink></li>
            <li><NavLink to="placement" className={({ isActive }) => (isActive ? "actif" : "")}>
              <Icone nom="placement" />{t("Placement", "Placement")}</NavLink></li>
            <li><NavLink to="departs" className={({ isActive }) => (isActive ? "actif" : "")}>
              <Icone nom="departs" />{t("Départs", "Departures")}
              {donnee.activation.capacites.departs === false && (
                <span className="verrou-rail" title={t("Une fois le contrat d'assurance signé et en vigueur", "Once the insurance contract is signed and in force")}
                      aria-label={t("pas encore ouvert", "not open yet")}>
                  <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg></span>)}</NavLink></li>
            <li><NavLink to="contact" className={({ isActive }) => (isActive ? "actif" : "")}>
              <Icone nom="messages" />{t("Contact", "Contact")}
              {donnee.nonLus > 0 && <span className="pastille-rail" aria-label={t(`${donnee.nonLus} non lu(s)`, `${donnee.nonLus} unread`)}>{donnee.nonLus}</span>}</NavLink></li>
            <li><NavLink to="equipe" className={({ isActive }) => (isActive ? "actif" : "")}>
              <Icone nom="equipe" />{t("Équipe", "Team")}</NavLink></li>
          </ol>
          {conseiller && (
            <div className="carte" style={{ marginTop: 20 }} data-visite="conseiller">
              <div className="discret" style={{ marginBottom: 8 }}>
                {donnee.role === "conseiller" ? t("Vous suivez ce dossier", "You follow this file") : t("Votre conseiller", "Your adviser")}
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
          <div className="actions" style={{ marginTop: 16 }}>
            <button type="button" className="lien" onClick={lancerVisite}>{t("Visite guidée", "Guided tour")}</button>
            <NavLink to="/guide">{t("Le guide", "The guide")}</NavLink>
          </div>
          </div>
        </aside>
        <section>
          <div className="entete-page"><FilAriane d={donnee} /><AidePage base={`/dossier/${donnee.org.id}`} /></div>
          <BandeauCycle org={donnee.org} />
          <BandeauActivation orgId={donnee.org.id} activation={donnee.activation} role={donnee.role} />
          <Outlet />
        </section>
        <PaletteAller d={donnee} />
        <BarreMobile d={donnee} />
        <Visite etapes={VISITE_DOSSIER} auto />
      </div>
    </Contexte.Provider>
  );
}
