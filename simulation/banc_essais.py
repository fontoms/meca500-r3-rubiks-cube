# -*- coding: utf-8 -*-
"""
Banc d'essais RoboDK : mouvements testés avec détection de collisions (MODE "tests")
et résolution complète d'un cube mélangé (MODE "resolution").

ATTENTION : la classe Cellule a ses PROPRES trajectoires (prise_repose, bascule, rotation_cube,
tourner_couche). Elles reproduisent celles de ../meca500_rubiks/ mais n'en sont pas issues :
une modification de meca500_rubiks ne se répercute pas ici. Pour voir exactement ce que fera
le robot, utilise les programmes de la station (simulateur.py) et verifier.py.
"""
import random
import time

from robodk import robolink
from robodk.robomath import pi, rotx, rotz, transl

import parametres as P
from connexion_robodk import RDK
from construction import construire_pince, construire_socle_et_cube, obtenir_robot, pose_cubie
from journalisation import log
from modele_cube import ModeleCube, chemin_vers_bas, ecrire_coups, inverse, lire_coups, rot_quart


def pose_outil(z, bascule_deg=0.0, rot_deg=0.0):
    """TCP sur l'axe du cube à la hauteur z (repère socle), pince verticale, doigts sur les faces ±X.
    bascule_deg : rotation autour de l'axe des doigts (X du socle) ; rot_deg : rotation autour de Z."""
    return transl(0, 0, z) * rotx(bascule_deg * pi / 180) * rotz(rot_deg * pi / 180) * rotz(pi / 2) * rotx(pi)


