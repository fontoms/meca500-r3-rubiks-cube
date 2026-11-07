# -*- coding: utf-8 -*-
# Programme RoboDK : exécute meca500_rubiks.remise_a_zero() dans la simulation.
import os
import sys
from robodk import robolink
projet = robolink.Robolink().getParam("PATH_OPENSTATION")    # dossier de Rubiks_Meca500.rdk
sys.path.insert(0, os.path.join(projet, "simulation"))
import simulateur
simulateur.simuler('remise_a_zero')
