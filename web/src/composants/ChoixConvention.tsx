import { useEffect, useId, useState } from "react";

import { api } from "../api";
import { t } from "../i18n";

export interface ConventionConnue { code: string; pays: string; libelle: string; en_vigueur_aujourd_hui: boolean }

function lireConventions(): Promise<ConventionConnue[]> {
  return api.get<{ conventions: ConventionConnue[] }>("/referentiel/conventions").then((r) => r.conventions).catch(() => []);
}

/** Une convention par code, pour le pays : le libellé de la version en vigueur (à défaut, la dernière lue). */
export function conventionsDuPays(liste: ConventionConnue[], pays: string): ConventionConnue[] {
  const parCode = new Map<string, ConventionConnue>();
  for (const c of liste.filter((x) => x.pays === pays)) {
    const deja = parCode.get(c.code);
    if (!deja || (c.en_vigueur_aujourd_hui && !deja.en_vigueur_aujourd_hui)) parCode.set(c.code, c);
  }
  return [...parCode.values()].sort((a, b) => a.libelle.localeCompare(b.libelle, "fr"));
}

export function useConventions(pays: string): ConventionConnue[] | null {
  const [toutes, setToutes] = useState<ConventionConnue[] | null>(null);
  useEffect(() => {
    let actif = true;
    void lireConventions().then((c) => { if (actif) setToutes(c); });
    return () => { actif = false; };
  }, []);
  return toutes && conventionsDuPays(toutes, pays);
}

/** La convention collective : choisie parmi celles que la plateforme connaît pour le pays, jamais tapée. Une seule
 *  possible : elle se lit, sans champ. Un code déjà enregistré que le référentiel ne connaît plus reste affiché tel
 *  quel, pour ne rien changer en silence. `facultatif` : une première option vide, avec ce qu'elle veut dire.
 *
 *  Contrôlé (`valeur` + `onChange`), ou dans un formulaire (`name` + `defaut`). */
export function ChoixConvention({ pays, libelle, valeur, onChange, name, defaut, facultatif }: {
  pays: string; libelle: string; valeur?: string; onChange?: (code: string) => void; name?: string; defaut?: string;
  facultatif?: string;
}) {
  const id = useId();
  const conventions = useConventions(pays);
  const [interne, setInterne] = useState(defaut ?? "");
  const courant = valeur ?? interne;
  const choisir = (code: string) => { if (valeur === undefined) setInterne(code); onChange?.(code); };
  const liste = conventions ?? [];
  const options = courant && !liste.some((c) => c.code === courant)
    ? [...liste, { code: courant, libelle: courant, pays, en_vigueur_aujourd_hui: false }] : liste;

  // Rien de choisi alors qu'il le faut : la première convention du pays.
  const premiere = liste[0]?.code;
  useEffect(() => {
    if (!facultatif && !courant && premiere) choisir(premiere);
  }, [facultatif, courant, premiere]);     // eslint-disable-line react-hooks/exhaustive-deps

  if (!facultatif && options.length <= 1) {
    const seule = options[0];
    return (
      <div className="champ-lu">
        <span className="champ-lu-libelle" id={`${id}-libelle`}>{libelle}</span>
        <span data-convention aria-labelledby={`${id}-libelle`}>{seule?.libelle ?? (conventions ? "—" : t("Chargement…", "Loading…"))}</span>
        {name && <input type="hidden" name={name} value={seule?.code ?? ""} />}
      </div>
    );
  }
  return (
    <label>{libelle}
      <select name={name} value={courant} onChange={(e) => choisir(e.target.value)}>
        {facultatif && <option value="">{facultatif}</option>}
        {options.map((c) => <option key={c.code} value={c.code}>{c.libelle}</option>)}
      </select>
    </label>
  );
}
