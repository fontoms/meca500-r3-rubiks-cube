# -*- coding: utf-8 -*-
"""
Exécute le code du robot (../meca500_rubiks/) dans la simulation RoboDK.

RobotSimule imite les commandes mecademicpy utilisées par meca500_rubiks
(MoveLin, MovePose, GripperOpen…) et les joue sur le Meca500 de la station.
Ainsi, ce que montre RoboDK est exactement ce que fera le vrai robot.

Utilisé par les programmes de la station (un par mouvement) :
    simulateur.simuler("tourner_cube_gauche")
ou depuis PyCharm / un terminal, RoboDK ouvert avec la station :
    python simulation/simulateur.py tourner_cube_gauche
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import parametres as P                          # noqa: E402  dimensions de la scène
import meca500_rubiks as rubiks                 # noqa: E402  le code du robot
from connexion_robodk import RDK                # noqa: E402

from robodk.robolink import (COLLISION_OFF, COLLISION_ON, ITEM_TYPE_FRAME, ITEM_TYPE_OBJECT,  # noqa: E402
                             ITEM_TYPE_ROBOT, ITEM_TYPE_TOOL)
from robodk.robomath import Mat, TxyzRxyz_2_Pose, pi, pose_2_quaternion, quaternion_2_pose  # noqa: E402
import math  # noqa: E402

from verifier import _slerp  # noqa: E402

from construction import pose_doigt, pose_tcp  # noqa: E402


def _pose(x, y, z, alpha, beta, gamma):
    """Pose Mecademic (mm, degrés, Rx·Ry·Rz) → matrice RoboDK."""
    return TxyzRxyz_2_Pose([x, y, z, alpha * pi / 180, beta * pi / 180, gamma * pi / 180])


class RobotSimule:
    """Faux robot mecademicpy : joue les commandes sur le Meca500 de la station RoboDK.

    collisions=True : chaque déplacement est d'abord testé (MoveL_Test / MoveJ_Test) avec la
    détection de collisions de RoboDK (robot, pince, doigts, socle, table, caméra, cube), puis
    le robot est placé directement à l'arrivée (pas d'animation). Bilan : self.collisions.
    """

    def __init__(self, collisions=False):
        self.robot = RDK.Item("", ITEM_TYPE_ROBOT)
        self.socle = RDK.Item(P.NOM_REPERE, ITEM_TYPE_FRAME)
        self.table = RDK.Item(P.NOM_REPERE_TABLE, ITEM_TYPE_FRAME)
        self.outil = RDK.Item(P.NOM_OUTIL, ITEM_TYPE_TOOL)
        self.doigts = [(RDK.Item("Doigt_1", ITEM_TYPE_OBJECT), 1), (RDK.Item("Doigt_2", ITEM_TYPE_OBJECT), 2)]
        self.pieces = [RDK.Item("Pince", ITEM_TYPE_OBJECT)] + [d for d, _ in self.doigts]
        self.cubies = [it for it in RDK.ItemList(ITEM_TYPE_OBJECT) if it.Name().startswith("Cubie_")]
        if not (self.robot.Valid() and self.socle.Valid() and self.table.Valid() and self.outil.Valid()
                and all(p.Valid() for p in self.pieces) and len(self.cubies) == 26):
            raise RuntimeError("Scène incomplète : lance « remise_a_zero » (ou Tools > Run Script > 00_Rubiks_Meca500).")

        self.robot.setPoseFrame(self.robot.Parent())     # MoveLin : repère de base du robot
        self.robot.setPoseTool(self.outil)
        self.robot.setSpeed(P.VITESSE_LIN, P.VITESSE_ART, P.ACCEL_LIN, P.ACCEL_ART)
        self.tenus = []
        self._placer_doigts(0.0)                          # pince ouverte
        self.journal = open(os.path.join(P.DOSSIER_JOURNAL, "dernier_mouvement.txt"), "w", encoding="utf-8")
        self.verifier_collisions = collisions
        self.collisions = []                              # [(commande, [objets en collision])]
        self.etape = ""
        if collisions:
            self._preparer_collisions()

    def fermer(self):
        self.journal.close()
        if self.verifier_collisions:
            RDK.setCollisionActive(COLLISION_OFF)

    def _noter(self, texte):
        self.etape = texte
        self.journal.write("%s  %s\n" % (time.strftime("%H:%M:%S"), texte))
        self.journal.flush()

    # ---------------- collisions ----------------
    def _preparer_collisions(self):
        """Active la détection de collisions, paire par paire (RoboDK ne teste pas par défaut les
        pièces fixées à un outil) : pince + doigts + robot + cube contre socle, table, caméra, cube."""
        RDK.setCollisionActive(COLLISION_ON)
        fixes = [RDK.Item(n, ITEM_TYPE_OBJECT) for n in ("Socle", "Table", "Camera")]
        fixes = [f for f in fixes if f.Valid()]
        table = RDK.Item("Table", ITEM_TYPE_OBJECT)
        etats, a, b, ia, ib = [], [], [], [], []

        def paire(etat, x, y, idx=0, idy=0):
            etats.append(etat)
            a.append(x)
            b.append(y)
            ia.append(idx)
            ib.append(idy)
        for p in self.pieces:                             # pince et doigts
            for f in fixes + self.cubies:
                paire(COLLISION_ON, p, f)
            for p2 in self.pieces:                        # pièces vissées entre elles
                if p2 is not p:
                    paire(COLLISION_OFF, p, p2)
            for lien in range(7):                         # pince vissée sur la bride
                paire(COLLISION_OFF, self.robot, p, lien, 0)
        for lien in range(7):                             # bras du robot
            for f in fixes + self.cubies:
                base_sur_table = lien == 0 and f == table
                paire(COLLISION_OFF if base_sur_table else COLLISION_ON, self.robot, f, lien, 0)
        for i, c in enumerate(self.cubies):
            for f in fixes:
                paire(COLLISION_ON, c, f)
            for c2 in self.cubies[i + 1:]:                # cubies entre eux : toujours en contact
                paire(COLLISION_OFF, c, c2)
        for f in fixes:                                   # socle et caméra posés sur la table
            if f != table and table.Valid():
                paire(COLLISION_OFF, f, table)
        RDK.setCollisionActivePairList(etats, a, b, ia, ib)
        n = RDK.Collisions()
        if n:
            self.collisions.append(("au départ", sorted(set(it.Name() for it in RDK.CollisionItems()))))

    def _paires_tenues(self, etat):
        """Cubies tenus ↔ pince : en contact pendant la prise."""
        if not self.verifier_collisions or not self.tenus:
            return
        a = [p for c in self.tenus for p in self.pieces]
        b = [c for c in self.tenus for _ in self.pieces]
        RDK.setCollisionActivePairList([etat] * len(a), a, b)

    def _resultat(self, res):
        if res == -2:
            self.collisions.append((self.etape, ["position inaccessible"]))
        elif res == -1:
            self.collisions.append((self.etape, ["mouvement impossible (singularité / limites)"]))
        elif res > 0:
            self.collisions.append((self.etape, sorted(set(it.Name() for it in RDK.CollisionItems()))))

    def _joints_vers(self, pose):
        bride = pose * _pose(*self.trf).inv()
        j = self.robot.SolveIK(bride, self.robot.Joints()).list()
        return j[:6] if len(j) >= 6 else None

    def _joints_continus(self, j1, pose, pas=2.0):
        """Articulations à l'arrivée d'un MoveLin, en suivant le trajet par petits pas depuis j1
        (comme le vrai robot : même configuration du bras et du poignet)."""
        depart = self.robot.SolveFK(j1) * _pose(*self.trf)
        dist = max(abs(depart[i, 3] - pose[i, 3]) for i in range(3))
        q0, q1 = pose_2_quaternion(depart), pose_2_quaternion(pose)
        angle = 2 * math.degrees(math.acos(min(1.0, abs(sum(a * b for a, b in zip(q0, q1))))))
        n = max(1, int(math.ceil(max(dist, angle) / pas)))
        j = j1
        for k in range(1, n + 1):
            t = k / n
            m = quaternion_2_pose(_slerp(q0, q1, t))
            m.setPos([a + t * (b - a) for a, b in zip(depart.Pos(), pose.Pos())])
            jj = self.robot.SolveIK(m * _pose(*self.trf).inv(), j).list()
            if len(jj) < 6:
                break
            j = jj[:6]
        return j

    # ---------------- déplacements ----------------
    trf = P.TCP

    def MoveLin(self, *p):
        self._noter("MoveLin%s" % (p,))
        if not self.verifier_collisions:
            self.robot.MoveL(_pose(*p))
            return
        j1 = self.robot.Joints().list()[:6]
        res = self.robot.MoveL_Test(j1, _pose(*p), 1)
        self._resultat(res)
        if res < 0:                                  # trajet impossible : on saute à l'arrivée
            j2 = self._joints_vers(_pose(*p))
            self.robot.setJoints(j2 if j2 else j1)
        else:                                        # le test a suivi le trajet : on garde la configuration
            self.robot.setJoints(self._joints_continus(j1, _pose(*p)))

    def MovePose(self, *p):
        self._noter("MovePose%s" % (p,))
        if not self.verifier_collisions:
            self.robot.MoveJ(_pose(*p))
            return
        j1 = self.robot.Joints().list()[:6]
        j2 = self._joints_vers(_pose(*p))
        if j2 is None:
            self._resultat(-2)
            return
        self._resultat(self.robot.MoveJ_Test(j1, j2, 2))
        self.robot.setJoints(j2)

    def MoveJoints(self, *j):
        self._noter("MoveJoints%s" % (j,))
        self.robot.MoveJ(list(j))

    def _attendre(self, secondes):
        """Pause visible dans RoboDK (robot.Pause ne bloque pas quand on pilote le robot depuis Python)."""
        time.sleep(secondes / max(RDK.SimulationSpeed(), 1e-3))

    def Delay(self, secondes):
        if not self.verifier_collisions:
            self._attendre(secondes)

    capteur_pince = True        # comme le vrai robot (firmware ≥ 9.1) : briques.attendre_pince

    def WaitGripperMoveCompletion(self, timeout=None):
        from meca500_rubiks.duree import DUREE_PINCE_CAPTEUR
        self.Delay(DUREE_PINCE_CAPTEUR)

    # ---------------- pince ----------------
    def _placer_doigts(self, serrage):
        for doigt, numero in self.doigts:
            doigt.setPose(pose_tcp().inv() * pose_doigt(numero, serrage))

    def GripperClose(self):
        self._noter("GripperClose")
        self._placer_doigts(P.SERRAGE)
        self.tenus = self._cubies_entre_les_doigts()
        self._paires_tenues(COLLISION_OFF)
        for c in self.tenus:
            c.setParentStatic(self.outil)

    def GripperOpen(self):
        self._noter("GripperOpen")
        self._placer_doigts(0.0)
        support = self._support_sous_la_pince()
        for c in self.tenus:
            c.setParentStatic(support)
            self._recaler(c)
        self._paires_tenues(COLLISION_ON)
        self.tenus = []

    def _support_sous_la_pince(self):
        """Socle ou table : le repère le plus proche du TCP (à l'horizontale)."""
        tcp = self.robot.Pose()                   # TCP dans le repère de base (socle et table aussi)

        def distance(repere):
            p = repere.Pose()
            return (p[0, 3] - tcp[0, 3]) ** 2 + (p[1, 3] - tcp[1, 3]) ** 2
        return min((self.socle, self.table), key=distance)

    def _cubies_entre_les_doigts(self):
        """Cube entier si les patins tiennent le centre du cube (le cube vient en bloc) ;
        s'ils sont plus haut (tourner_haut), seulement les couches que touchent les patins."""
        if self._support_sous_la_pince() != self.socle:      # sur la table : toujours le cube entier
            return list(self.cubies)
        tcp = self.socle.Pose().inv() * self.robot.Pose()     # TCP dans le repère du socle
        axe_z = tcp[2, 2]                                     # -1 : outil vertical vers le bas
        bas_patins = tcp[2, 3] - P.DOIGT_SOUS_TCP
        if axe_z > -0.99 or bas_patins <= P.h:
            return list(self.cubies)
        return [c for c in self.cubies if c.Pose()[2, 3] + P.S / 2 > bas_patins]

    def _recaler(self, cubie):
        """Replace exactement le cubie sur la grille du cube (supprime les petites dérives)."""
        m = cubie.Pose()
        rot = [[float(round(m[i, j])) for j in range(3)] for i in range(3)]
        pos = [round(m[0, 3] / P.S) * P.S, round(m[1, 3] / P.S) * P.S,
               P.h + round((m[2, 3] - P.h) / P.S) * P.S]
        ecart = max(abs(m[i, 3] - pos[i]) for i in range(3))
        if ecart > 2.0:
            RDK.ShowMessage("Attention : le cube n'a pas été reposé à sa place (écart %.0f mm)" % ecart, False)
            if self.verifier_collisions:
                self.collisions.append((self.etape, ["cube mal reposé (écart %.0f mm)" % ecart]))
            return
        cubie.setPose(Mat([rot[0] + [pos[0]], rot[1] + [pos[1]], rot[2] + [pos[2]], [0, 0, 0, 1]]))

    # ---------------- photo (presenter_faces) ----------------
    def prendre_photo(self, face):
        """Appelé par meca500_rubiks.photographier : pas de caméra simulée, juste une pause et un message."""
        self._noter("Photo face %s" % face)
        if not self.verifier_collisions:
            RDK.ShowMessage("Photo : face « %s »" % face, False)
            self._attendre(P.PAUSE_PHOTO)

    # ---------------- commandes sans effet en simulation ----------------
    def _rien(self, *args, **kwargs):
        pass

    Connect = ActivateAndHome = WaitHomed = WaitIdle = DeactivateRobot = Disconnect = _rien
    SetBlending = SetCartLinVel = SetCartAngVel = SetJointVel = SetCartAcc = SetJointAcc = SetGripperVel = _rien

    def SetTrf(self, *p):
        self.trf = p
        self.outil.setPoseTool(_pose(*p))


def remise_a_zero():
    """Cube neuf dans le socle, robot en position d'attente."""
    from banc_essais import preparer_scene
    P.VERIFIER_COLLISIONS = False
    preparer_scene([])


def tester_collisions(nom):
    """Rejoue le mouvement `nom` (ou une fonction mouvement(robot)) en testant chaque déplacement
    (collisions, atteignabilité). Ne s'anime pas. Renvoie la liste [(commande, [objets])] des problèmes
    (vide = OK)."""
    mouvement = getattr(rubiks, nom) if isinstance(nom, str) else nom
    robot = RobotSimule(collisions=True)
    try:
        rubiks.preparer(robot)
        mouvement(robot)
    finally:
        robot.fermer()
    return robot.collisions


def simuler(nom):
    """Exécute le mouvement `nom` de meca500_rubiks (ou « remise_a_zero ») dans RoboDK."""
    os.makedirs(P.DOSSIER_JOURNAL, exist_ok=True)
    RDK.setSimulationSpeed(P.VITESSE_SIMULATION)
    try:
        if nom == "remise_a_zero":
            remise_a_zero()
        elif nom == "verifier_mouvements":
            import verifier
            verifier.verifier_tout()
        else:
            mouvement = getattr(rubiks, nom)
            robot = RobotSimule()
            try:
                RDK.ShowMessage("%s : en cours…" % nom, False)
                rubiks.preparer(robot)
                mouvement(robot)
            finally:
                robot.fermer()
        RDK.ShowMessage("%s : terminé" % nom, False)
    except Exception as e:
        import traceback
        with open(os.path.join(P.DOSSIER_JOURNAL, "erreur.txt"), "w", encoding="utf-8") as f:
            f.write("%s\n%s" % (nom, traceback.format_exc()))
        RDK.ShowMessage("Échec de « %s » : %s (détails : journal/erreur.txt)" % (nom, e), False)
        raise


if __name__ == "__main__":
    noms = ["remise_a_zero", "verifier_mouvements"] + [m.__name__ for m in rubiks.MOUVEMENTS]
    if len(sys.argv) != 2 or sys.argv[1] not in noms:
        sys.exit("Usage : python simulation/simulateur.py <mouvement>\nMouvements : " + ", ".join(noms))
    simuler(sys.argv[1])
