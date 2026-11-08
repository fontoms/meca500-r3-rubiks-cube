# Rubik's Cube avec le Meca500 R3

Projet étudiant autour d'un robot Mecademic Meca500 R3 et d'une pince MEGP 25E. Le robot scanne les
six faces d'un Rubik's Cube avec une caméra, calcule une solution, puis peut l'exécuter ou la simuler
dans RoboDK.

## Documentation

- [Vue d'ensemble, commandes et tests](./LISEZMOI.md)
- [Intégration de la caméra](./INTEGRATION_CAMERA.md)
- [Guide de montage du socle](./GUIDE_MONTAGE.md)

## Récupération et démarrage

Cette branche contient le sous-module de vision. Pour la cloner avec son code caméra :

```powershell
git clone --recurse-submodules --branch feature/camera-integration https://github.com/fontoms/meca500-r3-rubiks-cube.git
```

Consulte [LISEZMOI.md](./LISEZMOI.md) pour installer les dépendances, générer les tables du solveur et
lancer l'interface ou la simulation.

## Contributeurs

- [D-Lecol](https://github.com/D-Lecol) — projet d'origine et développement du robot.
- [fontoms](https://github.com/fontoms) — intégration caméra, interface et adaptation du projet.
