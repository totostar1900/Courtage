import { useId, useState, type ReactNode } from "react";

import { t } from "../i18n";

/** Les indicatifs proposés : la CEMAC d'abord (le marché), puis les voisins et les pays d'où l'on appelle souvent.
 *  `tronc` : le 0 initial du numéro national tombe devant l'indicatif (France, Belgique, Royaume-Uni). La Côte
 *  d'Ivoire garde le sien : il fait partie de ses dix chiffres. */
export const INDICATIFS: { pays: string; code: string; drapeau: string; nom: () => string; exemple: string; tronc?: boolean }[] = [
  { pays: "CM", code: "237", drapeau: "🇨🇲", nom: () => t("Cameroun", "Cameroon"), exemple: "6 99 12 34 56" },
  { pays: "GA", code: "241", drapeau: "🇬🇦", nom: () => t("Gabon", "Gabon"), exemple: "06 12 34 56" },
  { pays: "CG", code: "242", drapeau: "🇨🇬", nom: () => t("Congo", "Congo"), exemple: "06 612 3456" },
  { pays: "TD", code: "235", drapeau: "🇹🇩", nom: () => t("Tchad", "Chad"), exemple: "63 01 23 45" },
  { pays: "CF", code: "236", drapeau: "🇨🇫", nom: () => t("Centrafrique", "Central African Rep."), exemple: "70 01 23 45" },
  { pays: "GQ", code: "240", drapeau: "🇬🇶", nom: () => t("Guinée équatoriale", "Equatorial Guinea"), exemple: "222 123 456" },
  { pays: "CI", code: "225", drapeau: "🇨🇮", nom: () => t("Côte d'Ivoire", "Côte d'Ivoire"), exemple: "07 01 23 45 67" },
  { pays: "SN", code: "221", drapeau: "🇸🇳", nom: () => t("Sénégal", "Senegal"), exemple: "77 123 45 67" },
  { pays: "NG", code: "234", drapeau: "🇳🇬", nom: () => t("Nigeria", "Nigeria"), exemple: "802 123 4567" },
  { pays: "FR", code: "33", drapeau: "🇫🇷", nom: () => t("France", "France"), exemple: "06 12 34 56 78", tronc: true },
  { pays: "BE", code: "32", drapeau: "🇧🇪", nom: () => t("Belgique", "Belgium"), exemple: "0470 12 34 56", tronc: true },
  { pays: "GB", code: "44", drapeau: "🇬🇧", nom: () => t("Royaume-Uni", "United Kingdom"), exemple: "07400 123456", tronc: true },
  { pays: "US", code: "1", drapeau: "🇺🇸", nom: () => t("États-Unis, Canada", "United States, Canada"), exemple: "201 555 0123" },
];

/** Le numéro complet (E.164) à partir de l'indicatif choisi et du numéro saisi. Un numéro saisi avec « + » ou « 00 »
 *  est déjà international : l'indicatif du menu ne s'y ajoute pas. Vide si rien n'est saisi. */
export function composer(pays: string, national: string): string {
  const brut = national.trim();
  if (!brut) return "";
  if (brut.startsWith("+") || brut.startsWith("00")) return "+" + brut.replace(/^00/, "").replace(/\D/g, "");
  const i = INDICATIFS.find((x) => x.pays === pays) ?? INDICATIFS[0];
  let chiffres = brut.replace(/\D/g, "");
  if (i.tronc) chiffres = chiffres.replace(/^0/, "");
  return `+${i.code}${chiffres}`;
}

/** L'inverse, pour afficher un numéro déjà connu : le pays de l'indicatif le plus long qui convient, et le reste. */
export function decomposer(valeur: string): { pays: string; national: string } {
  const v = valeur.replace(/[^\d+]/g, "");
  if (!v.startsWith("+")) return { pays: "CM", national: valeur };
  const i = [...INDICATIFS].sort((a, b) => b.code.length - a.code.length).find((x) => v.slice(1).startsWith(x.code));
  return i ? { pays: i.pays, national: v.slice(1 + i.code.length) } : { pays: "CM", national: valeur };
}

/** Un téléphone : l'indicatif à choisir, puis le numéro. Rend la forme E.164 que le serveur attend (« +237699123456 »).
 *  Contrôlé (`valeur` + `onChange`), ou dans un formulaire (`name` : un champ caché porte le numéro complet). */
export function ChampTelephone({ libelle, valeur, onChange, name, required, autoComplete = "tel", aide }: {
  libelle: ReactNode; valeur?: string; onChange?: (v: string) => void; name?: string; required?: boolean;
  autoComplete?: string; aide?: ReactNode;
}) {
  const id = useId();
  const [depart] = useState(() => decomposer(valeur ?? ""));
  const [pays, setPays] = useState(depart.pays);
  const [national, setNational] = useState(depart.national);
  const indicatif = INDICATIFS.find((x) => x.pays === pays) ?? INDICATIFS[0];
  const complet = composer(pays, national);
  const changer = (p: string, n: string) => { setPays(p); setNational(n); onChange?.(composer(p, n)); };

  return (
    <div className="champ-telephone">
      <label htmlFor={`${id}-numero`}>{libelle}</label>
      <div className="champ-telephone-ligne">
        <span className="champ-telephone-pays">
          <span className="champ-telephone-puce" aria-hidden="true">
            <span className="drapeau">{indicatif.drapeau}</span>+{indicatif.code}
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2"><path d="m6 9 6 6 6-6" /></svg>
          </span>
          <select aria-label={t("Indicatif du pays", "Country code")} value={pays} onChange={(e) => changer(e.target.value, national)}>
            {INDICATIFS.map((x) => <option key={x.pays} value={x.pays}>{x.drapeau} {x.nom()} (+{x.code})</option>)}
          </select>
        </span>
        <input id={`${id}-numero`} type="tel" inputMode="tel" autoComplete={autoComplete} required={required}
               value={national} placeholder={indicatif.exemple} onChange={(e) => changer(pays, e.target.value)} />
      </div>
      {name && <input type="hidden" name={name} value={complet} />}
      {aide && <div className="discret">{aide}</div>}
    </div>
  );
}
