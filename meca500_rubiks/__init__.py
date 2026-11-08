# -*- coding: utf-8 -*-
"""
Mouvements du Meca500 R3 pour manipuler un Rubik's cube (API mecademicpy).

Le cube est posé dans un socle dont les mors tiennent la couche du bas.

    reglages.py     adresse IP, vitesses, géométrie (socle, cube, TCP, hauteurs)   ← à régler
    poses.py        calcul des poses de la pince : pose(hauteur, inclinaison, rotation, recul)
    briques.py      préparer, position d'attente, ouvrir / fermer la pince, aller, saisir…
    mouvements.py   les mouvements du cube (une fonction chacun) + la liste MOUVEMENTS
    robot_reel.py   connexion au vrai robot, déconnexion, menu

Utilisation
    import meca500_rubiks as rubiks
    robot = rubiks.connecter()
    rubiks.tourner_cube_gauche(robot)
    rubiks.deconnecter(robot)

    ou :  python piloter_robot.py                    (menu)
          python piloter_robot.py basculer_droite    (un seul mouvement)

Le même code tourne dans la simulation RoboDK (programmes de la station) :
ce que tu vois dans RoboDK est exactement ce que fera le robot.
"""
from .reglages import *        # noqa: F401,F403
from .poses import pose        # noqa: F401
from .briques import (aller, aller_en_tournant, etapes_de_rotation, fermer_pince,  # noqa: F401
                      lacher_et_remonter, ouvrir_pince, photographier, position_attente, preparer,
                      regler_vitesse, saisir, tourner_pince)
from .mouvements import *      # noqa: F401,F403
from .mouvements import MOUVEMENTS  # noqa: F401
from .robot_reel import connecter, deconnecter, menu  # noqa: F401
