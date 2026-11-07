# Projet Rubik's cube — Meca500 R3 + pince MEGP 25E

```
Rubiks_Meca500/
├── piloter_robot.py       ← PILOTE LE VRAI ROBOT (menu, ou un seul mouvement)
├── placer_socle.py        ← aide au montage du socle (GUIDE_MONTAGE.md)
├── resoudre_cube.py       ← RÉSOUT LE CUBE avec le vrai robot à partir de son cubestring
├── INTEGRATION_CAMERA.md  ← guide pour le groupe caméra (cubestring, photos, où brancher)
├── installer_solveur.py   ← installe le solveur twophase et ses tables (une fois par ordinateur)
├── solveur_tables/        ← tables du solveur (~80 Mo, ignoré par git)
├── meca500_rubiks/        ← LE CODE DU ROBOT (API mecademicpy)
│   ├── reglages.py        ←   adresse IP, vitesses, géométrie (socle, cube, TCP, hauteurs)
│   ├── poses.py              calcul des poses de la pince : pose(hauteur, inclinaison, rotation, recul, lieu)
│   ├── briques.py            préparer, position d'attente, pince, aller, saisir, transférer, photographier…
│   ├── mouvements.py         les mouvements du cube, une fonction chacun + liste MOUVEMENTS
│   ├── resolution.py         cubestring → solution (twophase) → mouvements du robot
│   ├── modele_cube.py        modèle logiciel du cube (orientation, coups, cubestring)
│   └── robot_reel.py         connexion / déconnexion du vrai robot, menu
├── Rubiks_Meca500.rdk     ← la station RoboDK pour voir les mouvements en simulation
├── simulation/            ← fait tourner meca500_rubiks dans RoboDK
│   ├── parametres.py      ←   maillages 3D, MODE (reprend la géométrie de reglages.py)
│   ├── maillages/            socle allégé pour RoboDK (tiré de modeles_3D/)
│   ├── simulateur.py         joue meca500_rubiks dans RoboDK (programmes de la station)
│   ├── verifier.py           vérification cinématique
│   ├── scene.py              point d'entrée (Tools > Run Script > 00_Rubiks_Meca500)
│   ├── construction.py       construction 3D de la scène
│   ├── banc_essais.py        MODE "tests" (collisions) et "resolution"
│   ├── modele_cube.py        modèle logiciel du cube (sans RoboDK)
│   └── connexion_robodk.py   connexion à RoboDK
├── tests/                 ← tests pytest, lançables mouvement par mouvement depuis PyCharm
├── journal/               ← dernier_mouvement.txt (commandes envoyées), verification.txt, erreur.txt
├── modeles_3D/            ← tes pièces réelles (doigts, socle) + photos du montage
├── robot/                 ← modèle du Meca500 R3
└── archives/              ← anciennes versions
```

## Les mouvements : `meca500_rubiks/mouvements.py`
Une fonction par mouvement, **du point de vue du robot** : avant = loin du robot, arrière = vers le robot,
gauche / droite = la gauche / la droite du robot ; tourner « à gauche » = sens anti-horaire vu de dessus.

Position de départ : pince verticale, bout des doigts vers le robot, **J6 ≈ 0°** (câble de la pince dans
sa position neutre). J6 reste entre −146° et +146° dans tous les mouvements (vérifié, voir plus bas).

| Fonction | Ce que fait le robot |
|---|---|
| `verifier_outil` | **sans le cube** : pince ouverte, patins 10 mm au-dessus du haut du cube, pause 10 s (contrôle du TCP et du socle) |
| `prendre_et_reposer` | saisit le cube, le soulève de 30 mm, le repose |
| `tourner_cube_gauche` / `tourner_cube_droite` | le cube entier tourne de 90° vers la gauche (anti-horaire vu de dessus) / vers la droite |
| `basculer_gauche` / `basculer_droite` | le cube bascule de 90° : la face du dessus part à gauche / à droite du robot |
| `basculer_avant` / `basculer_arriere` | la face du dessus part loin du robot / vient vers le robot (3 prises) |
| `tourner_haut_gauche` / `tourner_haut_droite` | le socle tient la couche du bas, les 2 couches du haut tournent de 90° vers la gauche / la droite |
| `presenter_faces` | pose le cube sur la table, présente ses 6 faces à la caméra, le remet dans le socle |

