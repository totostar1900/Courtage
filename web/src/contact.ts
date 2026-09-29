/** Les liens qui ouvrent un échange hors de la plateforme : WhatsApp, courriel, appel. Rien n'est envoyé d'ici ;
 *  un numéro ou une adresse absents (entre crochets dans la configuration) ne donnent pas de lien. */

const chiffres = (telephone: string | null | undefined) => (telephone ?? "").replace(/[^\d+]/g, "");

/** Un numéro utilisable : « +237 6 99… » ; pas « [téléphone] ». */
export function numeroValide(telephone: string | null | undefined): boolean {
  return /^\+\d{8,15}$/.test(chiffres(telephone));
}

export function lienWhatsApp(telephone: string | null | undefined, texte?: string): string | null {
  if (!numeroValide(telephone)) return null;
  const n = chiffres(telephone).slice(1);
  return `https://wa.me/${n}${texte ? `?text=${encodeURIComponent(texte)}` : ""}`;
}

export function lienAppel(telephone: string | null | undefined): string | null {
  return numeroValide(telephone) ? `tel:${chiffres(telephone)}` : null;
}

export function lienCourriel(adresse: string | null | undefined, sujet?: string): string | null {
  if (!adresse || !/^[^\s@[\]]+@[^\s@[\]]+\.[^\s@[\]]+$/.test(adresse)) return null;
  return `mailto:${adresse}${sujet ? `?subject=${encodeURIComponent(sujet)}` : ""}`;
}
