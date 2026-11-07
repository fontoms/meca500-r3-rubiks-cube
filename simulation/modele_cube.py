# -*- coding: utf-8 -*-
"""Le modèle du cube est dans meca500_rubiks/modele_cube.py (utilisé aussi par la résolution
sur le vrai robot) ; ce module le réexporte pour la simulation et les tests."""
from meca500_rubiks.modele_cube import *  # noqa: F401,F403
from meca500_rubiks.modele_cube import (DIR_FACE, FACE_DIR, ModeleCube, chemin_vers_bas,  # noqa: F401
                                        cross, ecrire_coups, inverse, lire_coups, mul, mulm, nom_cubie,
                                        rot_autour, rot_quart, transp)
