import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { seConnecter, utilisateurCourant } from "./api";
import Accueil from "./pages/Accueil";
import Cahier from "./pages/Cahier";
import Connexion from "./pages/Connexion";
import Dossier from "./pages/Dossier";
import EtudeDetail from "./pages/EtudeDetail";
import Etudes from "./pages/Etudes";
import Financement from "./pages/Financement";
import Personnel from "./pages/Personnel";
import Regime from "./pages/Regime";
import Remuneration from "./pages/Remuneration";
import Simulation from "./pages/Simulation";
import TableauDeBord from "./pages/TableauDeBord";
import Verifier from "./pages/Verifier";

export default function App() {
  return (
    <>
      <Entete />
      <main className="page">
        <Routes>
          <Route path="/verifier/:numero" element={<Verifier />} />
          <Route path="/verifier" element={<Verifier />} />
          <Route path="/connexion" element={<Connexion />} />
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
            <Route path="remuneration" element={<Remuneration />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}

function Protege({ children }: { children: React.ReactNode }) {
  return utilisateurCourant() ? <>{children}</> : <Navigate to="/connexion" replace />;
}

function Entete() {
  const naviguer = useNavigate();
  const connecte = !!utilisateurCourant();
  return (
    <header className="entete">
      <div className="interieur">
        <Link to="/" className="marque">courtage<span>.</span></Link>
        <span className="discret" style={{ color: "#c9cfee" }}>Votre régime IFC, calculé avant d'être vendu</span>
        <div className="droite">
          <Link to="/verifier" style={{ color: "#fff" }}>Vérifier un document</Link>
          {connecte && (
            <button onClick={() => { seConnecter(null); naviguer("/connexion"); }}>Changer de personne</button>
          )}
        </div>
      </div>
    </header>
  );
}
