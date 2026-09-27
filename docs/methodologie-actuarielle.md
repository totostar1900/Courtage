# Méthodologie actuarielle

Ce document décrit ce que la plateforme calcule, et comment. Il est tenu fidèle au code : chaque formule
renvoie au module qui la porte. Moteur : `api/src/courtage/actuariat/ifc.py` (version `ifc-1.1.0`),
échéancier : `services/etudes.py`, financement : `financement/__init__.py`, expérience réelle :
`experience.py`, hypothèses par défaut : `referentiel/__init__.py`.

## 1. L'objet

L'indemnité de fin de carrière (IFC) est versée par l'employeur au salarié qui part à la retraite. Son
montant dépend du dernier salaire et de l'ancienneté. Le barème applicable est le plus favorable de deux
sources :
- la convention collective, qui fixe le plancher ;
- le régime propre de l'entreprise, s'il existe.

L'engagement est la valeur, aujourd'hui, des indemnités que l'entreprise versera à ses salariés actuels. On
n'en retient que la part déjà acquise par leurs services passés.

La plateforme applique la **méthode prospective des unités de crédit projetées**, avec une répartition
linéaire des droits au prorata de l'ancienneté. Le calcul se fait salarié par salarié, puis on additionne.
Il reprend la méthode du classeur Ariane IFC (feuille « Calcul Exo »).

## 2. Les données

Pour chaque salarié : matricule, date de naissance, date d'embauche, salaire brut (mensuel ou annuel,
ramené à l'année) et, si le régime en distingue, la catégorie. Le sexe est facultatif et n'entre pas dans le
calcul. **Aucun nom n'est lu** : une colonne de nom est reconnue pour être ignorée.

## 3. Le calcul, pour un salarié

Notations : $D$ la date d'évaluation, $R$ l'âge de départ à la retraite, $r$ le taux d'actualisation,
$g$ la croissance des salaires, $i$ l'inflation, $t_k$ le taux de rotation à l'âge $k$, $\ell_k$ la table
de mortalité.

**Âge et ancienneté.** Une durée entre deux dates se compte en années révolues, plus les jours écoulés
depuis le dernier anniversaire divisés par 365 (les fonctions DATEDIF « Y » et « YD » du tableur).

- âge $x$ = durée(naissance, $D$) ;
- ancienneté acquise $a$ = durée(embauche, $D$), et 0 si l'embauche est postérieure à $D$ ;
- date de retraite = naissance + $R$ ans ; années restantes $n = R - x$, et 0 si le salarié a déjà passé
  l'âge (signalé en avertissement) ;
- ancienneté totale à la retraite $A = \max\big(a,\ \text{durée(embauche, date de retraite)}\big)$.

**Salaire de fin de carrière** (mensuel) :

$$S_R = \frac{S_{\text{annuel}}}{12} \times \big((1+i)(1+g)\big)^{n}$$

**Droits.** Le barème donne un nombre de mois de salaire $m(A)$ :
- **tranches cumulatives** : chaque année d'ancienneté est payée au taux de sa tranche ;
- **paliers** : un nombre de mois fixe à partir d'une ancienneté, linéaire sous le premier palier.

L'ancienneté est arrondie selon la règle du régime, en années révolues (par défaut) ou en mois entiers. Deux
conditions s'appliquent ensuite :
- **ancienneté minimale** : en dessous, le droit est nul ;
- **plafond** : le nombre de mois ne dépasse pas le plafond fixé.

Quand un régime existe, la convention reste le plancher : pour chaque salarié, on retient le plus favorable
des deux.

$$\text{IFC} = S_R \times m(A)$$

**Probabilité d'être en vie à la retraite**, par la table TV CIMA F, lue à l'âge entier $\lfloor x \rfloor$ :

$$p^{\text{survie}} = \min\left(1,\ \frac{\ell_R}{\ell_{\lfloor x \rfloor}}\right) \quad (1 \text{ si } x > R)$$

