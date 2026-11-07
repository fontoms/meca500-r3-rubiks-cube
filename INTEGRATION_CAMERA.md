# Intégration de la caméra : guide pour le groupe « caméra »

Ce document explique **où brancher la caméra** et **quel cubestring fournir** au robot. Tout le reste
existe déjà et est testé : mouvements du robot, présentation des 6 faces à la caméra, solveur,
exécution de la solution.

## 1. Ce qui existe déjà

```
Cube dans le socle
  │  presenter_faces(robot)          ← meca500_rubiks/mouvements.py
  │    pose le cube sur la table, devant la caméra, et montre les 6 faces une par une ;
  │    à chaque face, appelle photographier(robot, face)   ← À BRANCHER (meca500_rubiks/briques.py)
  │    puis remet le cube dans le socle (TOURNÉ par rapport au départ, voir § 4)
  ▼
6 photos  ──►  VOTRE CODE : couleurs des 54 cases  ──►  cubestring (54 lettres)
  ▼
resolution.cubestring_apres_presenter_faces(cubestring)   ← tient compte de la rotation du § 4
  ▼
resolution.resoudre(robot, cubestring)      ← solveur twophase + mouvements du robot
  ▼
Cube résolu
```

Points d'entrée (tous dans `meca500_rubiks/resolution.py`, sauf mention) :

| Fonction | Rôle |
|---|---|
| `rubiks.connecter()` / `rubiks.deconnecter(robot)` | connexion au vrai Meca500 (`import meca500_rubiks as rubiks`) |
| `rubiks.presenter_faces(robot)` | montre les 6 faces à la caméra, renvoie la liste des faces dans l'ordre des photos |
| `verifier_cubestring(s)` | contrôle le format (54 lettres, 9 de chaque, centres URFDLB) |
| `cubestring_apres_presenter_faces(s)` | convertit le cubestring des photos pour le cube remis dans le socle |
| `calculer_solution(s)` | solution `[(face, k)]` (twophase), sans bouger le robot |
| `plan_robot(coups)` | mouvements du robot correspondants (sans bouger le robot) |
| `resoudre(robot, s)` | calcule et fait jouer la solution |
| `python resoudre_cube.py <cubestring> [--sans-robot]` | la même chose en ligne de commande |

En cas de problème, `ErreurResolution` est levée avec un message clair : cubestring invalide, ou
cube impossible (« couleurs mal lues ? »). Il faut l'attraper et refaire les photos, **ne jamais lancer le
robot avec un cubestring douteux**.

## 2. Le cubestring (format Kociemba)

54 lettres parmi `U R F D L B`. Les faces sont dans l'ordre **U, R, F, D, L, B**, 9 cases chacune. Chaque
lettre est **la face dont le centre a la couleur de cette case**. Les centres d'un Rubik's cube ne
bougent pas les uns par rapport aux autres ; les cases 5, 14, 23, 32, 41 et 50 (centres) valent donc
toujours U, R, F, D, L, B.

Dans chaque face, on lit les cases **ligne par ligne, de gauche à droite, en regardant la face de
l'extérieur**, avec en haut :

| Face | Rangée du haut (cases 1-2-3) = côté de… |
|---|---|
| U (dessus) | B |
| R, F, L, B (côtés) | U (le dessus) |
| D (dessous) | F |

```
              U1 U2 U3
              U4 U5 U6
              U7 U8 U9
    L1 L2 L3  F1 F2 F3  R1 R2 R3  B1 B2 B3
    L4 L5 L6  F4 F5 F6  R4 R5 R6  B4 B5 B6
    L7 L8 L9  F7 F8 F9  R7 R8 R9  B7 B8 B9
              D1 D2 D3
              D4 D5 D6
              D7 D8 D9
cubestring = U1…U9 R1…R9 F1…F9 D1…D9 L1…L9 B1…B9
```

**Correspondance avec le cube dans le socle** (du point de vue du robot) :
U = dessus, D = dessous, **F = face tournée vers le robot**, B = face opposée au robot,
R = face à droite du robot, L = face à gauche du robot.
Cube résolu : `UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB`.

## 3. Les photos de `presenter_faces`

La caméra est **à droite du cube posé sur la table** (vu depuis le robot), à 250 mm, à hauteur de son
centre, et elle regarde le cube (`TABLE` dans `meca500_rubiks/reglages.py`, dessin dans
`GUIDE_MONTAGE.md`). Avant chaque photo, le robot est immobile, pince au-dessus du cube.

Faces nommées **comme au départ** (cube dans le socle avant `presenter_faces`), image prise caméra droite
(pas de miroir) :

