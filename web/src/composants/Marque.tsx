/** Le logotype Nitch : « nitch » en Geist Sans 600, serré ; le point du i est un carré à l'accent (docs/design/marque-nitch.md).
 *  Des contours, pas du texte : il ne dépend d'aucune police chargée. L'encre suit `color`, le carré suit `--accent`. */
const TRACE = "M70 530V0H200V300C200 388 240 437 311 437C379 437 402 388 402 300V0H531V341C531 460 467 542 350 542C279 542 219 514 190 444L187 530Z M637 530V0H767V530Z M931 650V530H848V430H931V163C931 55 990 0 1099 0H1201V101H1121C1081 101 1061 122 1061 163V430H1201V530H1061V650Z M1617 335 1750 342C1736 466 1631 542 1504 542C1346 542 1242 433 1242 265C1242 97 1346 -12 1504 -12C1635 -12 1739 67 1754 195L1620 201C1610 130 1563 93 1504 93C1422 93 1375 156 1375 265C1375 374 1422 437 1504 437C1560 437 1607 401 1617 335Z M1822 710V0H1952V296C1952 384 1992 433 2063 433C2131 433 2154 384 2154 296V0H2283V341C2283 456 2221 542 2105 542C2042 542 1984 519 1952 462V710Z";

export default function Marque({ hauteur = 24, className }: { hauteur?: number; className?: string }) {
  return (
    <svg className={className} viewBox="-10 -740 2373 754" height={hauteur} width={Math.round(hauteur * 2373 / 754)}
         role="img" aria-label="Nitch" focusable="false">
      <g transform="scale(1 -1)"><path d={TRACE} fill="currentColor" /></g>
      <rect x="637" y="-730" width="130" height="130" style={{ fill: "var(--accent)" }} />
    </svg>
  );
}
