import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { api, DEMO, ErreurApi, seConnecter } from "./api";
import { useCharge } from "./composants/communs";
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
import EtudeDetail from "./pages/EtudeDetail";
import Etudes from "./pages/Etudes";
import Financement from "./pages/Financement";
import Guide from "./pages/Guide";
import Personnel from "./pages/Personnel";
import Regime from "./pages/Regime";
import Reponses from "./pages/Reponses";
import Simulation from "./pages/Simulation";
import TableauDeBord from "./pages/TableauDeBord";
import Verifier from "./pages/Verifier";

export default function App() {
  return (
    <>
      <Entete />
      {DEMO && (
        <div className="bandeau-demo">
          Démonstration : la Société Démo SA et ses 40 salariés sont fictifs. Les chiffres viennent du vrai moteur ;
          les actions qui modifieraient le dossier sont désactivées.
        </div>
      )}
      <Visionneuse />
      <main className="page">
        <Routes>
          <Route path="/verifier/:numero" element={<Verifier />} />
          <Route path="/verifier" element={<Verifier />} />
          <Route path="/connexion" element={<Connexion />} />
          <Route path="/guide/*" element={<Guide />} />
          <Route path="/" element={<Protege><Accueil /></Protege>} />
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
            <Route path="accompagnement" element={<Accompagnement />} />
            <Route path="departs" element={<Departs />} />
            <Route path="equipe" element={<Equipe />} />
            <Route path="dossiers/:id" element={<DossierPriseEnCharge />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}

/** Une page réservée : la session (ou, en développement, la personne choisie) doit être valable. */
function Protege({ children }: { children: React.ReactNode }) {
  const { donnee, erreur } = useCharge(() => api.get("/moi"), []);
  if (erreur instanceof ErreurApi && erreur.statut === 401) return <Navigate to="/connexion" replace />;
  if (erreur) return <div className="erreur">{erreur.message}</div>;
  return donnee ? <>{children}</> : <p className="discret">Chargement…</p>;
}

function Entete() {
  const naviguer = useNavigate();
  const { pathname } = useLocation();
  const connecte = !pathname.startsWith("/connexion") && !pathname.startsWith("/verifier") && !pathname.startsWith("/guide");
  return (
    <header className="entete">
      <div className="interieur">
        <Link to="/" className="marque">courtage<span>.</span></Link>
        <span className="discret" style={{ color: "#c9cfee" }}>Votre régime IFC, calculé avant d'être vendu</span>
        <div className="droite">
          <Link to="/guide" style={{ color: "#fff" }} data-visite="guide">Guide</Link>
          <Link to="/verifier" style={{ color: "#fff" }}>Vérifier un document</Link>
          {connecte && (
            <button onClick={async () => {
              await api.post("/auth/deconnexion").catch(() => undefined);
              seConnecter(null);
              naviguer("/connexion");
            }}>Se déconnecter</button>
          )}
        </div>
      </div>
    </header>
  );
}
