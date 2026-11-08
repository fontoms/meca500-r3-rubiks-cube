# -*- coding: utf-8 -*-
"""Briques de base (meca500_rubiks/briques.py), testées une par une avec un faux robot."""
import meca500_rubiks as rubiks

ATTENTE = rubiks.pose(rubiks.H_ATTENTE)


def test_preparer(robot):
    rubiks.preparer(robot)
    assert robot.commandes[0] == ("SetTrf", rubiks.TCP)
    assert ("SetBlending", (0,)) in robot.commandes
    assert ("SetCartLinVel", (rubiks.VITESSE_LINEAIRE,)) in robot.commandes
    assert ("SetCartAcc", (rubiks.ACCELERATION_CARTESIENNE,)) in robot.commandes
    assert ("SetJointAcc", (rubiks.ACCELERATION_ARTICULAIRE,)) in robot.commandes
    assert ("SetGripperVel", (rubiks.VITESSE_PINCE,)) in robot.commandes
    assert "GripperOpen" in robot.noms()
    assert robot.poses()[-1] == ATTENTE


def test_position_attente(robot):
    rubiks.position_attente(robot)
    assert robot.commandes == [("MovePose", ATTENTE)]


def test_ouvrir_pince_attend(robot):
    rubiks.ouvrir_pince(robot)
    assert robot.commandes == [("GripperOpen", ()), ("Delay", (rubiks.DUREE_PINCE,))]


def test_fermer_pince_attend(robot):
    rubiks.fermer_pince(robot)
    assert robot.commandes == [("GripperClose", ()), ("Delay", (rubiks.DUREE_PINCE,))]


def test_pince_attend_la_fin_reelle_si_le_robot_sait_la_donner(robot):
    """Vrai robot, firmware ≥ 9.1 (robot_reel.connecter met capteur_pince à True) : pas de pause fixe."""
    robot.capteur_pince = True
    rubiks.fermer_pince(robot)
    assert robot.noms() == ["GripperClose", "WaitGripperMoveCompletion"]


def test_saisir_depuis_le_bas_ne_remonte_pas(robot):
    """Liaison rapide : la pince vient de lâcher le cube à H_COUCHES_HAUT, elle descend directement."""
    rubiks.saisir(robot, rubiks.H_CUBE, rotation=90, depuis=(rubiks.H_COUCHES_HAUT, 0.0, 0.0))
    assert robot.poses() == [rubiks.pose(rubiks.H_CUBE, rotation=90)]


def test_saisir_apres_une_bascule_ne_remonte_pas(robot):
    """Pince penchée (bascule), mâchoires sur les faces avant / arrière : elle se redresse directement."""
    depuis = (rubiks.H_CUBE, rubiks.INCLINAISON, rubiks.DECALAGE_BASCULE)
    rubiks.saisir(robot, rubiks.H_COUCHES_HAUT, rotation=-90, depuis=depuis)
    assert robot.poses() == [rubiks.pose(rubiks.H_COUCHES_HAUT, rotation=-90)]


def test_pas_de_liaison_penchee_mâchoires_sur_les_cotes(robot):
    """Pince à 0° : pencher ferait passer les doigts à travers le cube."""
    import pytest
    with pytest.raises(ValueError):
        rubiks.saisir(robot, rubiks.H_CUBE, rotation=0, depuis=(rubiks.H_CUBE, rubiks.INCLINAISON, 10.0))


def test_remonter_apres_une_bascule_degage_le_long_de_l_axe(robot):
    from meca500_rubiks.briques import remonter
    remonter(robot, (rubiks.H_CUBE, 45.0, 10.0), 90)
    assert robot.poses() == [rubiks.pose(rubiks.H_CUBE, 45.0, 90, 10.0 + rubiks.RECUL_BASCULE),
                             rubiks.pose(rubiks.H_ATTENTE, rotation=90)]


def test_lacher_sans_remonter(robot):
    rubiks.lacher_et_remonter(robot, remonter=False)
    assert robot.poses() == []


def test_aller_en_ligne_droite(robot):
    rubiks.aller(robot, 50, inclinaison=45)
    assert robot.commandes == [("MoveLin", rubiks.pose(50, 45))]


def test_saisir(robot):
    rubiks.saisir(robot, rubiks.H_CUBE)
    assert robot.noms() == ["MovePose", "GripperOpen", "MoveLin", "GripperClose", "Delay"]
    assert robot.poses()[-1] == rubiks.pose(rubiks.H_CUBE)


def test_saisir_pince_tournee(robot):
    rubiks.saisir(robot, rubiks.H_CUBE, rotation=-90)
    assert robot.poses() == [rubiks.pose(rubiks.H_ATTENTE, rotation=-90), rubiks.pose(rubiks.H_CUBE, rotation=-90)]


def test_lacher_et_remonter(robot):
    rubiks.lacher_et_remonter(robot, rotation=90)
    assert robot.noms()[0] == "GripperOpen"
    assert robot.poses() == [rubiks.pose(rubiks.H_ATTENTE, rotation=90)]     # la pince reste tournée


def test_etapes_de_rotation():
    """Jamais 180° pile d'un coup (ambigu pour le robot) : 179°, puis le dernier degré."""
    assert rubiks.etapes_de_rotation(0, 0) == []
    assert rubiks.etapes_de_rotation(0, -90) == [-90]
    assert rubiks.etapes_de_rotation(90, -90) == [-89, -90]
    assert rubiks.etapes_de_rotation(-90, 90) == [89, 90]


def test_tourner_pince(robot):
    rubiks.tourner_pince(robot, -90, depuis=90)
    assert robot.poses() == [rubiks.pose(rubiks.H_ATTENTE, rotation=-89), rubiks.pose(rubiks.H_ATTENTE, rotation=-90)]
