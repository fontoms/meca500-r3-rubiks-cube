# -*- coding: utf-8 -*-
"""
Résout le cube avec le VRAI robot, ou dans la simulation RoboDK, à partir de son cubestring
(fourni par le groupe caméra).

    python resoudre_cube.py <cubestring>                 → calcule la solution, l'affiche, demande
                                                           confirmation, puis la fait jouer au robot
    python resoudre_cube.py <cubestring> --sans-robot    → calcule et affiche seulement (pas de robot)
    python resoudre_cube.py --exemple --sans-robot       → essai avec un cube mélangé d'exemple

    Simulation RoboDK (RoboDK ouvert avec Rubiks_Meca500.rdk), cube FICTIF :
    python resoudre_cube.py --exemple --simulation       → le cube d'exemple
    python resoudre_cube.py <cubestring> --simulation    → un cube décrit par son cubestring
    python resoudre_cube.py --melange 25 --simulation    → un cube mélangé au hasard (25 coups)
        --graine 3        mélange reproductible
        --collisions      teste chaque déplacement (collisions, atteignabilité) au lieu de l'animer
    python resoudre_cube.py --exemple --comparer         → durée estimée avant / après optimisation
    python resoudre_cube.py --presenter-faces           → scanne, calcule et résout en une session

Le cubestring (54 lettres U R F D L B, format Kociemba) décrit le cube TEL QU'IL EST POSÉ DANS LE
SOCLE : U = dessus, F = face tournée vers le robot, R = face à droite du robot (détails :
meca500_rubiks/resolution.py). Première fois : python installer_solveur.py

Depuis un autre programme (ex. le script caméra), robot déjà connecté :
    from meca500_rubiks import resolution
    resolution.resoudre(robot, cubestring)
"""
import argparse
import os
import random
import sys
import time

import meca500_rubiks as rubiks
from meca500_rubiks import resolution
from meca500_rubiks.modele_cube import ModeleCube, inverse
from meca500_rubiks.robot_reel import demander_facteur_vitesse
from meca500_rubiks.vision_capture import CUBESTRING_PATH, ErreurCamera, choisir_camera

EXEMPLE = "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL"


