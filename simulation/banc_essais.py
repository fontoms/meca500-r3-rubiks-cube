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
    with open(os.path.join(P.DOSSIER_JOURNAL, "collisions.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    return bilan


# ----------------------------- MODE "resolution" -----------------------------

def appliquer(modele, etape):
    """Effet d'une étape du plan (resolution.py) sur le modèle du cube."""
    nom, a, _ = etape
    if nom == "basculer":
        modele.tourner(rot_quart(0, a))
    elif nom == "tourner_cube":
        modele.tourner(rot_quart(2, a // 90))
    elif nom == "tourner_haut":                      # les 2 couches du haut
        modele.tourner(rot_quart(2, a // 90), lambda p: p[2] >= 0)
    # tourner_pince : pince ouverte, en l'air, le cube ne bouge pas


def jouer(robot, modele, etape):
    """Une étape du plan de resolution.py, jouée par le robot et appliquée au modèle du cube."""
    nom, a, prise = etape
    resolution.MOUVEMENTS_ROBOT[nom](robot, a, prise)
    appliquer(modele, etape)


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
    """(coups, étapes, source) : P.SOLUTION si renseignée, sinon le solveur twophase (comme sur le vrai
    robot, à partir du cubestring du modèle), sinon l'inverse du mélange."""
    if P.SOLUTION.strip():
        coups = lire_coups(P.SOLUTION)
        return coups, resolution.plan_robot(coups), "paramètre SOLUTION"
    try:
        coups, etapes = resolution.meilleure_solution(modele.facelets())
        return coups, etapes, "solveur twophase (cubestring du cube simulé)"
    except resolution.ErreurResolution as e:
        coups = inverse(melange)
        return coups, resolution.plan_robot(coups), "inverse du mélange (%s)" % e


def melange_aleatoire(n, graine=None):
    rnd = random.Random(graine)
    return [(rnd.choice("UDFBLR"), rnd.choice((1, -1, 2))) for _ in range(n)]


def resoudre_en_simulation(melange, coups=None, etapes=None, collisions=False, afficher=log):
    """Cube fictif mélangé par `melange`, résolu dans RoboDK par le VRAI code du robot.

    coups / etapes : solution déjà calculée (sinon : trouver_solution). Après chaque mouvement, on vérifie
    que le cube de RoboDK suit le modèle du cube. collisions=True : chaque déplacement est testé
    (collisions, atteignabilité) au lieu d'être animé.
    Renvoie (cube résolu ?, durée estimée du vrai robot en s, problèmes de collision).
    """
    import simulateur
    modele = preparer_scene(melange)
    if etapes is None:
        coups, etapes, source = trouver_solution(modele, melange)
        afficher("Solution (%s) :" % source)
    afficher("Mélange  : %s" % (ecrire_coups(melange) or "(aucun)"))
    afficher("Cubestring : %s" % modele.facelets())
    afficher("Solution (%d coups) : %s" % (len(coups), ecrire_coups(coups)))
    duree = resolution.duree_plan(etapes)
    afficher("Robot : %d prises, %d étapes, durée estimée %.0f s (%d min %02d s)"
             % (resolution.nombre_de_prises(etapes), len(etapes), duree, duree // 60, duree % 60))

    robot = simulateur.RobotSimule(collisions=collisions)
    RDK.setSimulationSpeed(P.VITESSE_SIMULATION)
    try:
        rubiks.preparer(robot)
        for i, etape in enumerate(etapes):
            afficher("  %2d/%d  %s" % (i + 1, len(etapes), resolution.decrire(etape)))
            jouer(robot, modele, etape)
            ecart = ecart_simulation_modele(modele)
            if ecart > 2.0:
                raise RuntimeError("le cube simulé ne suit pas le modèle après le mouvement %d (écart %.1f mm)"
                                   % (i + 1, ecart))
    finally:
        robot.fermer()
    resolu = modele.resolu()
    afficher("%s après %d coups." % ("Cube RÉSOLU" if resolu else "Séquence terminée (cube NON résolu)", len(coups)))
    for etape, objets in robot.collisions:
        afficher("  COLLISION %s : %s" % (etape, ", ".join(objets)))
    return resolu, duree, robot.collisions


def mode_resolution():
    if isinstance(P.MELANGE, int):
        melange = melange_aleatoire(P.MELANGE, P.GRAINE_ALEATOIRE)
    else:
        melange = lire_coups(P.MELANGE)
    return resoudre_en_simulation(melange, collisions=False)
