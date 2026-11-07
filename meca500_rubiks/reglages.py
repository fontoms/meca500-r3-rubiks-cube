# -*- coding: utf-8 -*-
"""Réglages du robot et géométrie de la cellule (repère de base du robot, en mm).

Géométrie réelle : pince MEGP 25E (manuel Mecademic, figure 1) montée avec sa plaque d'adaptation
standard, doigts imprimés (modeles_3D/doigts), socle Cube_holder.stl (modeles_3D/socle).
"""

ADRESSE_IP = "192.168.0.100"

VITESSE_LINEAIRE = 20.0      # mm/s   (lent pour les premiers essais)
VITESSE_ANGULAIRE = 30.0     # °/s    rotations de la pince
VITESSE_ARTICULAIRE = 10.0   # % de la vitesse max des articulations
DUREE_PINCE = 0.5            # s      attente après ouverture / fermeture

SOCLE = (170.0, 0.0, 7.0)    # centre du fond de la poche du socle, où repose le cube (x, y, z) :
#                              socle posé sur la plaque du robot, le cube repose 7 mm au-dessus
COTE_CUBE = 57.0

# TCP = centre des patins des doigts, dans le repère de la bride (SetTrf) :
#   - trou M4 des mâchoires à 19 mm sous la bride et 17 mm de son axe (manuel MEGP 25E) ;
#   - doigts : centre des patins 74,2 mm sous ce trou et 13,9 mm vers l'axe de la bride.
# Patins : 10 mm de haut, 45 mm de long (horizontaux), 63,6 mm d'écart pince ouverte,
# 57,6 mm pince fermée (course 3 mm par mâchoire) : le scotch sur les patins rattrape les 0,6 mm.
TCP = (3.1, 0.0, 93.2, 0.0, 0.0, 0.0)

# Hauteurs du TCP au-dessus du dessus du socle
H_CUBE = COTE_CUBE / 2       # TCP au centre du cube posé : patins de 23,5 à 33,5 mm (couche du milieu)
H_COUCHES_HAUT = 34.5        # patins de 29,5 à 39,5 mm : couches du milieu et du haut, pas celle du bas
LEVEE = 30.0                 # on soulève le cube de 30 mm pour le sortir du socle
H_ATTENTE = 109.5            # position d'attente : bas des patins 47,5 mm au-dessus du cube

# Bascule : la pince prend le cube penchée à 45°, le tourne de 90°, le repose penchée de l'autre côté.
# (Pince couchée à 90° : hors de portée du robot et collision avec les mors du socle.)
INCLINAISON = 45.0           # °
DECALAGE_BASCULE = 10.0      # cube tenu 10 mm plus bas dans les patins (couches du milieu et du haut) :
#                              sinon les bras des doigts touchent les coins du haut en penchant à 45°
RECUL_BASCULE = 40.0         # approche / dégagement le long de l'axe de la pince penchée

# Présentation des faces à la caméra (presenter_faces) : le cube est posé sur la table,
# à droite du socle (vu depuis le robot) ; la caméra est encore plus à droite et regarde vers le socle.
TABLE = (170.0, -110.0, 0.0)  # point de pose du cube sur la table : centre de sa face du dessous (x, y, z)
DUREE_PHOTO = 1.0            # s      robot immobile pendant chaque photo
