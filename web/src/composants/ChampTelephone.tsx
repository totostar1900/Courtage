import { useId, useMemo, useState, type KeyboardEvent, type ReactNode } from "react";
import { getCountries, getCountryCallingCode, getExampleNumber, parsePhoneNumberFromString,
         type CountryCode } from "libphonenumber-js/min";
import exemples from "libphonenumber-js/examples.mobile.json";
import metadonnees from "libphonenumber-js/metadata.min.json";

import { langue, t } from "../i18n";

/** Les pays proposés d'abord : la CEMAC (le marché), puis les voisins et les pays d'où l'on appelle souvent. Tous les
 *  autres suivent, par ordre alphabétique : la bibliothèque des numéros (libphonenumber) en connaît 245. */
const EN_TETE: CountryCode[] = ["CM", "GA", "CG", "TD", "CF", "GQ", "CI", "SN", "NG", "FR", "BE", "GB", "US"];

export interface Pays { iso: CountryCode; code: string; nom: string; drapeau: string }

/** Le drapeau d'un pays, en émoji : deux lettres « régionales ». */
const drapeau = (iso: string) => String.fromCodePoint(...[...iso].map((c) => 0x1f1a5 + c.charCodeAt(0)));

const sansAccents = (x: string) => x.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Tous les pays, nommés dans la langue de l'écran. */
export function listePays(): Pays[] {
  let noms: Intl.DisplayNames | null = null;
  try { noms = new Intl.DisplayNames([langue()], { type: "region" }); } catch { /* navigateur ancien : les codes */ }
  const tous = getCountries().map((iso) => ({ iso, code: getCountryCallingCode(iso), nom: noms?.of(iso) ?? iso, drapeau: drapeau(iso) }));
  const tete = EN_TETE.map((iso) => tous.find((p) => p.iso === iso)).filter((p): p is Pays => Boolean(p));
  const reste = tous.filter((p) => !EN_TETE.includes(p.iso)).sort((a, b) => a.nom.localeCompare(b.nom, langue()));
  return [...tete, ...reste];
}

/** Le pays d'un indicatif : celui qu'on a déjà s'il le partage (le Canada garde le +1), sinon le pays principal. */
function paysDeLIndicatif(code: string, courant: CountryCode): CountryCode | null {
  const pays = (metadonnees.country_calling_codes as Record<string, string[]>)[code] as CountryCode[] | undefined;
  if (!pays?.length) return null;
  return pays.includes(courant) ? courant : pays[0];
}

/** Ce qu'on a tapé dans l'indicatif : « +33 », « 33 », « 0033 », « France », « fr ». */
export function resoudre(saisie: string, courant: CountryCode, liste: Pays[]): CountryCode | null {
  const brut = saisie.trim();
  if (!brut) return null;
  if (/^[+\d\s()-]+$/.test(brut)) return paysDeLIndicatif(brut.replace(/\D/g, "").replace(/^00/, ""), courant);
  const cherche = sansAccents(brut);
  if (cherche.length === 2) {
    const iso = liste.find((p) => p.iso.toLowerCase() === cherche);
    if (iso) return iso.iso;
  }
  return (liste.find((p) => sansAccents(p.nom) === cherche) ?? liste.find((p) => sansAccents(p.nom).startsWith(cherche)))?.iso ?? null;
}

