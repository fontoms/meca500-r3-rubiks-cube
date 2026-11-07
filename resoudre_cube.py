# -*- coding: utf-8 -*-
"""
Résout le cube avec le VRAI robot à partir de son cubestring (fourni par le groupe caméra).

    python resoudre_cube.py <cubestring>               → calcule la solution, l'affiche, demande
                                                         confirmation, puis la fait jouer au robot
    python resoudre_cube.py <cubestring> --sans-robot  → calcule et affiche seulement (pas de robot)
    python resoudre_cube.py --exemple --sans-robot     → essai avec un cube mélangé d'exemple

Le cubestring (54 lettres U R F D L B, format Kociemba) décrit le cube TEL QU'IL EST POSÉ DANS LE
SOCLE : U = dessus, F = face tournée vers le robot, R = face à droite du robot (détails :
meca500_rubiks/resolution.py). Première fois : python installer_solveur.py

Depuis un autre programme (ex. le script caméra), robot déjà connecté :
    from meca500_rubiks import resolution
    resolution.resoudre(robot, cubestring)
"""
import argparse
import sys
import time

import meca500_rubiks as rubiks
from meca500_rubiks import resolution

EXEMPLE = "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL"


def main(argv):
    parser = argparse.ArgumentParser(description="Résout le Rubik's cube avec le Meca500.")
    parser.add_argument("cubestring", nargs="?", help="54 lettres U R F D L B (ordre des faces U R F D L B)")
    parser.add_argument("--exemple", action="store_true", help="utilise un cube mélangé d'exemple")
    parser.add_argument("--sans-robot", action="store_true", help="calcule et affiche, sans bouger le robot")
    args = parser.parse_args(argv)
    cubestring = EXEMPLE if args.exemple else args.cubestring
    if not cubestring:
        parser.error("donne un cubestring (ou --exemple)")

    try:
        debut = time.time()
        coups = resolution.calculer_solution(cubestring)
    except resolution.ErreurResolution as e:
        print("Erreur :", e)
        return 1
    etapes = resolution.plan_robot(coups)
    print("Solution (%d coups, calculée en %.1f s) : %s" % (len(coups), time.time() - debut, resolution.ecrire(coups)))
    print("Mouvements du robot : %d" % len(etapes))
    for i, etape in enumerate(etapes, 1):
        print("  %2d. %s" % (i, resolution.decrire(etape)))
    if args.sans_robot or not etapes:
        return 0

    print("\nCube dans le socle comme décrit (U dessus, F vers le robot) ? Main sur l'arrêt d'urgence.")
    if input("Entrée pour lancer, autre chose pour annuler : ").strip():
        print("Annulé.")
        return 0
    robot = rubiks.connecter()
    try:
        debut = time.time()
        resolution.executer(robot, etapes)
        robot.WaitIdle(120)
        print("Cube résolu en %.0f s." % (time.time() - debut))
    finally:
        rubiks.deconnecter(robot)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
