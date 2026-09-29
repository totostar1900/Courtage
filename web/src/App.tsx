import { Fragment, useEffect, useState, type ReactNode } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { api, DEMO, ErreurApi } from "./api";
import { useCharge } from "./composants/communs";
import { changerLangue, t, useLangue } from "./i18n";
import Marque from "./composants/Marque";
import PiedDePage from "./composants/PiedDePage";
import Titre from "./composants/Titre";
import Visionneuse from "./composants/Visionneuse";
import { choisirTheme, lireTheme, type Theme } from "./theme";
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
import { PageIfc, PageIfcCameroun } from "./pages/Contenu";
import { Conditions, Confidentialite, MentionsLegales } from "./pages/Legal";
import Messages from "./pages/Messages";
import Offre from "./pages/Offre";
import EtudeDetail from "./pages/EtudeDetail";
import Etudes from "./pages/Etudes";
import OffresDossier from "./pages/OffresDossier";
import Guide from "./pages/Guide";
import Personnel from "./pages/Personnel";
import Portefeuille from "./pages/Portefeuille";
import Placement from "./pages/Placement";
import Profil from "./pages/Profil";
import Regime from "./pages/Regime";
import Reponses from "./pages/Reponses";
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
          <Route path="/verifier/:numero" element={<><Titre valeur={t("Vérifier un document", "Verify a document")} /><Verifier /></>} />
          <Route path="/verifier" element={<><Titre valeur={t("Vérifier un document", "Verify a document")} /><Verifier /></>} />
          <Route path="/connexion" element={<><Titre valeur={t("Se connecter", "Sign in")} /><Connexion /></>} />
          <Route path="/inscription" element={<><Titre valeur={t("Créer votre compte", "Create your account")} /><Inscription /></>} />
          <Route path="/essai" element={<><Titre valeur={t("Essayer sans compte", "Try without an account")} /><Essai /></>} />
          <Route path="/offre/:jeton" element={<><Titre valeur={t("Consultation d'assureurs", "Insurer consultation")} /><Offre /></>} />
          <Route path="/guide/*" element={<><Titre valeur={t("Le guide", "The guide")} /><Guide /></>} />
          <Route path="/ifc" element={<><Titre valeur={t("Les indemnités de fin de carrière", "End-of-service benefits")} /><PageIfc /></>} />
          <Route path="/ifc/cameroun" element={<><Titre valeur={t("Les IFC au Cameroun", "End-of-service benefits in Cameroon")} /><PageIfcCameroun /></>} />
          <Route path="/mentions-legales" element={<><Titre valeur={t("Mentions légales", "Legal notice")} /><MentionsLegales /></>} />
          <Route path="/conditions" element={<><Titre valeur={t("Conditions d'utilisation", "Terms of use")} /><Conditions /></>} />
          <Route path="/confidentialite" element={<><Titre valeur={t("Confidentialité", "Privacy")} /><Confidentialite /></>} />
          <Route path="/" element={<Racine onVisiteur={setVisiteur} />} />
          <Route path="/profil" element={<Protege><Profil /></Protege>} />
          <Route path="/portefeuille" element={<Protege><Portefeuille /></Protege>} />
          <Route path="/dossier/:org" element={<Protege><Dossier /></Protege>}>
            <Route index element={<TableauDeBord />} />
            <Route path="personnel" element={<Personnel />} />
            <Route path="regime" element={<Regime />} />
            <Route path="simulation" element={<VersEtudes />} />
            <Route path="etudes" element={<Etudes />} />
            <Route path="etudes/:etude" element={<EtudeDetail />} />
            <Route path="etudes/:etude/financement" element={<VersOffres />} />
            <Route path="financement" element={<OffresDossier />} />
            <Route path="cahier" element={<Cahier />} />
            <Route path="cahier/:fiche" element={<Reponses />} />
            <Route path="contrat" element={<Contrat />} />
            <Route path="placement" element={<Placement />} />
            <Route path="accompagnement" element={<Accompagnement />} />
            <Route path="departs" element={<Departs />} />
            <Route path="equipe" element={<Equipe />} />
            <Route path="contact" element={<Messages />} />
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
  if (visiteur) return <><Titre /><Vitrine /></>;
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
                   "/confidentialite", "/offre", "/ifc"];

function Entete({ visiteur }: { visiteur: boolean }) {
  const { pathname } = useLocation();
  const connecte = !visiteur && !PUBLIQUES.some((p) => pathname.startsWith(p));
  return (
    <header className="entete">
      <div className="interieur">
        <Link to="/" className="marque" aria-label={t("Nitch, accueil", "Nitch, home")}><Marque /></Link>
        <span className="discret">{t("Votre régime IFC, calculé avant d'être vendu",
          "Your end-of-service plan, costed before it is sold")}</span>
        <div className="droite">
          <Link to="/guide" data-visite="guide">{t("Guide", "Guide")}</Link>
          <Link to="/verifier">{t("Vérifier un document", "Verify a document")}</Link>
          <BasculeTheme />
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
/** Automatique (celui de l'appareil), clair, sombre : trois icônes, à côté de FR · EN. */
function BasculeTheme() {
  const [theme, setTheme] = useState<Theme>(lireTheme);
  const choix: [Theme, string, ReactNode][] = [
    ["auto", t("Thème de l'appareil", "Device theme"), <><circle cx="12" cy="12" r="8" /><path d="M12 4v16" /><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor" /></>],
    ["clair", t("Thème clair", "Light theme"), <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>],
    ["sombre", t("Thème sombre", "Dark theme"), <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />],
  ];
  return (
    <div className="theme" role="group" aria-label={t("Thème", "Theme")}>
      {choix.map(([x, libelle, dessin]) => (
        <button key={x} type="button" aria-pressed={theme === x} aria-label={libelle} title={libelle}
                onClick={() => { choisirTheme(x); setTheme(x); }}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8"
               strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{dessin}</svg>
        </button>
      ))}
    </div>
  );
}

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

/** « Simuler » a rejoint la page Étude : l'ancienne adresse y mène, versions cochées comprises. */
function VersEtudes() {
  const { search } = useLocation();
  return <Navigate to={{ pathname: "../etudes", search }} replace />;
}

/** L'ancienne comparaison libre depuis une étude : les offres, désormais, viennent du conseiller. */
function VersOffres() {
  return <Navigate to="../financement" replace />;
}
