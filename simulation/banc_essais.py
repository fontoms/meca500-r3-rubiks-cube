# -*- coding: utf-8 -*-
"""
Banc d'essais RoboDK, sur les VRAIS mouvements de ../meca500_rubiks/ (pas de trajectoires à part) :

  MODE "tests"      : rejoue les mouvements de P.TESTS en testant chaque déplacement
                      (collisions robot / pince / doigts / socle / table / cube, atteignabilité) ;
                      bilan dans journal/collisions.txt.
  MODE "resolution" : résout un cube mélangé exactement comme le vrai robot (resoudre_cube.py) :
                      solveur twophase + plan de meca500_rubiks/resolution.py, en vérifiant après
                      chaque mouvement que le cube simulé suit le modèle.
"""
import os
import random
import time

from robodk import robolink

import parametres as P                         # (ajoute le dossier du projet au chemin)
import meca500_rubiks as rubiks                # noqa: E402
from meca500_rubiks import resolution          # noqa: E402
from connexion_robodk import RDK
from construction import construire_pince, construire_socle_et_cube, obtenir_robot, pose_cubie
from journalisation import log
from modele_cube import ModeleCube, ecrire_coups, inverse, lire_coups, rot_quart


# ----------------------------- Préparation de la scène -----------------------------

def preparer_scene(melange):
    """(Re)construit socle, cube (mélangé selon `melange`) et pince ; robot en position d'attente.
    Renvoie le modèle logiciel du cube."""
    robot = obtenir_robot()
    RDK.Render(False)
    repere, socle, cubies = construire_socle_et_cube(robot)
    construire_pince(robot)
    modele = ModeleCube()
    for f, k in melange:
        modele.coup(f, k)
    for p0, (p, R) in modele.c.items():
        cubies[p0].setPose(pose_cubie(p, R))
    RDK.Render(True)

    import simulateur
    simule = simulateur.RobotSimule()
    try:
        rubiks.preparer(simule)                      # SetTrf, pince ouverte, position d'attente
    finally:
        simule.fermer()
    return modele


# ----------------------------- MODE "tests" -----------------------------

def mode_tests():
    """Chaque mouvement de P.TESTS, testé (collisions + atteignabilité) à partir d'un cube neuf."""
    import simulateur
    lignes = []
    bilan = []
    for nom in P.TESTS:
        preparer_scene([])
        RDK.ShowMessage("Test des collisions : " + nom, False)
        lignes.append("=== %s" % nom)
        try:
            problemes = simulateur.tester_collisions(nom)
        except Exception as e:                       # noqa: BLE001  (on veut le bilan complet)
            problemes = [("exception", [str(e)])]
        lignes += ["   %s : %s" % (etape, ", ".join(objets)) for etape, objets in problemes]
        bilan.append((nom, "OK" if not problemes else "%d PROBLÈME(S)" % len(problemes)))
        time.sleep(P.PAUSE_ENTRE_TESTS)
    preparer_scene([])

    lignes += ["", "Bilan des collisions :"] + ["%-22s %s" % (n, e) for n, e in bilan]
    for ligne in lignes:
        log(ligne)
    os.makedirs(P.DOSSIER_JOURNAL, exist_ok=True)
    with open(os.path.join(P.DOSSIER_JOURNAL, "collisions.txt"), "w") as f:
        f.write("\n".join(lignes) + "\n")
    return bilan


# ----------------------------- MODE "resolution" -----------------------------

def jouer(robot, modele, etape):
    """Une étape du plan de resolution.py, jouée par le robot et appliquée au modèle du cube."""
    nom, a = etape
    resolution.MOUVEMENTS_ROBOT[nom](robot, a)
    if nom == "basculer":
        modele.tourner(rot_quart(0, a))
    elif nom == "tourner_cube":
        modele.tourner(rot_quart(2, a // 90))
    else:                                            # tourner_haut : les 2 couches du haut
        modele.tourner(rot_quart(2, a // 90), lambda p: p[2] >= 0)


def ecart_simulation_modele(modele):
    """Écart maximal (mm) entre la position des cubies dans RoboDK et le modèle."""
    pire = 0.0
    for p0, (p, R) in modele.c.items():
        att = pose_cubie(p, R)
        reel = RDK.Item("Cubie_%+d%+d%+d" % p0, robolink.ITEM_TYPE_OBJECT).Pose()
        pire = max(pire, max(abs(reel[i, j] - att[i, j]) * (1 if j == 3 else P.S)
                             for i in range(3) for j in range(4)))
    return pire


def trouver_solution(modele, melange):
    """Solution du cube mélangé : P.SOLUTION si renseignée, sinon le solveur twophase (comme sur le vrai
    robot, à partir du cubestring du modèle), sinon l'inverse du mélange."""
    if P.SOLUTION.strip():
        return lire_coups(P.SOLUTION), "paramètre SOLUTION"
    try:
        return resolution.calculer_solution(modele.facelets()), "solveur twophase (cubestring du cube simulé)"
    except resolution.ErreurResolution as e:
        return inverse(melange), "inverse du mélange (%s)" % e


def mode_resolution():
    import simulateur
    if P.GRAINE_ALEATOIRE is not None:
        random.seed(P.GRAINE_ALEATOIRE)
    if isinstance(P.MELANGE, int):
        melange = [(random.choice("UDFBLR"), random.choice((1, -1, 2))) for _ in range(P.MELANGE)]
    else:
        melange = lire_coups(P.MELANGE)
    modele = preparer_scene(melange)
    solution, source = trouver_solution(modele, melange)
    log("Mélange  :", ecrire_coups(melange))
    log("Facelets :", modele.facelets())
    log("Solution (%s, %d coups) : %s" % (source, len(solution), ecrire_coups(solution)))

    robot = simulateur.RobotSimule()
    RDK.setSimulationSpeed(P.VITESSE_SIMULATION)
    etapes = resolution.plan_robot(solution)
    log("Mouvements du robot : %d" % len(etapes))
    try:
        rubiks.preparer(robot)
        for i, etape in enumerate(etapes):
            log("mouvement %d/%d : %s" % (i + 1, len(etapes), resolution.decrire(etape)))
            jouer(robot, modele, etape)
            ecart = ecart_simulation_modele(modele)
            if ecart > 2.0:
                raise RuntimeError("le cube simulé ne suit pas le modèle après le mouvement %d (écart %.1f mm)"
                                   % (i + 1, ecart))
    finally:
        robot.fermer()
    log("%s après %d coups." % ("Cube RÉSOLU" if modele.resolu() else "Séquence terminée (cube non résolu)",
                                len(solution)))
    return modele
