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

from robodk.robolink import ITEM_TYPE_FRAME, ITEM_TYPE_OBJECT, ITEM_TYPE_ROBOT, ITEM_TYPE_TOOL  # noqa: E402
from robodk.robomath import Mat, TxyzRxyz_2_Pose, pi, transl  # noqa: E402


def _pose(x, y, z, alpha, beta, gamma):
    """Pose Mecademic (mm, degrés, Rx·Ry·Rz) → matrice RoboDK."""
    return TxyzRxyz_2_Pose([x, y, z, alpha * pi / 180, beta * pi / 180, gamma * pi / 180])


class RobotSimule:
    """Faux robot mecademicpy : joue les commandes sur le Meca500 de la station RoboDK."""

    def __init__(self):
        self.robot = RDK.Item("", ITEM_TYPE_ROBOT)
        self.socle = RDK.Item(P.NOM_REPERE, ITEM_TYPE_FRAME)
        self.table = RDK.Item(P.NOM_REPERE_TABLE, ITEM_TYPE_FRAME)
        self.outil = RDK.Item(P.NOM_OUTIL, ITEM_TYPE_TOOL)
        self.doigts = [(RDK.Item("Doigt_1", ITEM_TYPE_OBJECT), 1), (RDK.Item("Doigt_2", ITEM_TYPE_OBJECT), -1)]
        self.cubies = [it for it in RDK.ItemList(ITEM_TYPE_OBJECT) if it.Name().startswith("Cubie_")]
        if not (self.robot.Valid() and self.socle.Valid() and self.table.Valid() and self.outil.Valid()
                and len(self.cubies) == 26):
            raise RuntimeError("Scène incomplète : lance « remise_a_zero » (ou Tools > Run Script > 00_Rubiks_Meca500).")
        self._verifier_dimensions()

        self.robot.setPoseFrame(self.robot.Parent())     # MoveLin : repère de base du robot
        self.robot.setPoseTool(self.outil)
        self.robot.setSpeed(P.VITESSE_LIN, P.VITESSE_ART)
        self.tenus = []
        for doigt, _ in self.doigts:                      # pince ouverte
            doigt.setPose(transl(0, 0, -P.TCP_Z))
        self.journal = open(os.path.join(P.DOSSIER_JOURNAL, "dernier_mouvement.txt"), "w")

    def _verifier_dimensions(self):
        """Le code robot et la scène doivent utiliser les mêmes dimensions."""
        ecarts = []
        if abs(rubiks.TCP - P.TCP_Z) > 0.01:
            ecarts.append("TCP : %.1f (code robot) ≠ %.1f (simulation)" % (rubiks.TCP, P.TCP_Z))
        if any(abs(a - b) > 0.01 for a, b in zip(rubiks.SOCLE, (P.SOCLE_X, P.SOCLE_Y, P.HAUTEUR_SOCLE))):
            ecarts.append("SOCLE : %s ≠ %s" % (rubiks.SOCLE, (P.SOCLE_X, P.SOCLE_Y, P.HAUTEUR_SOCLE)))
        if any(abs(a - b) > 0.01 for a, b in zip(rubiks.TABLE, (P.TABLE_X, P.TABLE_Y, P.HAUTEUR_TABLE))):
            ecarts.append("TABLE : %s ≠ %s" % (rubiks.TABLE, (P.TABLE_X, P.TABLE_Y, P.HAUTEUR_TABLE)))
        if abs(rubiks.COTE_CUBE - P.COTE_CUBE) > 0.01:
            ecarts.append("COTE_CUBE : %.1f ≠ %.1f" % (rubiks.COTE_CUBE, P.COTE_CUBE))
        if ecarts:
            raise RuntimeError("meca500_rubiks/reglages.py et simulation/parametres.py ne concordent pas :\n" + "\n".join(ecarts))

    def fermer(self):
        self.journal.close()

    def _noter(self, texte):
        self.journal.write("%s  %s\n" % (time.strftime("%H:%M:%S"), texte))
        self.journal.flush()

    # ---------------- déplacements ----------------
    def MoveLin(self, *p):
        self._noter("MoveLin%s" % (p,))
        self.robot.MoveL(_pose(*p))

    def MovePose(self, *p):
        self._noter("MovePose%s" % (p,))
        self.robot.MoveJ(_pose(*p))

    def MoveJoints(self, *j):
        self._noter("MoveJoints%s" % (j,))
        self.robot.MoveJ(list(j))

    def Delay(self, secondes):
        self.robot.Pause(secondes * 1000)

    # ---------------- pince ----------------
    def GripperClose(self):
        self._noter("GripperClose")
        for doigt, sens in self.doigts:
            doigt.setPose(transl(0, 0, -P.TCP_Z) * transl(0, -sens * P.SERRAGE, 0))
        self.tenus = self._cubies_entre_les_doigts()
        for c in self.tenus:
            c.setParentStatic(self.outil)

    def GripperOpen(self):
        self._noter("GripperOpen")
        for doigt, _ in self.doigts:
            doigt.setPose(transl(0, 0, -P.TCP_Z))
        support = self._support_sous_la_pince()
        for c in self.tenus:
            c.setParentStatic(support)
            self._recaler(c)
        self.tenus = []

    def _support_sous_la_pince(self):
        """Socle ou table : le repère le plus proche du TCP (à l'horizontale)."""
        tcp = self.robot.Pose()                   # TCP dans le repère de base (socle et table aussi)

        def distance(repere):
            p = repere.Pose()
            return (p[0, 3] - tcp[0, 3]) ** 2 + (p[1, 3] - tcp[1, 3]) ** 2
        return min((self.socle, self.table), key=distance)

    def _cubies_entre_les_doigts(self):
        """Cube entier, sauf si le bout des doigts est au-dessus de la couche du bas
        (pince verticale assez haute) : alors seulement les cubies au-dessus des doigts."""
        if self._support_sous_la_pince() != self.socle:      # sur la table : toujours le cube entier
            return list(self.cubies)
        tcp = self.socle.Pose().inv() * self.robot.Pose()     # TCP dans le repère du socle
        axe_z = tcp[2, 2]                                     # -1 : pince verticale vers le bas
        bout_doigts = tcp[2, 3] - P.DOIGT_SOUS_TCP
        if axe_z > -0.99 or bout_doigts < P.S:
            return list(self.cubies)
        return [c for c in self.cubies if c.Pose()[2, 3] > bout_doigts]

    def _recaler(self, cubie):
        """Replace exactement le cubie sur la grille du cube (supprime les petites dérives)."""
        m = cubie.Pose()
        rot = [[float(round(m[i, j])) for j in range(3)] for i in range(3)]
        pos = [round(m[0, 3] / P.S) * P.S, round(m[1, 3] / P.S) * P.S,
               P.h + round((m[2, 3] - P.h) / P.S) * P.S]
        ecart = max(abs(m[i, 3] - pos[i]) for i in range(3))
        if ecart > 2.0:
            RDK.ShowMessage("Attention : le cube n'a pas été reposé à sa place (écart %.0f mm)" % ecart, False)
            return
        cubie.setPose(Mat([rot[0] + [pos[0]], rot[1] + [pos[1]], rot[2] + [pos[2]], [0, 0, 0, 1]]))

    # ---------------- commandes sans effet en simulation ----------------
    # ---------------- photo (presenter_faces) ----------------
    def prendre_photo(self, face):
        """Appelé par meca500_rubiks.photographier : pas de caméra simulée, juste une pause et un message."""
        self._noter("Photo face %s" % face)
        RDK.ShowMessage("Photo : face « %s »" % face, False)
        self.robot.Pause(P.PAUSE_PHOTO * 1000)

    def _rien(self, *args, **kwargs):
        pass

    Connect = ActivateAndHome = WaitHomed = WaitIdle = DeactivateRobot = Disconnect = _rien
    SetBlending = SetCartLinVel = SetCartAngVel = SetJointVel = _rien

    def SetTrf(self, x, y, z, alpha, beta, gamma):
        self.outil.setPoseTool(_pose(x, y, z, alpha, beta, gamma))


def remise_a_zero():
    """Cube neuf dans le socle, robot en position d'attente."""
    from banc_essais import preparer_scene
    P.VERIFIER_COLLISIONS = False
    preparer_scene([])


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
        with open(os.path.join(P.DOSSIER_JOURNAL, "erreur.txt"), "w") as f:
            f.write("%s\n%s" % (nom, traceback.format_exc()))
        RDK.ShowMessage("Échec de « %s » : %s (détails : journal/erreur.txt)" % (nom, e), False)
        raise


if __name__ == "__main__":
    noms = ["remise_a_zero", "verifier_mouvements"] + [m.__name__ for m in rubiks.MOUVEMENTS]
    if len(sys.argv) != 2 or sys.argv[1] not in noms:
        sys.exit("Usage : python simulation/simulateur.py <mouvement>\nMouvements : " + ", ".join(noms))
    simuler(sys.argv[1])
