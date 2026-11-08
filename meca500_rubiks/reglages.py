# -*- coding: utf-8 -*-
"""Réglages du robot et géométrie de la cellule (repère de base du robot, en mm).

Géométrie réelle : pince MEGP 25E (manuel Mecademic, figure 1) montée avec sa plaque d'adaptation
standard, doigts imprimés (modeles_3D/doigts), socle Cube_holder.stl (modeles_3D/socle).
"""

ADRESSE_IP = "192.168.0.100"

# Vitesses. Limites du Meca500 R3 : SetCartLinVel ≤ 5000 mm/s (défaut 150), SetCartAngVel ≤ 1000 °/s
# (défaut 45), SetJointVel ≤ 100 % (défaut 25 %) ; articulations J1…J6 : 150, 150, 180, 300, 300, 500 °/s.
# Historique : 20 mm/s, 30 °/s, 10 % (premiers essais) ; 5000 mm/s, 1000 °/s, 100 % le 7/11/2026 :
# cube résolu en 2 min 17 s (61 étapes), sans glissement.
VITESSE_LINEAIRE = 5000.0    # mm/s
VITESSE_ANGULAIRE = 1000.0   # °/s
VITESSE_ARTICULAIRE = 100.0  # %

# Accélérations (% du maximum) : sur nos petits trajets (30 à 80 mm, 90°), le robot n'atteint presque
# jamais la vitesse réglée ci-dessus ; c'est l'ACCÉLÉRATION qui fixe la durée des déplacements.
# Valeurs par défaut du Meca500 : SetCartAcc 50 %, SetJointAcc 80 %. Monter par paliers (100, 150…)
# en surveillant que le cube ne glisse pas dans la pince (voir la doc Mecademic pour le maximum).
ACCELERATION_CARTESIENNE = 100.0   # %   (MoveLin)
ACCELERATION_ARTICULAIRE = 100.0   # %   (MovePose)

# Pince. Vitesse des doigts : 40 % par défaut sur le Meca500.
VITESSE_PINCE = 100.0        # %
# Le robot repart dès que la pince a fini de s'ouvrir ou de se fermer (WaitGripperMoveCompletion :
# fin de course ou cube tenu ; firmware ≥ 9.1, vérifié à la connexion). Si ATTENDRE_FIN_PINCE = False,
# ou firmware trop ancien : pause fixe de DUREE_PINCE après chaque ouverture / fermeture.
ATTENDRE_FIN_PINCE = True
DUREE_PINCE = 0.5            # s

# Rotations de la pince (autour de la verticale, poses.pose) où elle peut saisir le cube. Le socle est
# symétrique sur ses 4 côtés et les 2 doigts sont identiques : prise à -90°, 0° ou +90° équivalente.
# La pince ne sort jamais de [-90°, +90°] (un demi-tour va de +90° à -90°) : J6 reste loin des ±180°
# permis par le câble de la pince.
ROTATIONS_PINCE = (-90.0, 0.0, 90.0)

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
H_ATTENTE = 77.0             # position haute / d'attente : bas des patins 15 mm au-dessus du cube

# Bascule : la pince prend le cube penchée à 45°, le tourne de 90°, le repose penchée de l'autre côté.
# (Pince couchée à 90° : hors de portée du robot et collision avec les mors du socle.)
INCLINAISON = 45.0           # °
ROTATION_BASCULE = 90.0      # ° : pendant la bascule, la pince tourne pour serrer les faces avant / arrière
#                              (J6 ≈ -90°, le câble reste dans sa plage)
DECALAGE_BASCULE = 10.0      # cube tenu 10 mm plus bas dans les patins (couches du milieu et du haut) :
#                              sinon les bras des doigts touchent les coins du haut en penchant à 45°
RECUL_BASCULE = 40.0         # approche / dégagement le long de l'axe de la pince penchée

# Présentation des faces à la caméra (presenter_faces) : le cube est posé sur la table,
# à droite du socle (vu depuis le robot) ; la caméra est encore plus à droite et regarde vers le socle.
TABLE = (170.0, -110.0, 0.0)  # point de pose du cube sur la table : centre de sa face du dessous (x, y, z)
DUREE_PHOTO = 1.0            # s      robot immobile pendant chaque photo
