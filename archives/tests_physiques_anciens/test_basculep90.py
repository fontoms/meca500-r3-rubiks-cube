# -*- coding: utf-8 -*-
"""Mouvement « bascule+90 » généré depuis la simulation RoboDK (rubiks_meca500.py).

AVANT DE LANCER :
  - le socle doit être à X=170.0 Y=0.0, dessus à Z=40.0 mm dans le repère base du robot ;
  - TCP de la pince : 94.5 mm sous la bride (centre du cube saisi) ;
  - 1er essai SANS le cube, puis avec le cube ; main sur l'arrêt d'urgence.
pip install mecademicpy
"""
import mecademicpy.robot as mdr

IP = "192.168.0.100"
VITESSE_LIN = 20.0   # mm/s
VITESSE_ART = 10.0   # %

robot = mdr.Robot()
robot.Connect(address=IP)
try:
    robot.ActivateAndHome()
    robot.WaitHomed()
    robot.SetTrf(0, 0, 94.500, 0, 0, 0)
    robot.SetJointVel(VITESSE_ART)
    robot.SetCartLinVel(VITESSE_LIN)
    # position d'attente
    robot.MoveJoints(0.000, 25.333, -34.678, -0.000, 99.345, 90.000)
    # retour position d'attente
    robot.MoveJoints(0.000, 25.333, -34.678, -0.000, 99.345, 90.000)
    # ouvrir la pince
    robot.GripperOpen()
    robot.Delay(0.5)
    # approche inclinée -45°
    robot.MoveLin(170.000, 31.113, 99.613, 135.000, 0.000, -90.000)
    # descente le long de l'axe de la pince
    robot.MoveLin(170.000, 2.828, 71.328, 135.000, 0.000, -90.000)
    # fermer la pince
    robot.GripperClose()
    robot.Delay(0.5)
    # sortie du socle
    robot.MoveLin(170.000, 2.828, 101.328, 135.000, 0.000, -90.000)
    # bascule -45° → +45°
    robot.MoveLin(170.000, -2.828, 101.328, -135.000, 0.000, -90.000)
    # retour dans le socle
    robot.MoveLin(170.000, -2.828, 71.328, -135.000, 0.000, -90.000)
    # ouvrir la pince
    robot.GripperOpen()
    robot.Delay(0.5)
    # dégagement le long de l'axe de la pince
    robot.MoveLin(170.000, -31.113, 99.613, -135.000, 0.000, -90.000)
    # redressement de la pince
    robot.MoveLin(170.000, 0.000, 149.500, 180.000, 0.000, -90.000)
    # retour position d'attente
    robot.MoveJoints(0.000, 25.333, -34.678, 0.000, 99.345, 90.000)
    robot.WaitIdle(120)
finally:
    robot.Disconnect()