Ils sont construits avec les briques de `briques.py`, et les positions sont calculées par
`pose(hauteur, inclinaison, rotation, recul)` à partir des valeurs de `reglages.py`.

## Résoudre le cube : `resoudre_cube.py`
**Groupe caméra : voir [INTEGRATION_CAMERA.md](INTEGRATION_CAMERA.md)** (où brancher la caméra, format du
cubestring, orientation de chaque photo). Consignes pour les assistants IA : [CLAUDE.md](CLAUDE.md).

Première fois sur un ordinateur : **`python installer_solveur.py`**. Il installe la librairie
`RubikTwoPhase` (solveur de Kociemba) et génère ses tables, ce qui prend une demi-heure ou plus.
Si tu as déjà les tables (par exemple celles du groupe solveur) :
`python installer_solveur.py --tables <dossier contenant co_classidx, phase1_prun…>`.
Les tables vont dans `solveur_tables/`, qui n'est pas suivi par git.

```
python resoudre_cube.py <cubestring>               # calcule, affiche, demande Entrée, fait jouer le robot
python resoudre_cube.py <cubestring> --sans-robot  # calcule et affiche seulement
python resoudre_cube.py --exemple --sans-robot     # essai avec un cube mélangé d'exemple
```

**Le cubestring (contrat avec le groupe caméra)** : 54 lettres `U R F D L B`, format Kociemba (faces
dans l'ordre U, R, F, D, L, B, 9 cases chacune ; la lettre d'une case = la face dont le centre a cette
couleur). Il décrit le cube **tel qu'il est posé dans le socle** :
U = dessus, D = dessous, **F = face tournée vers le robot**, B = face opposée au robot,
R = face à droite du robot, L = face à gauche du robot.
Cube résolu : `UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB`.

Depuis le programme de la caméra (robot déjà connecté) :
```python
from meca500_rubiks import resolution
resolution.resoudre(robot, cubestring)
```

**Comment le robot joue la solution** : il ne sait tourner que les 2 couches du haut (le socle tient
celle du bas). Pour chaque coup, il amène la face à tourner en bas (bascules / rotations du cube),
puis tourne les 2 couches du haut. Il suit l'orientation du cube d'un coup à l'autre au lieu de le
remettre droit : 1 à 3 prises par quart de tour, environ 60 mouvements pour une solution de 20 coups.
Le code du groupe solveur (`mapping.py`, `solver.py`) est conservé dans `archives/solveur_groupe/` :
son enchaînement est juste, mais il remet le cube droit après chaque coup (6 à 12 prises par coup).

Vérifié : `tests/test_resolution.py` (cubestring → solveur → mouvements → cube résolu, avec le modèle)
et, dans RoboDK, `MODE = "resolution"` de `simulation/parametres.py`, qui utilise exactement le même
code que le vrai robot.

## Piloter le vrai robot : `piloter_robot.py`
```
python piloter_robot.py                    # menu
python piloter_robot.py basculer_droite    # un seul mouvement, puis déconnexion
python piloter_robot.py --liste            # liste des mouvements
```
Ou dans ton propre script :
```python
import meca500_rubiks as rubiks

robot = rubiks.connecter()          # connexion, activation, position d'attente
rubiks.tourner_cube_gauche(robot)
rubiks.deconnecter(robot)
```

### Avant le premier essai sur le vrai robot
**Montage du socle et réglage de sa position : voir [GUIDE_MONTAGE.md](GUIDE_MONTAGE.md)** (`placer_socle.py`).

- ordinateur relié au robot en Ethernet (IP du robot dans `reglages.py`, `ADRESSE_IP`) ;
- socle posé sur la plaque du robot, centre de la poche à X=170, Y=0 (le cube repose à Z=7 mm) ;
- commence par `verifier_outil` **sans le cube** : les patins doivent encadrer la poche, 10 mm
  au-dessus de l'endroit où sera le haut du cube ;
- 1er passage **sans le cube**, vitesses basses (réglées par défaut), main sur l'arrêt d'urgence ;
- commence par `prendre_et_reposer`, un mouvement à la fois.