| Photo | Face vue (lettre) | En haut de l'image | À droite de l'image | Rangée du haut Kociemba de cette face |
|---|---|---|---|---|
| 1 | droite (R) | dessus | loin du robot | en haut de l'image |
| 2 | loin du robot (B) | dessus | gauche | en haut de l'image |
| 3 | gauche (L) | dessus | vers le robot | en haut de l'image |
| 4 | dessus (U) | droite | vers le robot | **à gauche** de l'image → tourner l'image de 90° |
| 5 | vers le robot (F) | droite | dessous | **à gauche** de l'image → tourner l'image de 90° |
| 6 | dessous (D) | droite | loin du robot | **à gauche** de l'image → tourner l'image de 90° |

Pour les photos 4 à 6, il faut tourner l'image de 90° dans le sens horaire avant de lire les cases
(la rangée du haut Kociemba est alors en haut). Ce tableau vient de `resolution.vue_camera(...)`, il est
vérifié par `tests/test_resolution.py`. Si on change la séquence (`ETAPES_PHOTO` dans `mouvements.py`),
on le recalcule avec :

```python
from meca500_rubiks import resolution
for face, o in resolution.orientations_presenter_faces():
    print(face, resolution.vue_camera(o))     # (face au centre, face en haut, face à droite)
```

**Où brancher la caméra** : `photographier(robot, face)` dans `meca500_rubiks/briques.py`. Aujourd'hui,
la fonction attend que le robot soit immobile (`WaitIdle`), puis fait une pause de `DUREE_PHOTO`.
Remplacez la pause par la prise de vue, et gardez le `WaitIdle` avant. Dans la simulation RoboDK, le faux
robot a une méthode `prendre_photo` qui affiche juste la face : ne cassez pas ce cas, sinon les tests
de simulation tombent.

## 4. Attention : le cube revient TOURNÉ dans le socle

Après les 6 photos, `presenter_faces` remet le cube dans le socle **dans une autre orientation qu'au
départ**. C'est le chemin le plus court, et c'est voulu. Un cubestring construit avec les noms de faces
du départ (tableau du § 3) décrit donc le cube d'**avant** : il faut le convertir.

```python
import meca500_rubiks as rubiks
from meca500_rubiks import resolution

robot = rubiks.connecter()
try:
    rubiks.presenter_faces(robot)                   # appelle votre code photo à chaque face
    cubestring_avant = ...                          # VOTRE CODE : à partir des 6 photos (noms du § 3)
    cubestring = resolution.cubestring_apres_presenter_faces(cubestring_avant)
    resolution.resoudre(robot, cubestring)
finally:
    rubiks.deconnecter(robot)
```

Sans cette conversion, le robot joue une solution fausse : un test le vérifie
(`test_sans_conversion_le_robot_se_tromperait`). Si le cube est scanné autrement (dans le socle, à la
main…), passez directement le cubestring du cube **tel qu'il est dans le socle** à `resoudre`.

## 5. Installer et tester sans robot

```
.venv/bin/pip install -r requirements.txt
.venv/bin/python installer_solveur.py            # tables du solveur (~80 Mo, longues à générer)
.venv/bin/python installer_solveur.py --tables <dossier>   # ou copie depuis un PC qui les a déjà
.venv/bin/python resoudre_cube.py --exemple --sans-robot
.venv/bin/pytest                                  # tests (ceux qui ont besoin de RoboDK sont ignorés s'il est fermé)
```

Pour fabriquer des cubestrings de test réalistes sans caméra, utilisez le modèle du cube :

```python
from meca500_rubiks.modele_cube import ModeleCube
m = ModeleCube()
for face, k in [("R", 1), ("U", -1), ("F", 2)]:   # mélange (k = 1 horaire, -1 anti-horaire, 2 demi-tour)
    m.coup(face, k)
print(m.facelets())                                 # cubestring de ce cube, dans le socle
```

Dans RoboDK (station `Rubiks_Meca500.rdk`), mettez `MODE = "resolution"` dans `simulation/parametres.py`
et lancez `scene.py` : le robot simulé résout un cube mélangé avec exactement le même code.

## 6. À ne pas faire
- **Ne pas commiter `solveur_tables/`** (80 Mo, ignoré par `.gitignore`) : `installer_solveur.py` le
  recrée.
- Ne pas changer les cotes de `meca500_rubiks/reglages.py` (TCP, socle, hauteurs) sans relancer
  `pytest -m robodk`, qui vérifie la cinématique et les collisions avec les vrais modèles 3D.
- Ne pas lancer `resoudre` sur le vrai robot avec un cubestring non vérifié (cf. § 1).
