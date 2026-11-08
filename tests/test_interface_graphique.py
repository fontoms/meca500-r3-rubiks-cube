import os
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

import interface_graphique
from meca500_rubiks import resolution, vision_capture


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    return app


def attendre(condition, timeout=3.0):
    limite = time.monotonic() + timeout
    while not condition() and time.monotonic() < limite:
        QTest.qWait(10)
    assert condition()


@pytest.mark.parametrize("automatique", [False, True])
def test_travail_resolution_respecte_le_mode_et_la_vitesse(monkeypatch, tmp_path, automatique):
    evenements = []
    cubestring_path = tmp_path / "cubestring.txt"
    cubestring_path.write_text("cube lu", encoding="utf-8")
    robot = SimpleNamespace(WaitIdle=lambda timeout: evenements.append(("attente", timeout)))
    worker = interface_graphique.TravailResolution()
    plans = []

    monkeypatch.setattr(vision_capture, "CUBESTRING_PATH", cubestring_path)
    monkeypatch.setattr(resolution, "charger_solveur", lambda: evenements.append("solveur"))
    monkeypatch.setattr(resolution, "verifier_cubestring",
                        lambda cubestring: evenements.append(("verifier", cubestring)) or "cube valide")
    monkeypatch.setattr(
        resolution, "meilleure_solution",
        lambda cubestring:
        evenements.append(("plan", cubestring)) or ([("R", 1)], [("tourner_haut", -90, 0)]))
    monkeypatch.setattr(resolution, "ecrire", lambda coups: "R")
    monkeypatch.setattr(resolution, "nombre_de_prises", lambda etapes: 1)
    monkeypatch.setattr(resolution, "duree_plan", lambda etapes: 12.0)
    monkeypatch.setattr(resolution, "decrire", lambda etape: "tourner_haut_droite")
    monkeypatch.setattr(
        interface_graphique.rubiks, "connecter",
        lambda facteur_vitesse: evenements.append(("connexion", facteur_vitesse)) or robot)
    monkeypatch.setattr(
        interface_graphique.rubiks, "presenter_faces",
        lambda robot_connecte, selection, callback, afficher_fenetre, callback_erreur_vision:
        evenements.append(("scan", robot_connecte, selection, callable(callback), afficher_fenetre)))
    monkeypatch.setattr(
        resolution, "executer",
        lambda robot_connecte, etapes, afficher: evenements.append(("execution", etapes)))
    monkeypatch.setattr(
        interface_graphique.rubiks, "deconnecter",
        lambda robot_connecte: evenements.append(("deconnexion", robot_connecte)))
    worker.plan_pret.connect(lambda texte, a_mouvements, auto: plans.append((texte, a_mouvements, auto)))

    worker.scanner(2, [0, 2], 0.75, automatique, 700, 7)

    assert ("connexion", 0.75) in evenements
    assert ("plan", "cube valide") in evenements
    assert ("scan", robot, (2, [0, 2], 700), True, False) in evenements
    assert plans and plans[0][1:] == (True, automatique)
    if automatique:
        assert any(evenement[0] == "execution" for evenement in evenements)
        assert ("deconnexion", robot) in evenements
    else:
        assert not any(evenement[0] == "execution" for evenement in evenements)
        assert worker.robot is robot
        worker.resoudre()
        assert any(evenement[0] == "execution" for evenement in evenements)
        assert ("deconnexion", robot) in evenements


def test_interface_affiche_camera_et_met_le_plan_en_validation(monkeypatch, application):
    class FauxFlux:
        def __init__(self, index, backend):
            self.index = index
            self.backend = backend

        def read(self):
            return np.zeros((2, 2, 3), dtype=np.uint8)

        def release(self):
            pass

    backend = interface_graphique.cv2.CAP_DSHOW
    monkeypatch.setattr(vision_capture, "lister_cameras",
                        lambda backend: [(0, "Caméra intégrée", backend),
                                         (2, "Logitech C920", backend)])
    monkeypatch.setattr(
        vision_capture, "ouvrir_camera", lambda index, backend: FauxFlux(index, backend))

    fenetre = interface_graphique.InterfaceGraphique()
    try:
        attendre(lambda: fenetre.camera_combo.count() > 0)
        attendre(lambda: fenetre._camera_apercu_ouverte)
        assert fenetre.titre_camera_chrono.text() == (
            "Remplacer les solutions chères généralistes par des solutions basique adoptées dans l'industrie.")
        assert fenetre.centralWidget().layout().itemAt(0).widget() is fenetre.titre_camera_chrono
        assert fenetre.titre_camera_chrono.font().pointSize() >= 22
        assert fenetre.chrono_total_label.font().pointSize() >= 30
        assert fenetre.chrono_resolution_label.font().pointSize() >= 30
        assert "#ffffff" in fenetre.styleSheet()
        assert "Caméra intégrée" in fenetre.camera_combo.itemText(0)
        assert fenetre.vitesse_spin.value() == 10
        assert not fenetre.automatique.isChecked()
        assert fenetre.lancer_button.text() == "Lancer le scan"

        fenetre._plan_pret("Solution prête", True, False)
        QTest.qWait(400)
        assert fenetre.lancer_button.text() == "Valider et résoudre"
        assert fenetre.lancer_button.isEnabled()
    finally:
        fenetre.close()
        attendre(lambda: not fenetre._thread.isRunning()
                 and not fenetre._thread_apercu.isRunning())