## Tester, mouvement par mouvement
`tests/test_mouvements.py` contient une classe par mouvement (`TestBasculerDroite`…). Dans PyCharm,
le ▶ à côté d'une classe lance seulement ce mouvement :
- séquence de commandes avec un faux robot (départ / retour en attente, pince, hauteur) — sans RoboDK ;
- cinématique dans RoboDK (atteignable, butées, poignet, sauts) — si RoboDK est ouvert, sinon ignoré ;
- simulation animée dans RoboDK — seulement avec `pytest -m simulation`.

`tests/test_briques.py` teste chaque brique (saisir, lâcher, ouvrir/fermer…), `tests/test_poses.py` le calcul des poses.

En terminal : `.venv/bin/pytest`, `.venv/bin/pytest tests/test_mouvements.py::TestBasculerDroite`,
`.venv/bin/pytest -m simulation`. Installation : `.venv/bin/pip install -r requirements.txt`.

### Configurations PyCharm (menu en haut à droite, ▶)
| Configuration | Ce qu'elle fait |
|---|---|
| 1 - Tests | tous les tests (code + cinématique RoboDK) |
| 2 - Simulation RoboDK | joue tous les mouvements dans RoboDK |
| 3 - Simuler UN mouvement | demande le nom (ex. `basculer_droite`) et le joue dans RoboDK |
| 4 - Vérification cinématique | rapport complet (`journal/verification.txt`) |
| 6 - ROBOT RÉEL : menu | connecte le vrai robot et propose les mouvements |
| 6b - ROBOT RÉEL : UN mouvement | demande le nom et l'exécute sur le vrai robot |
| 7 - Reconstruire la station | `scene.py` selon le MODE de `parametres.py` |

## Présenter les faces à la caméra : `presenter_faces`
Le socle cache le bas des faces : la présentation se fait donc **sur la table, à droite du socle**.
1. le robot sort le cube du socle et le pose sur la table (`TABLE` dans `reglages.py`) ;
2. la caméra, à droite du cube, voit une face ; le robot tourne / bascule le cube sur la table
   et s'arrête avant chaque photo (pince au-dessus du cube) : 6 photos, une par face ;
