# Consignes pour les assistants IA (Claude Code, Codex…) sur ce projet

Projet : un Meca500 R3 (Mecademic) avec une pince MEGP 25E résout un Rubik's cube. Code et
documentation en **français**, destinés à des étudiants.
À lire d'abord : `LISEZMOI.md` (vue d'ensemble), `INTEGRATION_CAMERA.md` (partie caméra, en cours),
`GUIDE_MONTAGE.md` (montage du socle).

## Architecture
- `meca500_rubiks/` : code du VRAI robot (API `mecademicpy`). C'est la référence.
  - `reglages.py` : **source unique** de la géométrie (TCP, socle, hauteurs, vitesses). La simulation la relit.
  - `poses.py` : `pose(hauteur, inclinaison, rotation, recul, lieu)` → (x, y, z, α, β, γ), Euler XYZ mobiles.
  - `briques.py` / `mouvements.py` : mouvements du cube ; liste `MOUVEMENTS` (menu, tests, programmes RoboDK).
  - `resolution.py` : cubestring → solveur twophase (24 orientations, `meilleure_solution`) → `plan_robot`
    (Dijkstra sur orientation du cube × rotation de pince × pince restée en bas, coût = `duree.py`) →
    `executer` (liaisons rapides, `briques.py` LIAISONS : après chaque prise la pince reste ouverte autour
    du cube, la prise suivante part de là ; on ne remonte que pour tourner la pince en l'air). Toujours
    passer par `executer`.
    Étapes = triplets `(nom, arg, prise)` ; la pince reste dans `ROTATIONS_PINCE` (-90/0/+90°).
  - Vitesse : le temps vient surtout de la pince (`attendre_pince`) et des ACCÉLÉRATIONS (trajets courts),
    pas des vitesses max. Pas de `WaitIdle` dans les mouvements, pas de lissage (`SetBlending(0)`).
  - `modele_cube.py` : modèle pur Python du cube (orientation, coups, cubestring Kociemba).
- `simulation/` : RoboDK. `simulateur.RobotSimule` imite `mecademicpy` et joue **le même code** que le vrai
  robot ; `verifier.py` vérifie la cinématique, `simulateur.tester_collisions` les collisions (vrais modèles 3D).
- Scripts : `piloter_robot.py`, `placer_socle.py`, `resoudre_cube.py`, `installer_solveur.py`.

## Conventions (ne pas les changer sans demander)
- Repère de base du robot : X = devant le robot, Y = sa gauche, Z = haut ; Z = 0 sur la plaque.
- Noms des mouvements **du point de vue du robot** : avant = loin du robot, gauche = +Y ; « tourner à
  gauche » = sens anti-horaire vu de dessus.
- Position de départ : pince verticale, bout des doigts vers le robot, **J6 ≈ 0°**. Le câble de la pince
  impose |J6| ≤ 180° ; `verifier.py` le contrôle.
- Le robot ne tourne que les 2 couches du haut (le socle tient celle du bas). Bascules : la pince penche
  sur le côté (±45°). Pencher vers l'avant ou l'arrière est hors de portée du robot (testé).
- Cubestring Kociemba : U = dessus, **F = face tournée vers le robot**, R = droite du robot.
  `presenter_faces` remet le cube **tourné** dans le socle : utiliser `cubestring_apres_presenter_faces`.

## Avant de dire « c'est fini »
- `.venv/bin/pytest` : tests sans RoboDK, toujours.
- Si la géométrie ou les mouvements changent : RoboDK ouvert avec `Rubiks_Meca500.rdk`, puis
  `.venv/bin/pytest -m robodk` (cinématique + collisions de chaque mouvement). Reconstruire ensuite la
  station : `cd simulation && ../.venv/bin/python scene.py` (MODE "installer").
- Ne jamais faire bouger le vrai robot sans que l'utilisateur le demande (main sur l'arrêt d'urgence).

## Ne pas commiter
`solveur_tables/` (tables twophase, ~80 Mo, recréées par `installer_solveur.py`), `.venv/`, `.idea/`, `.claude/`.