def test_chronometres_total_et_resolution(monkeypatch, application):
    monkeypatch.setattr(vision_capture, "lister_cameras", lambda backend: [])
    maintenant = [100.0]
    monkeypatch.setattr(interface_graphique, "monotonic", lambda: maintenant[0])
    fenetre = interface_graphique.InterfaceGraphique()
    try:
        fenetre._demarrer_chronos()
        maintenant[0] = 106.0
        fenetre._mettre_a_jour_chronos()
        assert fenetre.chrono_total_label.text() == "00:06"
        assert fenetre.chrono_resolution_label.text() == "00:00"

        fenetre._scan_termine()
        maintenant[0] = 500.0
        fenetre._mettre_a_jour_chronos()
        assert fenetre.chrono_total_label.text() == "00:06"

        fenetre._resolution_demarre()
        maintenant[0] = 504.0
        fenetre._mettre_a_jour_chronos()
        assert fenetre.chrono_total_label.text() == "00:10"
        assert fenetre.chrono_resolution_label.text() == "00:04"

        fenetre._resolution_terminee()
        maintenant[0] = 510.0
        fenetre._mettre_a_jour_chronos()
        assert fenetre.chrono_total_label.text() == "00:16"
        assert fenetre.chrono_resolution_label.text() == "00:04"

        fenetre._arreter_chronos()
    finally:
        fenetre.close()
        attendre(lambda: not fenetre._thread.isRunning()
                 and not fenetre._thread_apercu.isRunning())


def test_flux_camera_continue_pendant_la_resolution(monkeypatch, application):
    compteur = [0]
    verrou = threading.Lock()
    backend = interface_graphique.cv2.CAP_DSHOW
    robot = SimpleNamespace(WaitIdle=lambda timeout: None)

    class FauxFlux:
        index = 0

        def __init__(self, backend):
            self.backend = backend

        def read(self):
            with verrou:
                compteur[0] += 1
            return np.zeros((2, 2, 3), dtype=np.uint8)

        def release(self):
            pass

    monkeypatch.setattr(vision_capture, "lister_cameras",
                        lambda backend: [(0, "Caméra intégrée", backend)])
    monkeypatch.setattr(vision_capture, "ouvrir_camera",
                        lambda index, backend: FauxFlux(backend))

    mesures = {}

    def executer(robot_connecte, etapes, afficher):
        with verrou:
            mesures["avant"] = compteur[0]
        time.sleep(0.5)
        with verrou:
            mesures["apres"] = compteur[0]

    monkeypatch.setattr(resolution, "executer", executer)
    monkeypatch.setattr(interface_graphique.rubiks, "deconnecter", lambda robot: None)

    fenetre = interface_graphique.InterfaceGraphique()
    try:
        attendre(lambda: fenetre._camera_apercu_ouverte)
        fenetre._travail.robot = robot
        fenetre._travail.etapes = [("tourner_haut", -90, 0)]
        fenetre._operation_en_cours = True
        fenetre.demande_resolution.emit()
        attendre(lambda: "apres" in mesures)
        attendre(lambda: not fenetre._operation_en_cours)
        assert mesures["apres"] > mesures["avant"]
        assert fenetre._camera_apercu_ouverte
    finally:
        fenetre._operation_en_cours = False
        fenetre._robot_connecte = False
        fenetre.close()
        attendre(lambda: not fenetre._thread.isRunning()
                 and not fenetre._thread_apercu.isRunning())


def test_changement_rapide_de_camera_garde_le_dernier_choix(monkeypatch, application):
    cameras_ouvertes = []

    class FauxFlux:
        def __init__(self, index, backend):
            self.index = index
            self.backend = backend

        def read(self):
            return np.zeros((2, 2, 3), dtype=np.uint8)

        def release(self):
            pass

    backend = interface_graphique.cv2.CAP_DSHOW
    monkeypatch.setattr(
        vision_capture, "lister_cameras",
        lambda backend: [(0, "Caméra 0", backend), (1, "Caméra 1", backend),
                         (2, "Caméra 2", backend)])
    monkeypatch.setattr(
        vision_capture, "ouvrir_camera",
        lambda index, backend: cameras_ouvertes.append((index, backend)) or FauxFlux(index, backend))

    fenetre = interface_graphique.InterfaceGraphique()
    attendre(lambda: bool(cameras_ouvertes))
    assert cameras_ouvertes == [(0, backend)]

    fenetre.camera_combo.setCurrentIndex(1)
    fenetre.camera_combo.setCurrentIndex(2)
    QTest.qWait(400)
    assert cameras_ouvertes == [(0, backend), (2, backend)]

    fenetre.close()
    attendre(lambda: not fenetre._thread.isRunning()
             and not fenetre._thread_apercu.isRunning())


def test_point_entree_cree_et_lance_l_application(monkeypatch):
    evenements = []

    class FausseApplication:
        def __init__(self, arguments):
            evenements.append(("application", arguments))

        def setApplicationName(self, nom):
            evenements.append(("nom_application", nom))

        def exec(self):
            evenements.append("exec")
            return 0

    class FausseFenetre:
        def __init__(self):
            evenements.append("fenetre")

        def show(self):
            evenements.append("show")

    monkeypatch.setattr(interface_graphique, "QApplication", FausseApplication)
    monkeypatch.setattr(interface_graphique, "InterfaceGraphique", FausseFenetre)
    monkeypatch.setattr(interface_graphique.sys, "argv", ["interface_graphique.py"])

    assert interface_graphique.main() == 0
    assert evenements == [
        ("application", ["interface_graphique.py"]),
        ("nom_application", "Rubik's cube — Meca500 R3"),
        "fenetre",
        "show",
        "exec",
    ]
