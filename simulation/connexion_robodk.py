# -*- coding: utf-8 -*-
"""
Connexion unique à RoboDK, partagée par tous les modules de la simulation.

RoboDK doit être ouvert (avec la station Rubiks_Meca500.rdk) : la connexion se fait au premier
import de ce module, sur localhost:20500. Ça marche aussi bien depuis RoboDK (programmes de la
station) que depuis PyCharm ou un terminal.
"""
from robodk.robolink import Robolink

RDK = Robolink()


def joignable(adresse="localhost", port=20500, delai=0.5):
    """True si un RoboDK écoute sur ce port (sans le lancer, contrairement à Robolink())."""
    import socket
    try:
        with socket.create_connection((adresse, port), timeout=delai):
            return True
    except OSError:
        return False
