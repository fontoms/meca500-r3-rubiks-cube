# -*- coding: utf-8 -*-
"""
Vérification cinématique des mouvements de ../meca500_rubiks/ sur le Meca500 R3.

Chaque mouvement est rejoué « à blanc » (le robot de la station ne bouge pas) par un faux robot
qui calcule la cinématique inverse tous les 1 mm / 1° le long de chaque MoveLin, et vérifie :

  - ATTEIGNABLE   : chaque point du trajet a une solution de cinématique inverse ;
  - BUTÉES        : marge par rapport aux limites articulaires du Meca500 (≥ MARGE_BUTEE) ;
  - SINGULARITÉ   : |J5| reste loin de 0° (singularité du poignet, ≥ MARGE_POIGNET) ;
  - CÂBLE         : J6 reste entre -180° et +180° (recommandation Mecademic pour le câble de la
                    pince), en partant du robot juste après le homing (toutes articulations à 0°) ;
  - CONTINUITÉ    : pas de saut d'articulation entre deux points voisins (changement de
                    configuration ou passage près d'une singularité : le vrai robot refuserait
                    le MoveLin ou ferait un mouvement brusque).

Les collisions se vérifient à part (simulation/scene.py, MODE = "tests" dans parametres.py).
Résultat : fenêtre RoboDK + journal/verification.txt.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import parametres as P                          # noqa: E402
import meca500_rubiks as rubiks                 # noqa: E402
from connexion_robodk import RDK                # noqa: E402

from robodk.robolink import ITEM_TYPE_ROBOT     # noqa: E402
from robodk.robomath import TxyzRxyz_2_Pose, pi, pose_2_quaternion, quaternion_2_pose  # noqa: E402

MARGE_BUTEE = 10.0       # ° minimum avant une butée articulaire
MARGE_POIGNET = 10.0     # ° minimum pour |J5| (singularité du poignet à J5 = 0)
SAUT_MAX = 5.0           # ° maximum de variation d'une articulation entre deux points voisins
J6_MAX = 180.0           # ° : plage recommandée pour J6 avec le câble de la MEGP 25E
PAS_MM, PAS_DEG = 1.0, 1.0


def _pose(p):
    x, y, z, a, b, g = p
    return TxyzRxyz_2_Pose([x, y, z, a * pi / 180, b * pi / 180, g * pi / 180])


def _slerp(q0, q1, t):
    d = sum(a * b for a, b in zip(q0, q1))
    if d < 0:
        q1, d = [-v for v in q1], -d
    if d > 0.9995:
        q = [a + t * (b - a) for a, b in zip(q0, q1)]
    else:
        th = math.acos(d)
        q = [(math.sin((1 - t) * th) * a + math.sin(t * th) * b) / math.sin(th) for a, b in zip(q0, q1)]
    n = math.sqrt(sum(v * v for v in q))
    return [v / n for v in q]


class RobotVerificateur:
    """Faux robot mecademicpy qui ne bouge pas mais vérifie chaque trajectoire."""

    def __init__(self):
        self.robot = RDK.Item("", ITEM_TYPE_ROBOT)
        bas, haut, _ = self.robot.JointLimits()
        self.bas, self.haut = bas.list()[:6], haut.list()[:6]
        self.joints = [0.0] * 6          # robot juste après le homing
        self.j6_max = 0.0
        self.tcp = _pose(rubiks.TCP)     # bride → TCP (centre des patins des doigts)
        self.pose = None
        self.pires = {}                  # (étape, type) -> (valeur, message) : pire cas seulement
        self.marge_butee = (999.0, "")
        self.j5_min = 999.0
        self.saut_max = 0.0
        self.nb_points = 0
        self.etape = ""

    # --- vérifications ---
    def _ik(self, pose_tcp, approx):
        j = self.robot.SolveIK(pose_tcp * self.tcp.inv(), approx).list()
        return j[:6] if len(j) >= 6 else None

    def _controler(self, j, precedent):
        self.nb_points += 1
        for i in range(6):
            marge = min(j[i] - self.bas[i], self.haut[i] - j[i])
            if marge < self.marge_butee[0]:
                self.marge_butee = (marge, "J%d" % (i + 1))
            if marge < MARGE_BUTEE:
                self._probleme("butée J%d" % (i + 1), marge, "J%d à %.0f° de sa butée" % (i + 1, marge))
        self.j5_min = min(self.j5_min, abs(j[4]))
        self.j6_max = max(self.j6_max, abs(j[5]))
        if abs(j[5]) > J6_MAX:
            self._probleme("câble", -abs(j[5]), "J6 = %.0f° : hors de [-180°, 180°], le câble de la pince force" % j[5])
        if abs(j[4]) < MARGE_POIGNET:
            self._probleme("poignet", abs(j[4]), "poignet presque aligné (J5 = %.1f°) : singularité" % j[4])
        if precedent is not None:
            saut = max(abs(a - b) for a, b in zip(j, precedent))
            self.saut_max = max(self.saut_max, saut)
            if saut > SAUT_MAX:
                self._probleme("saut", -saut, "saut de %.0f° d'une articulation (changement de configuration)" % saut)

    def _probleme(self, genre, valeur, texte):
        """Garde, pour chaque étape et chaque type de problème, le cas le plus grave (valeur la plus basse)."""
        cle = (self.etape, genre)
        if cle not in self.pires or valeur < self.pires[cle][0]:
            self.pires[cle] = (valeur, "%s : %s" % (self.etape, texte))

    @property
    def problemes(self):
        return [msg for _, msg in self.pires.values()]

    # --- commandes mecademicpy ---
    def MoveLin(self, *p):
        self.etape = "MoveLin%s" % (tuple(round(v, 1) for v in p),)
        cible = _pose(p)
        depart = self.pose if self.pose is not None else cible
        dist = math.dist(depart.Pos(), cible.Pos())
        q0, q1 = pose_2_quaternion(depart), pose_2_quaternion(cible)
        angle = math.degrees(2 * math.acos(min(1.0, abs(sum(a * b for a, b in zip(q0, q1))))))
        n = max(1, int(math.ceil(max(dist / PAS_MM, angle / PAS_DEG))))
        j = self.joints
        for k in range(1, n + 1):
            t = k / n
            pos = [a + t * (b - a) for a, b in zip(depart.Pos(), cible.Pos())]
            m = quaternion_2_pose(_slerp(q0, q1, t))
            m.setPos(pos)
            jj = self._ik(m, j)
            if jj is None:
                self._probleme("inaccessible", 0, "point inaccessible à %.0f %% du trajet" % (100 * t))
                break
            self._controler(jj, j)
            j = jj
        self.joints, self.pose = j, cible

    def MovePose(self, *p):
        self.etape = "MovePose%s" % (tuple(round(v, 1) for v in p),)
        cible = _pose(p)
        j = self._ik(cible, self.joints)
        if j is None:
            self._probleme("inaccessible", 0, "position inaccessible")
            return
        self._controler(j, None)          # mouvement articulaire : seules les extrémités comptent
        self.joints, self.pose = j, cible

    def MoveJoints(self, *j):
        self.etape = "MoveJoints"
        self._controler(list(j), None)
        self.joints, self.pose = list(j), self.robot.SolveFK(list(j)) * self.tcp

    def _rien(self, *args, **kwargs):
        pass

    Connect = ActivateAndHome = WaitHomed = WaitIdle = DeactivateRobot = Disconnect = _rien
    SetBlending = SetCartLinVel = SetCartAngVel = SetJointVel = _rien

    def SetTrf(self, *p):
        self.tcp = _pose(p)
    GripperOpen = GripperClose = Delay = prendre_photo = _rien


def verifier_mouvement(mouvement):
    """Vérifie UN mouvement (ex. rubiks.basculer_droite). Résultat : .problemes (liste vide = OK),
    .nb_points, .marge_butee, .j5_min, .saut_max."""
    v = RobotVerificateur()
    rubiks.preparer(v)
    mouvement(v)
    return v


def verifier_tout(afficher=True):
    """Vérifie tous les mouvements de meca500_rubiks.MOUVEMENTS. Renvoie (tout_ok, {nom: problèmes}).

    afficher=False : pas de fenêtre RoboDK (utilisé par les tests pytest).
    """
    lignes = ["Vérification cinématique (marges : butées ≥ %.0f°, |J5| ≥ %.0f°, |J6| ≤ %.0f°, saut ≤ %.0f°)"
              % (MARGE_BUTEE, MARGE_POIGNET, J6_MAX, SAUT_MAX), ""]
    tout_ok = True
    resultats = {}
    for mouvement in rubiks.MOUVEMENTS:
        v = verifier_mouvement(mouvement)
        ok = not v.problemes
        resultats[mouvement.__name__] = v.problemes
        tout_ok &= ok
        lignes.append("%-22s %s   (%d points ; butée la plus proche : %.0f° sur %s ; |J5| min %.0f° ; |J6| max %.0f° ;"
                      " saut max %.1f°)" % (mouvement.__name__, "OK " if ok else "PROBLÈME", v.nb_points,
                                            v.marge_butee[0], v.marge_butee[1], v.j5_min, v.j6_max, v.saut_max))
        lignes += ["      - " + p for p in v.problemes]
    lignes += ["", "TOUS LES MOUVEMENTS SONT VALIDES" if tout_ok else "ATTENTION : au moins un mouvement pose problème"]
    texte = "\n".join(lignes)
    os.makedirs(P.DOSSIER_JOURNAL, exist_ok=True)
    with open(os.path.join(P.DOSSIER_JOURNAL, "verification.txt"), "w", encoding="utf-8") as f:
        f.write(texte + "\n")
    print(texte)
    if afficher:
        RDK.ShowMessage(texte, True)
    return tout_ok, resultats


if __name__ == "__main__":
    sys.exit(0 if verifier_tout()[0] else 1)
