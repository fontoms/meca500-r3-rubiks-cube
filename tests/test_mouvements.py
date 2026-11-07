# -*- coding: utf-8 -*-
"""
Un groupe de tests PAR MOUVEMENT (classe TestXxx) : dans PyCharm, le ▶ à côté d'une classe
lance seulement ce mouvement.

  - séquence de commandes (faux robot, sans RoboDK) ;
  - cinématique dans RoboDK : atteignable, butées, poignet, sauts (RoboDK ouvert, sinon ignoré) ;
  - simulation animée dans RoboDK : seulement avec  pytest -m simulation.
"""
import pytest

import meca500_rubiks as rubiks
from conftest import FauxRobot

ATTENTE = rubiks.pose(rubiks.H_ATTENTE)


def support_le_plus_proche(x, y):
    return min((rubiks.SOCLE, rubiks.TABLE), key=lambda s: (s[0] - x) ** 2 + (s[1] - y) ** 2)


class _Controles:
    """Contrôles communs ; chaque classe TestXxx ci-dessous choisit son mouvement."""
    mouvement = None

    def jouer(self):
        robot = FauxRobot()
        type(self).mouvement(robot)
        return robot

    def test_part_et_revient_en_position_d_attente(self):
        poses = self.jouer().poses()
        assert poses[0] == ATTENTE
        assert poses[-1] == ATTENTE

    def test_pince_ouverte_a_la_fin(self):
        etat = "ouverte"
        for nom in self.jouer().noms():
            if nom == "GripperClose":
                assert etat == "ouverte", "pince fermée deux fois de suite"
                etat = "fermee"
            elif nom == "GripperOpen":
                etat = "ouverte"
        assert etat == "ouverte"

    def test_tcp_jamais_sous_le_centre_du_cube(self):
        """Le TCP ne descend pas sous le centre du cube posé (socle ou table) : la pince ne touche pas le support."""
        for p in self.jouer().poses():
            support = support_le_plus_proche(p[0], p[1])
            assert p[2] >= support[2] + rubiks.H_CUBE - 3.0, p

    @pytest.mark.robodk
    def test_cinematique_robodk(self):
        import verifier
        v = verifier.verifier_mouvement(type(self).mouvement)
        assert not v.problemes, "\n".join(v.problemes)

    @pytest.mark.simulation
    def test_simulation_robodk(self):
        import simulateur
        simulateur.simuler(type(self).mouvement.__name__)


class TestPrendreEtReposer(_Controles):
    mouvement = rubiks.prendre_et_reposer


class TestTournerCubeGauche(_Controles):
    mouvement = rubiks.tourner_cube_gauche


class TestTournerCubeDroite(_Controles):
    mouvement = rubiks.tourner_cube_droite


class TestBasculerGauche(_Controles):
    mouvement = rubiks.basculer_gauche


class TestBasculerDroite(_Controles):
    mouvement = rubiks.basculer_droite


class TestBasculerAvant(_Controles):
    mouvement = rubiks.basculer_avant


class TestBasculerArriere(_Controles):
    mouvement = rubiks.basculer_arriere


class TestTournerHautGauche(_Controles):
    mouvement = rubiks.tourner_haut_gauche


class TestTournerHautDroite(_Controles):
    mouvement = rubiks.tourner_haut_droite


class TestPresenterFaces(_Controles):
    mouvement = rubiks.presenter_faces

    def test_une_photo_par_face(self):
        robot = self.jouer()
        photos = [args[0] for nom, args in robot.commandes if nom == "prendre_photo"]
        assert sorted(photos) == sorted(["dessus", "dessous", "avant", "arriere", "gauche", "droite"])

    def test_robot_immobile_avant_chaque_photo(self):
        noms = self.jouer().noms()
        for i, nom in enumerate(noms):
            if nom == "prendre_photo":
                assert noms[i - 1] == "WaitIdle"


# Effet de chaque mouvement sur l'orientation du cube (quarts de tour autour de X / Y / Z)
ROTATIONS = {"tourner_gauche": (2, -1), "tourner_droite": (2, 1), "basculer_gauche": (0, -1), "basculer_droite": (0, 1)}
DIRECTION_FACE = {"dessus": (0, 0, 1), "dessous": (0, 0, -1), "avant": (-1, 0, 0),
                  "arriere": (1, 0, 0), "gauche": (0, 1, 0), "droite": (0, -1, 0)}


def test_sequence_photo_montre_vraiment_chaque_face():
    """Avec le modèle du cube : à chaque photo, la face annoncée est bien tournée vers la caméra (à droite)."""
    from modele_cube import mul, mulm, rot_quart, transp
    vers_camera = DIRECTION_FACE["droite"]
    orientation = rot_quart(0, 0)
    vues = []
    for mouvement, face in [(None, rubiks.FACE_VUE_AU_DEPART)] + rubiks.ETAPES_PHOTO:
        if mouvement is not None:
            orientation = mulm(rot_quart(*ROTATIONS[mouvement]), orientation)
        assert mul(transp(orientation), vers_camera) == DIRECTION_FACE[face], (mouvement, face)
        vues.append(face)
    assert sorted(vues) == sorted(DIRECTION_FACE)


def test_presenter_faces_pose_le_cube_sur_la_table():
    robot = FauxRobot()
    rubiks.presenter_faces(robot)
    table = [p for p in robot.poses() if support_le_plus_proche(p[0], p[1]) == rubiks.TABLE]
    assert table, "le cube n'est jamais allé sur la table"
    assert min(p[2] for p in table) == pytest.approx(rubiks.TABLE[2] + rubiks.H_CUBE)


def test_dimensions_identiques_robot_et_simulation():
    """meca500_rubiks/reglages.py et simulation/parametres.py doivent décrire la même cellule."""
    import parametres as P
    assert rubiks.TCP == pytest.approx(P.TCP_Z, abs=0.01)
    assert rubiks.SOCLE == pytest.approx((P.SOCLE_X, P.SOCLE_Y, P.HAUTEUR_SOCLE), abs=0.01)
    assert rubiks.COTE_CUBE == pytest.approx(P.COTE_CUBE, abs=0.01)
    assert rubiks.TABLE == pytest.approx((P.TABLE_X, P.TABLE_Y, P.HAUTEUR_TABLE), abs=0.01)
