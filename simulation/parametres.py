# -*- coding: utf-8 -*-
"""
Paramètres de la simulation RoboDK : maillages 3D, positions dans la scène, réglages des modes.

La géométrie de la cellule (TCP, socle, table, cube) vient de ../meca500_rubiks/reglages.py :
elle n'est écrite qu'à un seul endroit, le code du robot et la simulation ne peuvent pas diverger.

Les maillages 3D sont les VRAIES pièces (dossier ../modeles_3D/) :
  - pince MEGP 25E : dessinée d'après le manuel Mecademic (figure 1), plaque d'adaptation standard
    (le fichier modeles_3D/pince/MEGP_25LS.stp est celui de la 25LS, pas utilisé) ;
  - doigts : modeles_3D/doigts/mors.STL et Mors_droite.STL (placés ici, voir POSE_DOIGT_*) ;
  - socle : simulation/maillages/socle.stl (Cube_holder.stl simplifié à 40 000 triangles, écart
    < 0,1 mm, repère au centre du fond de la poche).
Aucune dépendance à RoboDK ici : ce module s'importe aussi dans les tests.
"""
import os
import sys

# ======================= Dossiers =======================

DOSSIER_SIMULATION = os.path.dirname(os.path.abspath(__file__))
DOSSIER_PROJET = os.path.dirname(DOSSIER_SIMULATION)
DOSSIER_JOURNAL = os.path.join(DOSSIER_PROJET, "journal")
DOSSIER_PROGRAMMES = os.path.join(DOSSIER_SIMULATION, "programmes")
DOSSIER_MAILLAGES = os.path.join(DOSSIER_SIMULATION, "maillages")
DOSSIER_MODELES = os.path.join(DOSSIER_PROJET, "modeles_3D")
if DOSSIER_PROJET not in sys.path:
    sys.path.insert(0, DOSSIER_PROJET)          # pour importer meca500_rubiks

from meca500_rubiks import reglages as R      # noqa: E402  géométrie de la cellule (source unique)

# ======================= Lancement de scene.py =======================

MODE = "installer"                # "installer", "tests" ou "resolution" (voir scene.py)

VITESSE_SIMULATION = 1.0          # 1 = temps réel (RoboDK accélère souvent ×5 par défaut)

# MODE "tests" : mouvements de meca500_rubiks rejoués avec détection de collisions
# (robot, pince, doigts, socle, table, cube). Résultat : journal/collisions.txt.
TESTS = ["verifier_outil", "prendre_et_reposer", "tourner_cube_gauche", "tourner_cube_droite", "basculer_gauche",
         "basculer_droite", "tourner_haut_gauche", "tourner_haut_droite", "presenter_faces"]
VERIFIER_COLLISIONS = True
PAUSE_ENTRE_TESTS = 0.5           # s

# MODE "resolution" :
# MELANGE  : coups appliqués instantanément au cube virtuel ("R U R' U'" ou un nombre → aléatoire).
# SOLUTION : coups exécutés par le robot. Vide → kociemba si installé, sinon inverse du mélange.
MELANGE = "R U F' L2 D B'"
SOLUTION = ""
GRAINE_ALEATOIRE = None

ENREGISTRER_PROJET = True
NOM_PROJET = "Rubiks_Meca500.rdk"   # dans DOSSIER_PROJET
JOURNAL = "Rubiks_Meca500_journal.txt"

# ======================= Cellule (reprise de meca500_rubiks/reglages.py) =======================

SOCLE_X, SOCLE_Y, HAUTEUR_SOCLE = R.SOCLE      # centre du fond de la poche du socle
TABLE_X, TABLE_Y, HAUTEUR_TABLE = R.TABLE      # point de pose du cube sur la table
COTE_CUBE = R.COTE_CUBE
TCP = R.TCP                                    # bride → TCP (x, y, z, alpha, beta, gamma), comme SetTrf

# ======================= Maillages =======================

FICHIER_SOCLE = os.path.join(DOSSIER_MAILLAGES, "socle.stl")
FICHIER_DOIGT_1 = os.path.join(DOSSIER_MODELES, "doigts", "mors.STL")
FICHIER_DOIGT_2 = os.path.join(DOSSIER_MODELES, "doigts", "Mors_droite.STL")

