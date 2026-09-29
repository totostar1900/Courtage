import { Fragment, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { api, DEMO, ErreurApi } from "./api";
import { useCharge } from "./composants/communs";
import { changerLangue, t, useLangue } from "./i18n";
import PiedDePage from "./composants/PiedDePage";
import Visionneuse from "./composants/Visionneuse";
import Accueil from "./pages/Accueil";
import Cahier from "./pages/Cahier";
import Connexion from "./pages/Connexion";
import Contrat from "./pages/Contrat";
import Accompagnement from "./pages/Accompagnement";
import Departs from "./pages/Departs";
import Dossier from "./pages/Dossier";
import DossierPriseEnCharge from "./pages/DossierPEC";
import Equipe from "./pages/Equipe";
import Essai from "./pages/Essai";
import Inscription from "./pages/Inscription";
import { Conditions, Confidentialite, MentionsLegales } from "./pages/Legal";
import Messages from "./pages/Messages";
import EtudeDetail from "./pages/EtudeDetail";
import Etudes from "./pages/Etudes";
import Financement from "./pages/Financement";
import Guide from "./pages/Guide";
import Personnel from "./pages/Personnel";
import Placement from "./pages/Placement";
import Profil from "./pages/Profil";
import Regime from "./pages/Regime";
import Reponses from "./pages/Reponses";
import Simulation from "./pages/Simulation";
import TableauDeBord from "./pages/TableauDeBord";
import Verifier from "./pages/Verifier";
import Vitrine from "./pages/Vitrine";

export default function App() {
  // Changer de langue redessine tout : chaque texte se relit dans la nouvelle langue ; l'adresse reste.
  const l = useLangue();
  // `/` sans session : la vitrine. L'en-tête le sait, pour proposer « Se connecter » plutôt que le profil.
  const [visiteur, setVisiteur] = useState(false);
  return (
    <Fragment key={l}>
      <Entete visiteur={visiteur} />
      {DEMO && (
        <div className="bandeau-demo">
          {t("Démonstration : la Société Démo SA et ses 40 salariés sont fictifs. Les chiffres viennent du vrai moteur ; "
            + "les actions qui modifieraient le dossier sont désactivées.",
            "Demo: Société Démo SA and its 40 employees are fictitious. The figures come from the real engine; "
            + "actions that would change the file are disabled.")}
        </div>
      )}
      <Visionneuse />
      <main className="page">
        <Routes>
          <Route path="/verifier/:numero" element={<Verifier />} />
          <Route path="/verifier" element={<Verifier />} />
          <Route path="/connexion" element={<Connexion />} />
          <Route path="/inscription" element={<Inscription />} />
          <Route path="/essai" element={<Essai />} />
          <Route path="/guide/*" element={<Guide />} />
          <Route path="/mentions-legales" element={<MentionsLegales />} />
          <Route path="/conditions" element={<Conditions />} />
          <Route path="/confidentialite" element={<Confidentialite />} />
          <Route path="/" element={<Racine onVisiteur={setVisiteur} />} />
          <Route path="/profil" element={<Protege><Profil /></Protege>} />
          <Route path="/dossier/:org" element={<Protege><Dossier /></Protege>}>
            <Route index element={<TableauDeBord />} />
            <Route path="personnel" element={<Personnel />} />
            <Route path="regime" element={<Regime />} />
            <Route path="simulation" element={<Simulation />} />
            <Route path="etudes" element={<Etudes />} />
            <Route path="etudes/:etude" element={<EtudeDetail />} />
            <Route path="etudes/:etude/financement" element={<Financement />} />
            <Route path="financement" element={<Financement />} />
            <Route path="cahier" element={<Cahier />} />
            <Route path="cahier/:fiche" element={<Reponses />} />
            <Route path="contrat" element={<Contrat />} />
            <Route path="placement" element={<Placement />} />
            <Route path="accompagnement" element={<Accompagnement />} />
            <Route path="departs" element={<Departs />} />
            <Route path="equipe" element={<Equipe />} />
            <Route path="messages" element={<Messages />} />
            <Route path="dossiers/:id" element={<DossierPriseEnCharge />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <PiedDePage />
    </Fragment>
  );
}

/** `/` : l'accueil des dossiers pour qui a une session, la vitrine pour qui n'en a pas. */
function Racine({ onVisiteur }: { onVisiteur: (v: boolean) => void }) {
  const { donnee, erreur } = useCharge(() => api.get("/moi"), []);
  const visiteur = erreur instanceof ErreurApi && erreur.statut === 401;
  useEffect(() => { onVisiteur(visiteur); return () => onVisiteur(false); }, [visiteur, onVisiteur]);
  if (visiteur) return <Vitrine />;
  if (erreur) return <div className="erreur">{erreur.message}</div>;
  return donnee ? <Accueil /> : <p className="discret">{t("Chargement…", "Loading…")}</p>;
}

/** Une page réservée : la session (ou, en développement, la personne choisie) doit être valable. */
function Protege({ children }: { children: React.ReactNode }) {
  const { donnee, erreur } = useCharge(() => api.get("/moi"), []);
  if (erreur instanceof ErreurApi && erreur.statut === 401) return <Navigate to="/connexion" replace />;
  if (erreur) return <div className="erreur">{erreur.message}</div>;
  return donnee ? <>{children}</> : <p className="discret">{t("Chargement…", "Loading…")}</p>;
}

const PUBLIQUES = ["/connexion", "/verifier", "/guide", "/inscription", "/essai", "/mentions-legales", "/conditions",
                   "/confidentialite"];

function Entete({ visiteur }: { visiteur: boolean }) {
  const { pathname } = useLocation();
  const connecte = !visiteur && !PUBLIQUES.some((p) => pathname.startsWith(p));
  return (
    <header className="entete">
      <div className="interieur">
        <Link to="/" className="marque">courtage<span>.</span></Link>
        <span className="discret" style={{ color: "#c9cfee" }}>{t("Votre régime IFC, calculé avant d'être vendu",
          "Your end-of-service plan, costed before it is sold")}</span>
        <div className="droite">
          <Link to="/guide" style={{ color: "#fff" }} data-visite="guide">{t("Guide", "Guide")}</Link>
          <Link to="/verifier" style={{ color: "#fff" }}>{t("Vérifier un document", "Verify a document")}</Link>
          <BasculeLangue />
          {visiteur && <Link to="/connexion" className="bouton-profil">{t("Se connecter", "Sign in")}</Link>}
          {connecte && (
            <Link to="/profil" className="bouton-profil" title={t("Mon profil", "My profile")}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8"
                   strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
              <span>{t("Mon profil", "My profile")}</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

/** FR | EN : la langue de l'interface, gardée dans ce navigateur. */
function BasculeLangue() {
  const l = useLangue();
  return (
    <div className="langues" role="group" aria-label={t("Langue", "Language")}>
      {(["fr", "en"] as const).map((x) => (
        <button key={x} type="button" lang={x} aria-pressed={l === x} onClick={() => changerLangue(x)}
                title={x === "fr" ? "Français" : "English"}>{x.toUpperCase()}</button>
      ))}
    </div>
  );
}