def minutes(secondes):
    return "%d min %02d s" % (secondes // 60, secondes % 60)


def afficher_plan(coups, etapes, duree_calcul, detail=True):
    print("Solution (%d coups, calculée en %.1f s) : %s" % (len(coups), duree_calcul, resolution.ecrire(coups)))
    print("Robot : %d prises, durée estimée %s" % (resolution.nombre_de_prises(etapes),
                                                     minutes(resolution.duree_plan(etapes))))
    if detail:
        for i, etape in enumerate(etapes, 1):
            print("  %2d. %s" % (i, resolution.decrire(etape)))


def comparer(cubestring, coups, etapes):
    """Durée estimée : plan d'avant l'optimisation (solution brute du solveur) / plan optimisé."""
    brut = resolution.calculer_solution(cubestring)
    simple = resolution.plan_simple(brut)
    print("\nComparaison (durées estimées, vitesses de reglages.py) :")
    print("  avant : %2d coups, %2d prises, %s" % (len(brut), resolution.nombre_de_prises(simple),
                                                 minutes(resolution.duree_plan(simple))))
    print("  après : %2d coups, %2d prises, %s" % (len(coups), resolution.nombre_de_prises(etapes),
                                                 minutes(resolution.duree_plan(etapes))))


def simuler(coups, etapes, melange, collisions):
    """Joue la solution dans RoboDK sur un cube fictif mélangé par `melange`."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "simulation"))
    import banc_essais
    resolu, _, problemes = banc_essais.resoudre_en_simulation(melange, coups, etapes, collisions, afficher=print)
    if problemes:
        print("%d problème(s) de collision / atteignabilité." % len(problemes))
    return 0 if resolu and not problemes else 1


def main(argv):
    parser = argparse.ArgumentParser(description="Résout le Rubik's cube avec le Meca500 (ou dans RoboDK).")
    parser.add_argument("cubestring", nargs="?", help="54 lettres U R F D L B (ordre des faces U R F D L B)")
    parser.add_argument("--exemple", action="store_true", help="utilise un cube mélangé d'exemple")
    parser.add_argument("--melange", type=int, metavar="N", help="cube mélangé au hasard de N coups")
    parser.add_argument("--graine", type=int, help="graine du mélange au hasard (reproductible)")
    parser.add_argument("--sans-robot", action="store_true", help="calcule et affiche, sans bouger le robot")
    parser.add_argument("--presenter-faces", action="store_true",
                        help="scanne les 6 faces puis résout le cube avec le robot")
    parser.add_argument("--simulation", action="store_true", help="joue la solution dans RoboDK (cube fictif)")
    parser.add_argument("--collisions", action="store_true", help="simulation : teste les collisions")
    parser.add_argument("--comparer", action="store_true", help="durée estimée avant / après optimisation")
    args = parser.parse_args(argv)

    if args.presenter_faces:
        if args.cubestring or args.exemple or args.sans_robot:
            parser.error("--presenter-faces ne se combine pas avec un cubestring, --exemple ou --sans-robot")
        return presenter_et_resoudre()

    melange = None
    if args.melange:
        rnd = random.Random(args.graine)
        melange = [(rnd.choice("URFDLB"), rnd.choice((1, -1, 2))) for _ in range(args.melange)]
        modele = ModeleCube()
        for f, k in melange:
            modele.coup(f, k)
        cubestring = modele.facelets()
        print("Mélange au hasard : %s" % resolution.ecrire(melange))
    else:
        cubestring = EXEMPLE if args.exemple else args.cubestring
    if not cubestring:
        parser.error("donne un cubestring (ou --exemple, ou --melange N)")

    try:
        debut = time.time()
        coups, etapes = resolution.meilleure_solution(cubestring)
        afficher_plan(coups, etapes, time.time() - debut, detail=not args.simulation)  # la simulation les affiche
        if args.comparer:
            comparer(cubestring, coups, etapes)
    except resolution.ErreurResolution as e:
        print("Erreur :", e)
        return 1
    if args.simulation:
        return simuler(coups, etapes, melange or inverse(coups), args.collisions)
    if args.sans_robot or args.comparer or not etapes:
        return 0

    if not confirmer_execution():
        return 0
    robot = rubiks.connecter()
    try:
        executer_etapes(robot, etapes)
    finally:
        rubiks.deconnecter(robot)
    return 0


def calculer_etapes(cubestring):
    debut = time.time()
    coups = resolution.calculer_solution(cubestring)
    etapes = resolution.plan_robot(coups)
    print("Solution (%d coups, calculée en %.1f s) : %s" %
          (len(coups), time.time() - debut, resolution.ecrire(coups)))
    print("Mouvements du robot : %d" % len(etapes))
    for i, etape in enumerate(etapes, 1):
        print("  %2d. %s" % (i, resolution.decrire(etape)))
    return etapes


def confirmer_execution():
    print("\nCube dans le socle comme décrit (U dessus, F vers le robot) ? Main sur l'arrêt d'urgence.")
    if input("Entrée pour lancer, autre chose pour annuler : ").strip():
        print("Annulé.")
        return False
    return True


def confirmer_demarrage():
    print("\nVérifie que le cube est dans le socle et que l'arrêt d'urgence est à portée.")
    if input("Entrée pour lancer le scan complet, autre chose pour annuler : ").strip():
        print("Annulé.")
        return False
    return True


def executer_etapes(robot, etapes):
    debut = time.time()
    resolution.executer(robot, etapes)
    robot.WaitIdle(120)
    print("Cube résolu en %s (estimé : %s)." %
          (minutes(time.time() - debut), minutes(resolution.duree_plan(etapes))))


def presenter_et_resoudre():
    try:
        resolution.charger_solveur()
    except resolution.ErreurResolution as e:
        print("Erreur :", e)
        return 1

    try:
        selection_camera = choisir_camera()
    except (ImportError, ErreurCamera) as e:
        print("Erreur caméra :", e)
        return 1

    facteur_vitesse = demander_facteur_vitesse(rubiks.VITESSE_GLOBALE)
    print("Vitesse sélectionnée : %g%% des limites R3." % (facteur_vitesse * 100))
    if not confirmer_demarrage():
        return 0

    robot = rubiks.connecter(facteur_vitesse=facteur_vitesse)
    try:
        rubiks.presenter_faces(robot, selection_camera)
        try:
            cubestring = resolution.verifier_cubestring(
                CUBESTRING_PATH.read_text(encoding="utf-8"))
        except OSError as e:
            print("Impossible de lire %s :" % CUBESTRING_PATH, e)
            return 1
        except resolution.ErreurResolution as e:
            print("Erreur :", e)
            return 1

        try:
            etapes = calculer_etapes(cubestring)
        except resolution.ErreurResolution as e:
            print("Erreur :", e)
            return 1
        if not etapes or not confirmer_execution():
            return 0

        executer_etapes(robot, etapes)
        return 0
    finally:
        rubiks.deconnecter(robot)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
