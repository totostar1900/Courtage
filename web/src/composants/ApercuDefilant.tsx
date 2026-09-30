import { useEffect, useState, type ReactNode } from "react";

import { t } from "../i18n";

/** Le visuel du bandeau d'accueil : quatre aperçus du service qui se relaient — l'engagement chiffré, les offres
 *  classées, les départs à venir, un dossier de départ suivi. Des chiffres d'exemple, dits comme tels.
 *
 *  Il avance seul toutes les `PAUSE` ms, s'arrête sous la souris ou le focus, et reste immobile quand l'appareil
 *  demande moins de mouvement ; les points le mènent à la main. */
const PAUSE = 5500;

function Panneau({ titre, etat, children }: { titre: string; etat?: ReactNode; children: ReactNode }) {
  return (
    <>
      <div className="apercu-tete"><span>{titre}</span>{etat ?? <span className="apercu-exemple">{t("Exemple", "Example")}</span>}</div>
      {children}
    </>
  );
}

function panneaux(): { nom: string; corps: ReactNode }[] {
  const offres: [string, number, boolean][] = [["A", 4.85, true], ["B", 4.4, false], ["C", 3.95, false]];
  const departs: [string, number][] = [["2027", 8.4], ["2028", 12.1], ["2029", 5.2], ["2030", 18.6], ["2031", 9.9]];
  const etapes: [string, boolean][] = [
    [t("Départ déclaré", "Departure declared"), true], [t("Montant recalculé", "Amount recalculated"), true],
    [t("Transmis à l'assureur", "Sent to the insurer"), true], [t("Payé", "Paid"), false]];
  return [
    { nom: t("L'engagement", "The liability"), corps: (
      <Panneau titre={t("Votre engagement au 31/12", "Your liability at 31/12")}
               etat={<span className="etat bien">{t("Scellé", "Sealed")}</span>}>
        <div className="apercu-chiffre">135,8 M F</div>
        <div className="apercu-barres">{[38, 12, 30, 6, 64, 8, 22, 46, 18, 14].map((h, i) => <span key={i} style={{ height: `${h}px` }} />)}</div>
        <div className="apercu-ligne"><span>{t("Offres reçues", "Offers received")}</span><strong>3</strong></div>
        <div className="apercu-ligne"><span>{t("Meilleur rendement net", "Best net return")}</span><strong>4,85 %</strong></div>
      </Panneau>) },
    { nom: t("Les offres", "The offers"), corps: (
      <Panneau titre={t("Offres classées", "Offers ranked")}>
        <p className="apercu-sous">{t("Rendement net : taux servi − frais − chargements", "Net return: rate paid − fees − charges")}</p>
        <ol className="apercu-offres">
          {offres.map(([nom, taux, tete]) => (
            <li key={nom} className={tete ? "tete" : undefined}>
              <span>{t(`Assureur ${nom}`, `Insurer ${nom}`)}</span>
              <span className="apercu-jauge"><span style={{ width: `${(taux / 5.5) * 100}%` }} /></span>
              <strong>{taux.toFixed(2).replace(".", ",")} %</strong>
            </li>
          ))}
        </ol>
        <div className="apercu-ligne"><span>{t("Recommandée", "Recommended")}</span><strong>{t("Assureur A", "Insurer A")}</strong></div>
      </Panneau>) },
    { nom: t("Les départs", "The departures"), corps: (
      <Panneau titre={t("Départs à venir", "Upcoming departures")}>
        <div className="apercu-annees">
          {departs.map(([an, m]) => (
            <div key={an}><span className="apercu-valeur">{m.toFixed(1).replace(".", ",")}</span>
              <span className="apercu-colonne" style={{ height: `${(m / 18.6) * 84}px` }} /><span className="apercu-an">{an}</span></div>
          ))}
        </div>
        <div className="apercu-ligne"><span>{t("Sur cinq ans", "Over five years")}</span><strong>54,2 M F</strong></div>
        <div className="apercu-ligne"><span>{t("Prochain départ", "Next departure")}</span><strong>{t("mars 2027", "March 2027")}</strong></div>
      </Panneau>) },
    { nom: t("Le dossier", "The claim file"), corps: (
      <Panneau titre={t("Dossier de départ · 0142", "Departure file · 0142")}>
        <div className="apercu-chiffre">7,25 M F</div>
        <ol className="apercu-etapes">
          {etapes.map(([nom, fait]) => <li key={nom} className={fait ? "fait" : "attente"}><span aria-hidden="true" />{nom}</li>)}
        </ol>
        <div className="apercu-ligne"><span>{t("Délai de l'assureur", "Insurer's deadline")}</span><strong>{t("J+12 sur 30", "Day 12 of 30")}</strong></div>
      </Panneau>) },
  ];
}

function moinsDeMouvement(): boolean {
  try { return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false; } catch { return false; }
}

export default function ApercuDefilant() {
  const [i, setI] = useState(0);
  const [arret, setArret] = useState(false);
  const liste = panneaux();
  useEffect(() => {
    if (arret || moinsDeMouvement()) return;
    const minuterie = window.setInterval(() => setI((x) => (x + 1) % liste.length), PAUSE);
    return () => window.clearInterval(minuterie);
  }, [arret, liste.length]);
  return (
    <div className="apercu-defilant" role="group" aria-roledescription={t("carrousel", "carousel")}
         aria-label={t("Aperçu du service, en exemple", "A preview of the service, by example")}
         onMouseEnter={() => setArret(true)} onMouseLeave={() => setArret(false)}
         onFocus={() => setArret(true)} onBlur={() => setArret(false)}>
      <div className="apercu-pile">
        {liste.map((p, n) => (
          <div key={p.nom} className={`apercu-carte${n === i ? " visible" : ""}`} aria-hidden={n !== i}>{p.corps}</div>
        ))}
      </div>
      <div className="apercu-points">
        {liste.map((p, n) => (
          <button key={p.nom} type="button" aria-label={t(`Voir : ${p.nom}`, `Show: ${p.nom}`)} aria-pressed={n === i}
                  title={p.nom} onClick={() => setI(n)}><span /></button>
        ))}
      </div>
    </div>
  );
}