**Probabilité d'être encore dans l'entreprise**, par la rotation du personnel, année d'âge par année d'âge :

$$p^{\text{présence}} = \prod_{k=\lfloor x \rfloor}^{R-1} (1 - t_k)$$

**Actualisation** : $v = (1+r)^{-n}$.

**Valeur actuelle probable des flux futurs** (VAPF) :

$$\text{VAPF} = \text{IFC} \times p^{\text{survie}} \times p^{\text{présence}} \times v$$

**Dette actuarielle**, la part acquise par les services passés :

$$\text{Dette} = \text{VAPF} \times \frac{a}{A}$$

**Charge de l'année**, ce que coûte une année de service de plus :

$$\text{Charge} = \frac{\text{VAPF}}{A} \quad (0 \text{ si } x \ge R)$$

## 4. Les totaux

Soit $F$ le fonds déjà constitué (chez un assureur ou en provision), et $f$ les frais sur cotisation.

- **Dette**, **charge** et **VAPF** sont les sommes sur les salariés, arrondies au franc à la sortie. Les
  calculs se font sans arrondi intermédiaire.
- **Cotisation nette à verser** : $\max(\text{Dette} + \text{Charge} - F,\ 0)$.
- **Cotisation totale** : $\text{Cotisation nette} \times (1 + f)$, frais compris.

L'étude présente ce rapprochement, dans cet ordre : dette + charge − fonds = cotisation nette, puis + frais
= cotisation totale.

Les totaux sont aussi donnés **par catégorie** de personnel.

## 5. Les hypothèses

| Hypothèse | Par défaut | Remarque |
|---|---|---|
| Taux d'actualisation $r$ | 3,5 % | Le paramètre le plus sensible. |
| Croissance des salaires $g$ | 2 % | Par an, jusqu'à la retraite. |
| Inflation $i$ | 0 % | S'ajoute à $g$ par produit. |
| Âge de départ $R$ | 60 ans | |
| Rotation $t_k$ | 2 % par an | Le même taux à chaque âge, de 18 ans à $R - 1$ ; ou, en option, un taux par tranche d'âge (jusqu'à six tranches, la première à 18 ans, chacune courant jusqu'à la suivante, la dernière jusqu'à $R - 1$). |
| Table de mortalité | TV CIMA F | La table féminine (TF), pour tous. La table masculine (TH) sera proposée quand elle sera versée au référentiel avec sa source. |
| Frais sur cotisation $f$ | 4 % | |

Toutes les hypothèses se règlent dans le formulaire de l'étude, dans des bornes : actualisation de −2 % à
15 %, salaires de −5 % à 15 %, inflation de −5 % à 20 %, départ de 50 à 70 ans, rotation de 0 à 50 %, frais
de 0 à 20 %. Chacune y dit son rôle, son effet et comment la fixer ; le même texte figure au rapport.

Une étude qui s'écarte d'une valeur par défaut enregistre l'écart et sa **justification**. L'écart est
imprimé dans le rapport scellé. Une étude qui s'écarte fortement de la précédente est signalée.

**Sensibilités.** L'étude recalcule la dette et la charge dans six cas :
- le taux d'actualisation à $r - 1$ et $r + 1$ point ;
- la croissance des salaires à $g - 1$ et $g + 1$ point ;
- la rotation à $t_k - 1$ point (sans descendre sous zéro) et $t_k + 1$ point, à chaque âge.

Quand la rotation est donnée par tranche d'âge, l'expérience réelle compare la rotation observée à la
rotation moyenne supposée de la population : le taux de chaque salarié à son âge, en moyenne.

## 6. L'échéancier des départs