class Cellule:
    """Robot + pince + cube de la station, avec un modèle logiciel du cube tenu à jour."""

    def __init__(self, robot, repere, socle, outil, pieces, doigts, cubies, modele):
        self.robot, self.repere, self.socle, self.outil = robot, repere, socle, outil
        self.pieces, self.doigts, self.cubies, self.m = pieces, doigts, cubies, modele
        self.fermee = False
        self.tenus = []
        self.j_home = None
        self.nb = {"bascule": 0, "rotation": 0, "couche": 0}
        self.collisions = []            # (segment, objets) détectés
        self.segment = ""

    # --- collisions ---
    def preparer_collisions(self):
        if not P.VERIFIER_COLLISIONS:
            return
        RDK.setCollisionActive(robolink.COLLISION_ON)
        cub = list(self.cubies.values())
        a, b = [], []
        for i in range(len(cub)):                     # cubies entre eux : toujours en contact
            for k in range(i + 1, len(cub)):
                a.append(cub[i])
                b.append(cub[k])
        for i in range(len(self.pieces)):             # pièces de la pince entre elles
            for k in range(i + 1, len(self.pieces)):
                a.append(self.pieces[i])
                b.append(self.pieces[k])
        RDK.setCollisionActivePairList([robolink.COLLISION_OFF] * len(a), a, b)
        for p in self.pieces:                          # pince fixée sur la bride
            for lien in range(7):
                RDK.setCollisionActivePair(robolink.COLLISION_OFF, self.robot, p, lien, 0)
        n = RDK.Collisions()
        if n:
            log("Attention : %d collision(s) dès le départ :" % n,
                ", ".join(it.Name() for it in RDK.CollisionItems()))

    def _paires_tenues(self, etat):
        if not P.VERIFIER_COLLISIONS or not self.tenus:
            return
        a, b = [], []
        for p0 in self.tenus:
            for p in self.pieces:
                a.append(p)
                b.append(self.cubies[p0])
        RDK.setCollisionActivePairList([etat] * len(a), a, b)

    def _tester(self, res):
        if res == -2:
            raise RuntimeError("position inaccessible (%s)" % self.segment)
        if res == -1:
            raise RuntimeError("mouvement linéaire impossible (%s)" % self.segment)
        if res > 0:
            noms = sorted(set(it.Name() for it in RDK.CollisionItems()))
            self.collisions.append((self.segment, noms))
            log("   COLLISION pendant « %s » : %s" % (self.segment, ", ".join(noms)))

    def _ik(self, pose):
        bride = self.repere.Pose() * pose * transl(0, 0, -P.TCP_Z)
        j = self.robot.SolveIK(bride, self.robot.Joints()).list()
        if len(j) < 6:
            raise RuntimeError("position inaccessible (%s)" % self.segment)
        return j[:6]

    # --- déplacements (testés, puis exécutés) ---
    def J(self, nom, cible):
        """Mouvement articulaire vers une pose (Mat) ou des joints (liste)."""
        self.segment = nom
        j1 = self.robot.Joints().list()
        j2 = list(cible) if isinstance(cible, (list, tuple)) else self._ik(cible)
        if P.VERIFIER_COLLISIONS:
            self._tester(self.robot.MoveJ_Test(j1, j2, 2))
            self.robot.setJoints(j1)
        self.robot.MoveJ(j2)

    def L(self, nom, pose):
        """Mouvement linéaire du TCP vers une pose (repère socle)."""
        self.segment = nom
        j1 = self.robot.Joints().list()
        if P.VERIFIER_COLLISIONS:
            self._tester(self.robot.MoveL_Test(j1, pose, 2))
            self.robot.setJoints(j1)
        self.robot.MoveL(pose)

    def LouJ(self, nom, pose):
        """Rotation autour du centre du cube : linéaire si possible, sinon articulaire."""
        j1 = self.robot.Joints().list()
        res = self.robot.MoveL_Test(j1, pose)
        self.robot.setJoints(j1)
        if res in (-1, -2):
            return self.J(nom, pose)
        return self.L(nom, pose)

    def home(self):
        self.J("retour position d'attente", self.j_home)

    def j6(self, rot_deg, z):
        """Joints actuels avec seulement J6 tourné pour atteindre pose_outil(z, rot=rot_deg)."""
        cible = self.repere.Pose() * pose_outil(z, 0, rot_deg) * transl(0, 0, -P.TCP_Z)
        j = self.robot.Joints().list()[:6]
        sols = []
        for d in (rot_deg, -rot_deg):
            jj = j[:]
            jj[5] += d
            fk = self.robot.SolveFK(jj)
            if max(abs(fk[i, k] - cible[i, k]) for i in range(3) for k in range(4)) < 0.5:
                sols.append(jj)
        if not sols:
            raise RuntimeError("Rotation J6 introuvable")
        return min(sols, key=lambda jj: abs(jj[5]))

    # --- pince ---
    def _doigts(self, fermer):
        if self.fermee == fermer:
            return
        for d, sg in self.doigts:
            d.setPose(d.Pose() * transl(0, (-sg if fermer else sg) * P.SERRAGE, 0))
        self.fermee = fermer

    def ouvrir_vide(self):
        self._doigts(False)

    def fermer(self, filtre):
        self._doigts(True)
        self.tenus = [p0 for p0, (p, R) in self.m.c.items() if filtre(p)]
        self._paires_tenues(robolink.COLLISION_OFF)
        for p0 in self.tenus:
            self.cubies[p0].setParentStatic(self.outil)
        self.robot.Pause(200)

    def ouvrir(self):
        self._doigts(False)
        for p0 in self.tenus:
            self.cubies[p0].setParentStatic(self.repere)
        self.verifier(self.tenus)
        self._paires_tenues(robolink.COLLISION_ON)
        self.tenus = []
        self.robot.Pause(200)

    def verifier(self, liste):
        """Compare la position des cubies dans RoboDK au modèle, puis les recale exactement."""
        pire = 0.0
        for p0 in liste:
            p, R = self.m.c[p0]
            att = pose_cubie(p, R)
            reel = self.cubies[p0].Pose()
            ecart = max(abs(reel[i, j] - att[i, j]) * (1 if j == 3 else P.S) for i in range(3) for j in range(4))
            pire = max(pire, ecart)
            self.cubies[p0].setPose(att)
        if pire > 2.0:
            raise RuntimeError("Le cube simulé ne correspond plus au modèle (écart %.1f mm)" % pire)

    def annuler(self):
        """Après un mouvement impossible : lâche le cube à sa place (modèle) et revient en attente."""
        self._doigts(False)
        for p0 in self.tenus:
            self.cubies[p0].setParentStatic(self.repere)
            self.cubies[p0].setPose(pose_cubie(*self.m.c[p0]))
        self._paires_tenues(robolink.COLLISION_ON)
        self.tenus = []
        self.robot.setJoints(self.j_home)

    def prendre(self, z, filtre, quoi):
        self.home()
        self.ouvrir_vide()
        self.L("descente sur " + quoi, pose_outil(z))
        self.fermer(filtre)

    # --- mouvements de base ---
    def prise_repose(self):
        self.prendre(P.Z_PRISE, lambda p: True, "le cube")
        self.L("sortie du socle", pose_outil(P.Z_PRISE + P.LEVEE))
        self.L("retour dans le socle", pose_outil(P.Z_PRISE))
        self.ouvrir()
        self.L("dégagement vertical", pose_outil(P.Z_APPROCHE))
        self.home()

    def bascule(self, s):
        """Quart de tour autour de X : pince de -45°·s à +45°·s, jamais couchée."""
        a0, a1 = -P.ANGLE_PRISE_BASCULE * s, P.ANGLE_PRISE_BASCULE * s

        def penchee(z, a, recul=0.0):
            return pose_outil(z, a) * transl(0, 0, -(P.DECALAGE_BASCULE + recul))

        self.home()
        self.ouvrir_vide()
        self.LouJ("approche inclinée %+.0f°" % a0, penchee(P.Z_PRISE, a0, P.RECUL_BASCULE))
        self.L("descente le long de l'axe de la pince", penchee(P.Z_PRISE, a0))
        self.fermer(lambda p: True)
        self.L("sortie du socle", penchee(P.Z_PRISE + P.LEVEE, a0))
        self.LouJ("bascule %+.0f° → %+.0f°" % (a0, a1), penchee(P.Z_PRISE + P.LEVEE, a1))
        self.L("retour dans le socle", penchee(P.Z_PRISE, a1))
        self.m.tourner(rot_quart(0, s))
        self.ouvrir()
        self.L("dégagement le long de l'axe de la pince", penchee(P.Z_PRISE, a1, P.RECUL_BASCULE))
        self.LouJ("redressement de la pince", pose_outil(P.Z_APPROCHE))
        self.home()
        self.nb["bascule"] += 1

    def rotation_cube(self, q):
        self.prendre(P.Z_PRISE, lambda p: True, "le cube")
        self.L("sortie du socle", pose_outil(P.Z_PRISE + P.LEVEE))
        self.J("rotation du cube %+d°" % (90 * q), self.j6(90 * q, P.Z_PRISE + P.LEVEE))
        self.L("retour dans le socle", pose_outil(P.Z_PRISE, 0, 90 * q))
        self.m.tourner(rot_quart(2, q))
        self.ouvrir()
        self.L("dégagement vertical", pose_outil(P.Z_APPROCHE, 0, 90 * q))
        self.home()
        self.nb["rotation"] += 1

    def tourner_couche(self, q):
        """Tourne les 2 couches du haut de q×90° (autour de +Z) ; le socle tient la couche du bas."""
        self.prendre(P.Z_PRISE_HAUT, lambda p: p[2] >= 0, "les 2 couches du haut")
        self.J("rotation couche %+d°" % (90 * q), self.j6(90 * q, P.Z_PRISE_HAUT))
        self.m.tourner(rot_quart(2, q), lambda p: p[2] >= 0)
        self.ouvrir()
        self.L("dégagement vertical", pose_outil(P.Z_APPROCHE, 0, 90 * q))
        self.home()
        self.nb["couche"] += 1

    def executer_test(self, nom):
        if nom == "prise":
            return self.prise_repose()
        for prefixe, fct in (("rotation", self.rotation_cube), ("couche", self.tourner_couche),
                             ("bascule", self.bascule)):
            if nom.startswith(prefixe):
                angle = int(nom[len(prefixe):])
                if angle % 90 or not -180 <= angle <= 180 or angle == 0 or (prefixe == "bascule" and abs(angle) != 90):
                    break
                return fct(angle // 90)
        raise ValueError("Test inconnu : %s" % nom)

    # --- un coup de notation standard (MODE resolution) ---
    def jouer(self, face, k):
        for op, arg in chemin_vers_bas(self.m.centre(face)):
            if op == "B":
                self.bascule(arg)
            else:
                self.rotation_cube(arg)
        # Face en bas : la tourner de k quarts (sens horaire vu de dessous) revient,
        # à l'orientation près, à tourner les 2 couches du haut de -k quarts autour de +Z.
        self.tourner_couche(2 if k == 2 else -k)


# ----------------------------- Préparation de la scène -----------------------------

def preparer_scene(melange):
    """(Re)construit socle, cube (mélangé selon `melange`) et pince ; robot en position d'attente."""
    robot = obtenir_robot()
    RDK.Render(False)
    repere, socle, cubies = construire_socle_et_cube(robot)
    outil, pieces, doigts = construire_pince(robot)
    modele = ModeleCube()
    for f, k in melange:
        modele.coup(f, k)
    for p0, (p, R) in modele.c.items():
        cubies[p0].setPose(pose_cubie(p, R))
    RDK.Render(True)

    robot.setPoseFrame(repere)
    robot.setPoseTool(outil)
    robot.setSpeed(P.VITESSE_LIN, P.VITESSE_ART)
    cell = Cellule(robot, repere, socle, outil, pieces, doigts, cubies, modele)
    cell.preparer_collisions()
    cell.segment = "approche"
    cell.j_home = cell._ik(pose_outil(P.Z_APPROCHE))
    robot.MoveJ(cell.j_home)
    return cell


# ----------------------------- Modes -----------------------------

def mode_tests():
    cell = preparer_scene([])
    log("TCP_Z = %.1f mm | doigts : bout à %.0f mm du bas du cube, extension à %.0f mm au-dessus"
        % (P.TCP_Z, P.GARDE_BAS, P.GARDE_HAUT))
    bilan = []
    for nom in P.TESTS:
        RDK.ShowMessage("Test : " + nom, False)
        log("=== Test « %s »" % nom)
        cell.collisions = []
        try:
            cell.executer_test(nom)
            etat = "OK" if not cell.collisions else "COLLISION"
        except Exception as e:
            etat = "IMPOSSIBLE : %s" % e
            log("   " + etat)
            cell.annuler()
        bilan.append((nom, etat))
        time.sleep(P.PAUSE_ENTRE_TESTS)

    log("\n".join(["Bilan :"] + ["%-12s %s" % (n, e) for n, e in bilan]))
    return cell, bilan


def trouver_solution(modele, melange):
    if P.SOLUTION.strip():
        return lire_coups(P.SOLUTION), "paramètre SOLUTION"
    try:
        import kociemba
        return lire_coups(kociemba.solve(modele.facelets())), "solveur kociemba"
    except ImportError:
        return inverse(melange), "inverse du mélange (kociemba non installé)"


def mode_resolution():
    if P.GRAINE_ALEATOIRE is not None:
        random.seed(P.GRAINE_ALEATOIRE)
    if isinstance(P.MELANGE, int):
        melange = [(random.choice("UDFBLR"), random.choice((1, -1, 2))) for _ in range(P.MELANGE)]
    else:
        melange = lire_coups(P.MELANGE)
    cell = preparer_scene(melange)
    modele = cell.m
    solution, source = trouver_solution(modele, melange)
    log("Mélange  :", ecrire_coups(melange))
    log("Facelets :", modele.facelets())
    log("Solution (%s, %d coups) : %s" % (source, len(solution), ecrire_coups(solution)))

    attendu = modele.copie()          # référence : coups appliqués directement au modèle
    for i, (f, k) in enumerate(solution):
        log("coup %d/%d : %s" % (i + 1, len(solution), ecrire_coups([(f, k)])))
        cell.jouer(f, k)
        attendu.coup(f, k)
        if not cell.m.egal(attendu):
            raise RuntimeError("état du cube incorrect après le coup %d" % (i + 1))
    log("%s après %d coups (%d bascules, %d rotations, %d couches tournées)." % (
        "Cube RÉSOLU" if modele.resolu() else "Séquence terminée (cube non résolu)",
        len(solution), cell.nb["bascule"], cell.nb["rotation"], cell.nb["couche"]))
    return cell