3. le robot remet le cube dans le socle (dans une autre orientation qu'au départ).

Ordre des photos (faces nommées selon leur position au départ, dans le socle) :
droite, loin du robot, gauche, dessus, vers le robot, dessous — `ETAPES_PHOTO` dans `mouvements.py` (5 prises).
Un test vérifie, avec le modèle du cube, que chaque photo montre bien la face annoncée.

**Orientation sur la table** : pour que le robot atteigne la table avec la pince penchée (bascule),
la pince reste toujours face au robot. Posé à `TABLE = (170, -110, 0)`, le cube est donc tourné
d'environ 33° : la caméra doit le regarder perpendiculairement à la ligne robot → cube, à hauteur
de son centre (dans RoboDK : objet `Camera`, à `DISTANCE_CAMERA` = 250 mm ; taille dans `parametres.py`).

- **Dans RoboDK** : programme **presenter_faces** de l'arbre. La caméra n'est pas simulée : c'est juste
  sa représentation 3D ; à chaque « photo », RoboDK fait une pause et affiche la face dans la barre d'état.
- **Sur le vrai robot** : `python piloter_robot.py presenter_faces`. Pour l'instant chaque « photo » est
  une pause de `DUREE_PHOTO` s : branche ta caméra dans `photographier()` (`meca500_rubiks/briques.py`).
- Si tu déplaces le point de pose : change `TABLE` dans `reglages.py` **et** `TABLE_X`, `TABLE_Y`,
  `HAUTEUR_TABLE` dans `simulation/parametres.py`, puis relance les tests (cinématique).

## Voir les mouvements dans RoboDK
1. Ouvre RoboDK, puis **File > Open** → `Rubiks_Meca500.rdk`
   (le double-clic dans le Finder ouvre une station vide sur macOS).
2. Dans l'arbre (à gauche), en bas : un programme par fonction, **avec le même nom**.
   Double-clic = RoboDK exécute cette fonction de `meca500_rubiks`, exactement comme le ferait le robot.
3. Le cube garde son état d'un mouvement à l'autre ; **remise_a_zero** remet un cube neuf.

Si tu modifies un mouvement ou un réglage, le double-clic suivant joue la nouvelle version.
Si tu ajoutes un mouvement : ajoute-le à la liste `MOUVEMENTS` (bas de `mouvements.py`), ajoute sa classe
dans `tests/test_mouvements.py`, puis reconstruis la station (RoboDK : **Tools > Run Script > 00_Rubiks_Meca500**)
pour qu'il apparaisse dans l'arbre.

## Vérifier les mouvements (cinématique)
Programme **verifier_mouvements** dans l'arbre de la station (ou `simulation/verifier.py`). Il rejoue
chaque mouvement sans bouger le robot, en calculant la cinématique inverse tous les 1 mm / 1° le long
de chaque ligne droite. Il vérifie :
- que chaque point est **atteignable** ;
- les **butées** articulaires (marge ≥ 10°) ;
- la **singularité du poignet** (|J5| ≥ 10°) ;
- le **câble de la pince** : J6 reste entre −180° et +180° (recommandation Mecademic), en partant du robot
  juste après le homing ;
- l'absence de **saut d'articulation** (changement de configuration en plein MoveLin).

Bilan affiché dans RoboDK et écrit dans `journal/verification.txt`. Les collisions se vérifient à part :
`MODE = "tests"` dans `simulation/parametres.py`, puis lancer `scene.py`.

## Géométrie réelle (pince MEGP 25E, doigts et socle imprimés)
- **Pince MEGP 25E** avec sa plaque d'adaptation standard (manuel Mecademic, figure 1) : le trou M4
  des mâchoires est à 19 mm sous la bride et 17 mm de son axe ; course 3 mm par mâchoire.
- **Doigts** (`modeles_3D/doigts`) : vissés sur les mâchoires, ils descendent en S jusqu'aux patins
  horizontaux (10 mm de haut, 45 mm de long). Centre des patins = TCP = `SetTrf(3.1, 0, 93.2, 0, 0, 0)`
  (l'ancien 94,5 mm était presque juste). Écart entre patins : 63,6 mm ouverte, 57,6 mm fermée :
  le scotch sur les patins rattrape le reste (cube 57 mm) — garde-le.
- **Prise** : patins sur la couche du milieu (`H_CUBE`) ; pour `tourner_haut`, sur les couches du milieu
  et du haut (`H_COUCHES_HAUT`) pendant que le socle tient celle du bas.
- **Bascule** : `DECALAGE_BASCULE = 10` mm (cube tenu plus bas dans les patins), sinon les bras des
  doigts touchent les coins du haut du cube quand la pince est penchée à 45°.
- **Socle** (`Cube_holder.stl`) posé sur la plaque : le cube repose 7 mm au-dessus, `SOCLE = (170, 0, 7)`.

Le fichier `modeles_3D/pince/MEGP_25LS.stp` est celui de la 25LS : il n'est pas utilisé (la simulation
dessine la 25E d'après son manuel).

## Vérifier les collisions (vrais doigts, vrai socle)
Chaque mouvement de `meca500_rubiks` est rejoué déplacement par déplacement avec la détection de
collisions de RoboDK (bras, pince, doigts, cube tenu contre socle, table, caméra, cube posé) :
`pytest -m robodk`, ou `MODE = "tests"` dans `simulation/parametres.py` puis `scene.py`
(→ `journal/collisions.txt`). Résultat actuel : aucune collision.

## Changer la géométrie
Tout est dans `meca500_rubiks/reglages.py` ; la simulation le reprend (plus de double saisie).
Les maillages de la simulation : `simulation/parametres.py` (`FICHIER_*`, `POSE_DOIGT_*`, `PINCE_25E`).
Reconstruis ensuite la station (Tools > Run Script > 00_Rubiks_Meca500) et relance les tests.

## Affichage RoboDK
Les grosses flèches des repères (socle, table, caméra, base du robot) sont masquées à la construction
de la scène. **Alt + /** les réaffiche ou les masque toutes ; **+** / **−** changent leur taille.
