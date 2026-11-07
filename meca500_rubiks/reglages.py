# -*- coding: utf-8 -*-
"""Réglages du robot et géométrie de la cellule (repère de base du robot, en mm)."""

ADRESSE_IP = "192.168.0.100"

VITESSE_LINEAIRE = 20.0      # mm/s   (lent pour les premiers essais)
VITESSE_ANGULAIRE = 30.0     # °/s    rotations de la pince
VITESSE_ARTICULAIRE = 10.0   # % de la vitesse max des articulations
DUREE_PINCE = 0.5            # s      attente après ouverture / fermeture

SOCLE = (170.0, 0.0, 40.0)   # centre du dessus du socle (x, y, z)
COTE_CUBE = 57.0
TCP = 94.5                   # distance bride → centre du cube saisi (point piloté par MoveLin)

# Hauteurs du TCP au-dessus du dessus du socle
H_CUBE = COTE_CUBE / 2       # TCP au centre du cube posé : la pince tient le cube entier
H_COUCHES_HAUT = 34.5        # TCP plus haut : les doigts ne tiennent que les 2 couches du haut
LEVEE = 30.0                 # on soulève le cube de 30 mm pour le sortir du socle
H_ATTENTE = 109.5            # position d'attente : doigts 40 mm au-dessus du cube

# Bascule : la pince prend le cube penchée à 45°, le tourne de 90°, le repose penchée de l'autre côté.
# (Pince couchée à 90° : hors de portée du robot et collision avec les mors du socle.)
INCLINAISON = 45.0           # °
DECALAGE_BASCULE = 4.0       # cube tenu 4 mm plus près du bout des doigts (son arête évite la pince)
RECUL_BASCULE = 40.0         # approche / dégagement le long de l'axe de la pince penchée

# Présentation des faces à la caméra (presenter_faces) : le cube est posé sur la table,
# à droite du socle (vu depuis le robot) ; la caméra est encore plus à droite et regarde vers le socle.
TABLE = (170.0, -110.0, 0.0)  # point de pose du cube sur la table : centre de sa face du dessous (x, y, z)
DUREE_PHOTO = 1.0            # s      robot immobile pendant chaque photo
