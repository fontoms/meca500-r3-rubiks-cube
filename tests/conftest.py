# -*- coding: utf-8 -*-
"""
Configuration commune des tests.

- Les tests marqués « robodk » / « simulation » sont ignorés si RoboDK n'est pas ouvert.
- FauxRobot : remplace le Meca500 ; il note chaque commande reçue au lieu de bouger.
"""
import socket

import pytest


def robodk_ouvert(port=20500):
    try:
        with socket.create_connection(("localhost", port), timeout=0.5):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(config, items):
    if robodk_ouvert():
        return
    saut = pytest.mark.skip(reason="RoboDK n'est pas ouvert (ouvre Rubiks_Meca500.rdk puis relance)")
    for item in items:
        if "robodk" in item.keywords or "simulation" in item.keywords:
            item.add_marker(saut)


class FauxRobot:
    """Accepte n'importe quelle commande mecademicpy et la note : self.commandes = [(nom, args), ...]."""

    def __init__(self):
        self.commandes = []

    def __getattr__(self, nom):
        if nom.startswith("_"):
            raise AttributeError(nom)
        return lambda *args: self.commandes.append((nom, args))

    def noms(self):
        return [nom for nom, _ in self.commandes]

    def poses(self):
        """Poses envoyées par MoveLin / MovePose, dans l'ordre."""
        return [args for nom, args in self.commandes if nom in ("MoveLin", "MovePose")]


@pytest.fixture
def robot():
    return FauxRobot()