Chaque salarié est rangé à l'année de sa retraite. S'il a déjà passé l'âge, il est rangé à l'année de
l'évaluation. Pour chaque année :
- le nombre de départs ;
- l'indemnité si tous partent ($\sum \text{IFC}$) ;
- les **prestations probables** ($\sum \text{IFC} \times p^{\text{survie}} \times p^{\text{présence}}$), ce
  que l'entreprise versera probablement cette année-là ;
- la VAPF ;
- le détail par catégorie.

Le graphique de l'étude lit ces mêmes chiffres, par année ou cumulés. En lecture cumulée, il les compare au
fonds déjà constitué.

## 7. Le financement

Le module projette, année par année, un fonds alimenté par les cotisations et vidé par les prestations
probables. La projection se fait pour chaque offre d'assureur (taux garanti, participation aux bénéfices,
frais) et sous trois scénarios de rendement : prudent 3,5 %, central 5 %, favorable 6,5 %.

Une année $t$, dans l'ordre :

1. **L'entreprise cotise.** La cotisation est la charge indexée, $\text{Charge} \times (1+g)^{t-1}$, plus
   une annuité d'amortissement du déficit initial $\max(\text{Dette} - F, 0) / N$ pendant $N$ années.
2. **L'assureur prélève ses frais sur cotisations.**
3. **Le fonds est crédité** au taux
   $\text{garanti} + \text{participation} \times \max(\text{rendement} - \text{garanti}, 0)$.
4. **L'assureur prélève ses frais sur encours.**
5. **Les prestations probables de l'année sont payées par le fonds**, dans la limite de ce qu'il contient.
   Le reste est un découvert, que l'entreprise paie elle-même.

Deux critères en sortent :
- **Coût net actualisé** : les cotisations et les découverts actualisés, moins le fonds restant à l'horizon
  (il appartient à l'entreprise). C'est un critère de **comparaison** entre offres, qui reçoivent les mêmes
  cotisations et paient les mêmes prestations. Il peut être négatif.
- **Couverture** : le fonds à l'horizon, rapporté à la valeur à cette date des prestations probables qui
  restent à payer.

Le classement des réponses d'assureurs se fait par coût net actualisé dans le scénario central. La réponse
**recommandée** est la moins chère parmi celles qui respectent le cahier des charges.

## 8. L'expérience réelle

Les départs enregistrés dans le dossier sont confrontés au prévu.

- **Taux de rotation observé** : départs pour démission ou licenciement ÷ (années × effectif), sur les
  cinq dernières années au plus.
- **Seuil de crédibilité** : ce taux n'est crédible qu'à partir de **5 départs**.
- **Proposition** : il est proposé comme hypothèse s'il s'écarte d'au moins un demi-point de l'hypothèse en
  cours. Il n'est **jamais appliqué d'office** : changer d'hypothèse reste une décision justifiée.

Dans le cahier des charges envoyé aux assureurs, l'historique est regroupé par périodes d'au moins trois
départs, pour qu'aucun montant individuel ne se lise.

## 9. Limites, dites

- **Seul le départ à la retraite est évalué.** Les autres événements qu'un régime peut couvrir (départ
  anticipé, licenciement économique, décès) sont enregistrés et signalés (« événements non chiffrés »),
  mais pas chiffrés.
- **Une seule table de mortalité pour tous** : la table féminine. Les femmes y vivent plus longtemps, donc
  l'hypothèse est prudente, puisqu'elle augmente la probabilité de toucher l'indemnité.
- **Rotation constante avec l'âge** par défaut. Une table par âge est possible dans le moteur ; l'interface
  ne propose que le taux unique.
- **Pas d'échelle de salaire par âge ou par carrière** : une croissance uniforme.
- **Base de salaire approchée.** Un régime fondé sur la moyenne des douze derniers mois est évalué sur le
  salaire courant projeté, et c'est signalé.
- **Une indication, pas un avis réglementaire.** L'étude est un calcul actuariel d'aide à la décision ; ce
  n'est pas un avis juridique ou fiscal. Les conventions « à valider » ne permettent pas d'émettre.