/** Les pays qui répondent à une saisie : par nom (début d'un mot), par code du pays, par indicatif. */
function filtrer(saisie: string, liste: Pays[]): Pays[] {
  const brut = saisie.trim();
  if (!brut) return liste;
  if (/^[+\d\s]+$/.test(brut)) {
    const chiffres = brut.replace(/\D/g, "").replace(/^00/, "");
    return liste.filter((p) => p.code.startsWith(chiffres));
  }
  const cherche = sansAccents(brut);
  return liste.filter((p) => p.iso.toLowerCase() === cherche
    || sansAccents(p.nom).split(/[\s'’-]+/).some((mot) => mot.startsWith(cherche)));
}

/** Le numéro complet (E.164) à partir du pays choisi et du numéro saisi. Un numéro saisi avec « + » ou « 00 » est
 *  déjà international : l'indicatif choisi ne s'y ajoute pas. Le préfixe national (le 0 français) tombe là où le
 *  plan de numérotation le veut, et reste là où il fait partie du numéro (Côte d'Ivoire). Vide si rien n'est saisi. */
export function composer(pays: string, national: string): string {
  const brut = national.trim();
  if (!brut) return "";
  const international = brut.startsWith("+") || brut.startsWith("00");
  const texte = international ? "+" + brut.replace(/^\+|^00/, "").replace(/\D/g, "") : brut;
  const lu = parsePhoneNumberFromString(texte, international ? undefined : (pays as CountryCode));
  if (lu) return lu.number;
  const chiffres = brut.replace(/\D/g, "");
  if (international) return "+" + chiffres.replace(/^00/, "");
  const code = getCountries().includes(pays as CountryCode) ? getCountryCallingCode(pays as CountryCode) : "237";
  return `+${code}${chiffres}`;
}

/** L'inverse, pour afficher un numéro déjà connu : son pays et le reste. Sans « + », le Cameroun, et tel quel. */
export function decomposer(valeur: string): { pays: string; national: string } {
  const v = valeur.replace(/[^\d+]/g, "");
  if (!v.startsWith("+")) return { pays: "CM", national: valeur };
  const lu = parsePhoneNumberFromString(v);
  if (lu?.country) return { pays: lu.country, national: lu.nationalNumber };
  if (lu) {
    const pays = paysDeLIndicatif(lu.countryCallingCode, "CM");
    if (pays) return { pays, national: lu.nationalNumber };
  }
  return { pays: "CM", national: valeur };
}

/** Un numéro d'exemple pour le pays, en format national : « 6 71 23 45 67 ». */
function exemple(pays: string): string {
  try { return getExampleNumber(pays as CountryCode, exemples)?.formatNational() ?? ""; } catch { return ""; }
}

/** Un téléphone : l'indicatif, puis le numéro. L'indicatif se tape (« +33 », « 33 », « France », « fr ») ou se choisit
 *  dans la liste de tous les pays, filtrée à mesure. Rend la forme E.164 que le serveur attend (« +237699123456 »).
 *  Contrôlé (`valeur` + `onChange`), ou dans un formulaire (`name` : un champ caché porte le numéro complet). */
export function ChampTelephone({ libelle, valeur, onChange, name, required, autoComplete = "tel", aide }: {
  libelle: ReactNode; valeur?: string; onChange?: (v: string) => void; name?: string; required?: boolean;
  autoComplete?: string; aide?: ReactNode;
}) {
  const id = useId();
  const liste = useMemo(() => listePays(), []);
  const [depart] = useState(() => decomposer(valeur ?? ""));
  const [pays, setPays] = useState<CountryCode>(depart.pays as CountryCode);
  const [national, setNational] = useState(depart.national);
  const [saisie, setSaisie] = useState<string | null>(null);     // null : l'indicatif du pays choisi s'affiche
  const [actif, setActif] = useState(0);
  const courant = liste.find((p) => p.iso === pays) ?? liste[0];
  const ouvert = saisie !== null;
  const proposes = ouvert ? filtrer(saisie, liste) : [];
  const complet = composer(pays, national);

  const changer = (p: CountryCode, n: string) => { setPays(p); setNational(n); onChange?.(composer(p, n)); };
  function choisir(p: CountryCode) { changer(p, national); setSaisie(null); }
  /** Enter ou la sortie du champ : l'indicatif ou le pays tapé, sinon le pays en surbrillance, sinon rien ne change. */
  function valider() {
    if (saisie === null) return;
    const trouve = (saisie.trim() ? resoudre(saisie, pays, liste) : null) ?? (saisie.trim() ? proposes[actif]?.iso : null);
    if (trouve) choisir(trouve); else setSaisie(null);
  }
  function touche(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!ouvert) { setSaisie(""); setActif(0); return; }
      const n = proposes.length;
      if (n) setActif((a) => (a + (e.key === "ArrowDown" ? 1 : n - 1)) % n);
    } else if (e.key === "Enter" && ouvert) {
      e.preventDefault();
      const surligne = proposes[actif];
      if (surligne && !/^[+\d\s]+$/.test(saisie ?? "")) choisir(surligne.iso); else valider();
    } else if (e.key === "Escape" && ouvert) {
      e.preventDefault();
      setSaisie(null);
    }
  }

  return (
    <div className="champ-telephone">
      <label htmlFor={`${id}-numero`}>{libelle}</label>
      <div className="champ-telephone-ligne">
        <span className="champ-telephone-pays">
          <span className="drapeau" aria-hidden="true">{courant.drapeau}</span>
          <input id={`${id}-indicatif`} className="champ-telephone-indicatif" type="text" autoComplete="off" spellCheck={false}
                 role="combobox" aria-label={t("Indicatif du pays", "Country code")} aria-expanded={ouvert}
                 aria-controls={`${id}-pays`} aria-autocomplete="list"
                 aria-activedescendant={ouvert && proposes[actif] ? `${id}-p-${proposes[actif].iso}` : undefined}
                 title={courant.nom} value={saisie ?? `+${courant.code}`}
                 onFocus={(e) => { e.currentTarget.select(); setSaisie(""); setActif(0); }}
                 onChange={(e) => { setSaisie(e.target.value); setActif(0); }}
                 onKeyDown={touche} onBlur={valider} />
        </span>
        <input id={`${id}-numero`} type="tel" inputMode="tel" autoComplete={autoComplete} required={required}
               value={national} placeholder={exemple(pays)} onChange={(e) => changer(pays, e.target.value)} />
      </div>
      {ouvert && (
        <ul id={`${id}-pays`} className="champ-telephone-liste" role="listbox" aria-label={t("Pays", "Countries")}>
          {proposes.length === 0 && <li className="discret" role="presentation">{t("Aucun pays ne correspond.", "No country matches.")}</li>}
          {proposes.map((p, i) => (
            <li key={p.iso} id={`${id}-p-${p.iso}`} role="option" aria-selected={i === actif}
                onMouseDown={(e) => { e.preventDefault(); choisir(p.iso); }} onMouseEnter={() => setActif(i)}>
              <span aria-hidden="true">{p.drapeau}</span><span>{p.nom}</span><span className="champ-telephone-code">+{p.code}</span>
            </li>
          ))}
        </ul>
      )}
      {name && <input type="hidden" name={name} value={complet} />}
      {aide && <div className="discret">{aide}</div>}
    </div>
  );
}
