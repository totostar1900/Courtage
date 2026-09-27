# Le cycle de vie d'un dossier client

*Conception, 27/09/2026. Décidé avec le porteur du projet : le conseiller seul change l'état d'un dossier.*

## Pourquoi

Un dossier s'ouvrait et ne se fermait jamais. Or un mandat prend fin, un client ne paie pas, un dossier est ouvert
par erreur. Une banque ne supprime pas un compte : elle le clôture, puis l'archive pour la durée légale. Trois
principes en découlent :

- l'état d'un dossier est un **cycle de vie**, pas un interrupteur ;
- **clôturer n'est pas effacer** : on garde ce que la preuve exige, on efface le reste à date fixe ;
- chaque changement est **motivé, daté, signé**, et réversible tant que le dossier n'est pas archivé.

## Les états

| État | Ce qu'on peut faire | Passage |
|---|---|---|
| **Ouvert** | tout | à la création ; « Reprendre » depuis Suspendu ou Clôturé (motif écrit) |
| **Suspendu** | lire, exporter, préparer ; rien ne s'émet (étude, cahier des charges) | « Suspendre » : impayé, litige, pièces attendues, autre |
| **Clôturé** | lire, exporter, calculer (simulation, financement) ; aucune écriture | « Clôturer » : fin du mandat, changement de courtier, cessation d'activité, autre |
| **Archivé** | le dossier ne s'ouvre plus ; ses documents se vérifient par leur numéro | automatique, 90 jours après la clôture |
| **Supprimé** | disparaît des listes, ses membres le quittent | « Supprimer », seulement si le dossier est vide |

Le conseiller seul change l'état (rôle `conseiller`). La DRH et la lecture seule voient l'état, le motif et
l'historique.

## Ce que devient chaque donnée

| Donnée | Clôture | Archivage |
|---|---|---|
| Personnel déposé | lecture seule | **vidé** : la ligne reste (les études la référencent, son empreinte prouve ce qui a été évalué) |
| Identité des bénéficiaires, pièces | lecture seule | **effacées** (sinon, à 12 mois du paiement, comme aujourd'hui) |
| Études, rapports scellés, sceaux | lecture seule | conservés ; vérifiables par leur numéro |
| Journal, historique des états | conservés | conservés |
| Accès des membres | lecture seule | fermés |

Un dossier « vide » n'a ni personnel, ni régime, ni étude, ni cahier, ni contrat, ni départ, ni dossier de
prise en charge. La suppression ne détruit rien : le journal garde la création et la suppression.

## Mise en œuvre

- `organisations.etat` et `etat_depuis` : l'état courant, lu avant qu'un dossier soit choisi (« Vos dossiers »).
- `etats_dossier` : l'historique, append-only, sous RLS (migration `0016_cycle_de_vie`).
- `fichiers_personnel.vide_le` : le rôle applicatif ne peut modifier que `lignes`, `anomalies` et `vide_le`, et un
  déclencheur (`fichiers_personnel_vidage`, contrôlé au déploiement) n'autorise que le vidage, une seule fois.
- `services/cycle.py` : transitions, motifs, vérification du dossier vide, archivage.
- L'accès (`acces()`) refuse un dossier archivé (410) et toute écriture sur un dossier clôturé (409), sauf le
  changement d'état et les calculs qui n'enregistrent rien. L'émission d'une étude ou d'un cahier refuse aussi un
  dossier suspendu.
- L'archivage passe par `python -m courtage.purge`, chaque jour et à chaque démarrage.

## À valider

- **Les durées de conservation** au-delà de l'archivage (études, rapports, journal) : à faire valider par un
  juriste. En zone OHADA, les pièces comptables se gardent 10 ans ; la loi camerounaise sur les données personnelles
  s'applique aussi. Proposition : 10 ans après la clôture, puis effacement des études.
- **Le délai de 90 jours** entre clôture et archivage : une valeur raisonnable, à confirmer.
- La consultation d'un dossier archivé par la plateforme, sur demande motivée, n'est pas encore construite.
