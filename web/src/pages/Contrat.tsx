import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { Constats, Erreur, useCharge, Volet } from "../composants/communs";
import { Terme } from "../composants/Terme";
import { dateFr } from "../format";
import type { ContratsDossier } from "../types";
import { useDossier } from "./Dossier";

const SERVICES = {
  courtage: {
    titre: "Courtage",
    phrase: "Nous sommes votre courtier : mandatés par vous, entre vous et l'assureur.",
    depart: [
      "Vous nous déclarez le départ ; nous montons le dossier de prise en charge et le transmettons à l'assureur.",
      "Nous suivons le paiement et vous alertons si l'assureur dépasse le délai prévu.",
      "Pour ce dossier seulement, nous recueillons l'identité du bénéficiaire ; elle n'entre dans aucun rapport.",
    ],
  },
  comparaison: {
    titre: "Comparaison",
    phrase: "Nous avons éclairé votre choix ; vous avez contracté directement avec l'assureur.",
    depart: [
      "Vous vous adressez directement à votre assureur pour la prise en charge.",
      "Nous vous indiquons à qui, avec quelles pièces, et le montant dû que nous avons calculé.",
      "Nous ne vous demandons jamais l'identité d'un salarié. Vous pouvez nous déclarer ce que l'assureur a payé, sans nom, pour vos rapports.",
    ],
  },
} as const;

/** Le service que nous vous rendons, et ce qu'il change le jour où un salarié part. */
export default function Contrat() {
  const d = useDossier();
  const { donnee, erreur, recharger } = useCharge(() => api.get<ContratsDossier>(`/organisations/${d.org.id}/contrats`), []);
  const [ouvert, setOuvert] = useState(false);
  if (erreur) return <Erreur erreur={erreur} />;
  if (!donnee) return <p className="discret">Chargement…</p>;
  const s = SERVICES[donnee.service];
  const c = donnee.en_vigueur;

  return (
    <>
      <h1>Votre contrat</h1>
      <p>Deux services existent : le <Terme cle="courtage">courtage</Terme> et la <Terme cle="comparaison">comparaison</Terme>.
        Le vôtre décide qui s'occupe d'une prestation quand un salarié part en retraite.</p>

      <div className="carte section" data-service={donnee.service}>
        <div className="actions" style={{ marginTop: 0, justifyContent: "space-between" }}>
          <h2 style={{ margin: 0 }}>{s.titre}</h2>
          <span className={`etat ${donnee.service === "courtage" ? "bien" : "neutre"}`}>
            {c ? `depuis le ${dateFr(c.en_vigueur_du)}` : "par défaut : aucun contrat enregistré"}</span>
        </div>
        <p style={{ marginTop: 8 }}>{s.phrase}</p>
        {c && (
          <div className="lignes-offre">
            {c.assureur && <div><span>Assureur</span><strong>{c.assureur}</strong></div>}
            {c.numero_police && <div><span>Police</span><span>{c.numero_police}{c.date_effet_police && ` · effet le ${dateFr(c.date_effet_police)}`}</span></div>}
            {c.mandat_reference && <div><span>Mandat</span><span>{c.mandat_reference}</span></div>}
            {c.note && <div><span>Note</span><span>{c.note}</span></div>}
          </div>
        )}
        <h3 className="section">Quand un salarié part</h3>
        <ul>{s.depart.map((t) => <li key={t}>{t}</li>)}</ul>
        <Link to="/guide/contrat">Courtage ou comparaison : le guide</Link>
      </div>

      {donnee.constats.length > 0 && <div className="section"><Constats constats={donnee.constats} /></div>}

      {donnee.historique.length > 1 && (
        <div className="section">
          <h2>Historique</h2>
          <table>
            <thead><tr><th>Depuis le</th><th>Service</th><th>Assureur</th><th>Police</th></tr></thead>
            <tbody>{donnee.historique.map((h) => (
              <tr key={h.id}><td>{dateFr(h.en_vigueur_du)}</td><td>{SERVICES[h.service].titre}</td>
                <td>{h.assureur ?? "—"}</td><td>{h.numero_police ?? "—"}</td></tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {d.role === "conseiller" && (
        <div className="section">
          {ouvert
            ? <NouveauContrat onFermer={() => setOuvert(false)} onFait={() => { setOuvert(false); recharger(); }} />
            : <button className="principal" onClick={() => setOuvert(true)}>Enregistrer un contrat</button>}
        </div>
      )}
    </>
  );
}

function NouveauContrat({ onFermer, onFait }: { onFermer: () => void; onFait: () => void }) {
  const d = useDossier();
  const [service, setService] = useState<"courtage" | "comparaison">("courtage");
  const [erreur, setErreur] = useState<unknown>(null);
  async function enregistrer(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const texte = (k: string) => (String(f.get(k) ?? "").trim() || null);
    setErreur(null);
    try {
      await api.post(`/organisations/${d.org.id}/contrats`, {
        en_vigueur_du: f.get("en_vigueur_du"), service, assureur: texte("assureur"), numero_police: texte("numero_police"),
        date_effet_police: texte("date_effet_police"), mandat_reference: service === "courtage" ? texte("mandat_reference") : null,
        note: texte("note") });
      onFait();
    } catch (e) { setErreur(e); }
  }
  return (
    <Volet titre="Enregistrer un contrat" onFermer={onFermer}>
      <form className="formulaire" onSubmit={enregistrer}>
        <p className="discret">Un contrat ne se modifie pas : un nouveau prend effet à sa date, l'ancien reste dans l'historique.</p>
        <div className="grille g3">
          <label>Service
            <select value={service} onChange={(e) => setService(e.target.value as "courtage" | "comparaison")}>
              <option value="courtage">Courtage (mandat)</option>
              <option value="comparaison">Comparaison</option>
            </select>
          </label>
          <label>À partir du<input name="en_vigueur_du" type="date" required /></label>
          <label>Assureur<input name="assureur" required={service === "courtage"} /></label>
          <label>Numéro de police<input name="numero_police" /></label>
          <label>Effet de la police<input name="date_effet_police" type="date" /></label>
          {service === "courtage" && <label>Référence du mandat<input name="mandat_reference" required placeholder="Mandat du 15/12/2025" /></label>}
        </div>
        <label>Note<input name="note" /></label>
        <div className="actions"><button className="principal">Enregistrer</button></div>
        <Erreur erreur={erreur} />
      </form>
    </Volet>
  );
}