# Position des doigts dans le repère de la bride, pince OUVERTE. La languette de chaque mâchoire
# entre dans l'encoche du doigt (vis M4 à 19 mm sous la bride, 17 mm de l'axe, selon +X bride).
# Rotation (les deux doigts) : X du STL → -Y de la bride, Y du STL → -Z (le doigt descend),
# Z du STL → +X de la bride (direction de la pince, vers les mâchoires).
POSE_DOIGT_1 = (-19.37, 56.8, 98.23)     # mors.STL, côté +Y de la bride
POSE_DOIGT_2 = (-19.37, 34.8, 98.23)     # Mors_droite.STL (symétrique), côté -Y
SERRAGE = 2.9                     # course simulée de chaque mâchoire à la fermeture (3 mm max)
DOIGT_SOUS_TCP = 5.0              # bas des patins sous le TCP (patins de 10 mm de haut)

# MEGP 25E (manuel, figure 1), repère de la bride : X vers les mâchoires, Z sort de la bride.
# Boîtes (x0, y0, z0, x1, y1, z1).
PINCE_25E = [
    (-15.75, -15.75, 0.0, 15.75, 15.75, 3.0),     # plaque d'adaptation
    (-49.0, -12.7, 3.0, 13.5, 12.7, 25.4),        # corps
    (-49.0, 12.7, 6.0, -37.0, 29.5, 18.0),        # connecteur
]
LANGUETTES_25E = (13.5, 21.0, 14.0, 24.0, 4.0)   # x0, x1, z0, z1, épaisseur (face ext. à 12,5 ouverte)

# ======================= Valeurs dérivées (ne pas modifier) =======================

h = COTE_CUBE / 2                 # demi-côté du cube
S = COTE_CUBE / 3                 # côté d'un cubie

# ======================= Noms et couleurs dans la station =======================

NOM_REPERE = "Socle_repere"
NOM_OUTIL = "MEGP 25E"
NOMS_SCENE = ["Socle", "Table", "Camera", "Cube", "Cube_bas", "Cube_haut"]
NOMS_PINCE = ["Pince_plaque", "Pince_corps", "Pince_CAO", "Pince", "Doigt_1", "Doigt_2"]

COUL = {
    "noir": [0.05, 0.05, 0.05, 1], "gris": [0.6, 0.6, 0.62, 1], "gris_fonce": [0.3, 0.3, 0.33, 1],
    "pla": [0.95, 0.55, 0.15, 1], "alu": [0.8, 0.8, 0.82, 1], "socle": [0.45, 0.35, 0.25, 1],
    "table": [0.85, 0.85, 0.8, 1], "camera": [0.15, 0.15, 0.17, 1],
    "U": [0.95, 0.95, 0.95, 1], "D": [1.0, 0.85, 0.0, 1], "F": [0.0, 0.6, 0.2, 1],
    "B": [0.0, 0.3, 0.8, 1], "R": [0.85, 0.1, 0.1, 1], "L": [1.0, 0.45, 0.0, 1],
}

# ======================= Table et caméra (presenter_faces) =======================

NOM_REPERE_TABLE = "Table_repere"
TABLE_DESSIN = (-120.0, 320.0, -320.0, 160.0, 6.0)   # plaque dessinée : x min, x max, y min, y max, épaisseur

# Caméra (représentation 3D seulement) : à droite du cube posé sur la table, à hauteur de son
# centre, elle regarde le cube (donc vers le socle).
NOM_REPERE_CAMERA = "Camera_repere"
DISTANCE_CAMERA = 250.0           # mm entre l'objectif et le centre du cube
BOITIER_CAMERA = (60.0, 40.0, 50.0)   # largeur, hauteur, profondeur du boîtier (mm)
OBJECTIF_CAMERA = (24.0, 20.0)        # côté, longueur de l'objectif (mm)
PAUSE_PHOTO = 1.0                 # s de pause simulée à chaque photo

# ======================= Vitesses de la simulation =======================

VITESSE_LIN = 35.0
VITESSE_ART = 45.0
