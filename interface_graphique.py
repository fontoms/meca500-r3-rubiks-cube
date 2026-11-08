# -*- coding: utf-8 -*-
"""Interface graphique PyQt pour scanner et résoudre un Rubik's cube."""
import logging
import sys
import threading
from time import monotonic

import cv2
from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGroupBox,
                             QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                             QPushButton, QSlider, QSpinBox, QTextEdit,
                             QVBoxLayout, QWidget)

import meca500_rubiks as rubiks
from meca500_rubiks import resolution, vision_capture
from meca500_rubiks.reglages import VITESSE_GLOBALE

_LOG = logging.getLogger(__name__)


def _pixmap_image(frame, taille):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hauteur, largeur = rgb.shape[:2]
    image = QImage(rgb.data, largeur, hauteur, rgb.strides[0],
                   QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(image).scaled(
        taille, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


def _duree(secondes):
    return "%d min %02d s" % (secondes // 60, secondes % 60)


class TravailApercu(QObject):
    image = pyqtSignal(object, int)
    cameras_listees = pyqtSignal(int, object, str)
    apercu_ouvert = pyqtSignal(int)
    apercu_ferme = pyqtSignal(int)
    erreur = pyqtSignal(int, str)

    def __init__(self):
        super().__init__()
        self._camera = None
        self._timer = None
        self._generation = 0
        self._annulation = None
        self._lectures_echouees = 0

    @pyqtSlot(int, object)
    def lister_cameras(self, generation, backend):
        self._fermer_flux()
        self._generation = generation
        try:
            cameras = vision_capture.lister_cameras(backend)
        except (ImportError, vision_capture.ErreurCamera, cv2.error) as exc:
            self.cameras_listees.emit(generation, [], str(exc))
        else:
            self.cameras_listees.emit(generation, cameras, "")

    @pyqtSlot(int, object, int, object)
    def ouvrir(self, index, backend, generation, annulation):
        if annulation.is_set():
            return
        self._fermer_flux()
        self._generation = generation
        try:
            camera = vision_capture.ouvrir_camera(index, backend)
        except (ImportError, vision_capture.ErreurCamera, cv2.error) as exc:
            if not annulation.is_set():
                self.erreur.emit(generation, str(exc))
            return
        if annulation.is_set():
            camera.release()
            return
        self._camera = camera
        self._annulation = annulation
        self._lectures_echouees = 0
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.setInterval(33)
            self._timer.timeout.connect(self._lire)
        self._timer.start()
        self.apercu_ouvert.emit(generation)

    @pyqtSlot(int)
    def fermer(self, generation):
        self._generation = generation
        self._fermer_flux()
        self.apercu_ferme.emit(generation)

    def _lire(self):
        if self._camera is None:
            return
        generation = self._generation
        if self._annulation is not None and self._annulation.is_set():
            self._fermer_flux()
            return
        try:
            frame = self._camera.read()
        except (RuntimeError, cv2.error) as exc:
            self._fermer_flux()
            self.erreur.emit(generation, str(exc))
            return
        if self._annulation is not None and self._annulation.is_set():
            self._fermer_flux()
            return
        if frame is None:
            self._lectures_echouees += 1
            if self._lectures_echouees >= 10:
                self._fermer_flux()
                self.erreur.emit(generation, "La caméra ne fournit plus d'image.")
            return
        self._lectures_echouees = 0
        self.image.emit(frame.copy(), generation)

    def _fermer_flux(self):
        if self._annulation is not None:
            self._annulation.set()
            self._annulation = None
        if self._timer is not None:
            self._timer.stop()
        if self._camera is not None:
            camera, self._camera = self._camera, None
            try:
                camera.release()
            except cv2.error as exc:
                _LOG.exception("Échec de la libération de la caméra")
                self.erreur.emit(self._generation, str(exc))


class TravailResolution(QObject):
    image = pyqtSignal(object, int)
    etat = pyqtSignal(str)
    plan_pret = pyqtSignal(str, bool, bool)
    termine = pyqtSignal(str)
    erreur = pyqtSignal(str)
    connexion = pyqtSignal(bool)
    deconnexion_terminee = pyqtSignal()
    scan_termine = pyqtSignal()
    avertissement_vision = pyqtSignal(str, int)
    resolution_demarre = pyqtSignal()
    resolution_terminee = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.robot = None
        self.etapes = None
        self._generation_apercu = 0

    @pyqtSlot(int, object, float, bool, int, int)
    def scanner(self, index_camera, cameras_disponibles, facteur_vitesse,
                automatique, backend_camera, generation_apercu):
        if self.robot is not None:
            self.erreur.emit("Une résolution est déjà en cours.")
            return

        self._generation_apercu = generation_apercu
        try:
            self.etat.emit("Chargement du solveur…")
            resolution.charger_solveur()
            self.etat.emit("Connexion au robot…")
            self.robot = rubiks.connecter(facteur_vitesse=facteur_vitesse)
            self.connexion.emit(True)

            self.etat.emit("Scan des six faces…")
            selection_camera = (index_camera, list(cameras_disponibles), backend_camera)
            rubiks.presenter_faces(
                self.robot, selection_camera, self._emettre_image, False,
                self._emettre_avertissement_vision)
            self.scan_termine.emit()

            self.etat.emit("Calcul du plan de résolution…")
            cubestring = resolution.verifier_cubestring(
                vision_capture.CUBESTRING_PATH.read_text(encoding="utf-8"))
            resultat = resolution.meilleure_solution(cubestring)
            if resultat is None:
                raise resolution.ErreurResolution("Aucun plan de résolution n'a été calculé.")
            coups, self.etapes = resultat
            self.plan_pret.emit(self._decrire_plan(cubestring, coups, self.etapes),
                                bool(self.etapes), automatique)

            if not self.etapes:
                self._terminer("Le cube est déjà résolu.")
            elif automatique:
                self.resoudre()
            else:
                self.etat.emit("Scan terminé. Vérifie le plan, puis valide la résolution.")
        except Exception as exc:
            _LOG.exception("Échec du scan ou du calcul de résolution")
            self.erreur.emit("Échec du scan ou du calcul : %s" % exc)
            self._terminer("Opération interrompue.")

    @pyqtSlot()
    def resoudre(self):
        if self.robot is None or self.etapes is None:
            self.erreur.emit("Aucun plan prêt à exécuter.")
            return

        self.resolution_demarre.emit()
        self.etat.emit("Résolution en cours…")
        try:
            resolution.executer(self.robot, self.etapes, afficher=self.etat.emit)
            self.robot.WaitIdle(120)
            self.resolution_terminee.emit()
            self._terminer("Cube résolu.")
        except Exception as exc:
            _LOG.exception("Échec pendant l'exécution de la résolution")
            self.erreur.emit("Échec de l'exécution : %s" % exc)
            self._terminer("Résolution interrompue.")

    @pyqtSlot()
    def deconnecter_pour_fermeture(self):
        self._deconnecter_robot()
        self.deconnexion_terminee.emit()

    def _emettre_image(self, frame):
        self.image.emit(frame.copy(), self._generation_apercu)

    def _emettre_avertissement_vision(self, erreur):
        self.avertissement_vision.emit(str(erreur), self._generation_apercu)

    def _deconnecter_robot(self):
        if self.robot is None:
            return
        robot, self.robot = self.robot, None
        try:
            rubiks.deconnecter(robot)
        except Exception as exc:
            _LOG.exception("Échec de la déconnexion du robot")
            self.erreur.emit("Erreur pendant la déconnexion : %s" % exc)
        finally:
            self.connexion.emit(False)

    def _terminer(self, message):
        self._deconnecter_robot()
        self.etapes = None
        self.termine.emit(message)

    @staticmethod
    def _decrire_plan(cubestring, coups, etapes):
        lignes = [
            "Cubestring après le scan :",
            cubestring,
            "",
            "Solution (%d coups) : %s" % (len(coups), resolution.ecrire(coups)),
            "Robot : %d prises, durée estimée %s" %
            (resolution.nombre_de_prises(etapes), _duree(resolution.duree_plan(etapes))),
        ]
        if etapes:
            lignes.extend(("", "Mouvements :"))
            lignes.extend("%2d. %s" % (i, resolution.decrire(etape))
                          for i, etape in enumerate(etapes, 1))
        return "\n".join(lignes)


class InterfaceGraphique(QMainWindow):
    demande_scan = pyqtSignal(int, object, float, bool, int, int)
    demande_resolution = pyqtSignal()
    demande_deconnexion = pyqtSignal()
    demande_liste_cameras = pyqtSignal(int, object)
    demande_ouverture_apercu = pyqtSignal(int, object, int, object)
    demande_fermeture_apercu = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rubik's cube — Meca500 R3")
        self.resize(900, 760)
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #ffffff; color: #222222; }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #d6dbe1;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 8px;
            }
            QGroupBox::title { left: 10px; padding: 0 4px; }
            QLabel#apercuCamera {
                background-color: #f3f5f7;
                color: #40464d;
                border: 1px solid #d6dbe1;
            }
            QLabel#chrono { color: #1f5f99; background-color: #ffffff; }
            QComboBox, QSpinBox, QTextEdit, QPushButton {
                background-color: #ffffff;
                color: #222222;
                border: 1px solid #cbd2d9;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover { background-color: #f1f5f8; }
            QCheckBox { background-color: #ffffff; }
        """)

        self._cameras = []
        self._robot_connecte = False
        self._operation_en_cours = False
        self._validation_en_attente = False
        self._fermeture_demandee = False
        self._fermeture_finalisee = False
        self._temps_total = 0.0
        self._debut_total = None
        self._temps_resolution = 0.0
        self._debut_resolution = None
        self._generation_apercu = 0
        self._camera_apercu_ouverte = False
        self._ouverture_apercu_demandee = None
        self._suite_apres_fermeture = None
        self._annulation_apercu = None

        self._construire_interface()
        self._timer_apercu = QTimer(self)
        self._timer_apercu.setSingleShot(True)
        self._timer_apercu.setInterval(180)
        self._timer_apercu.timeout.connect(self._demander_ouverture_apercu)
        self._chrono_timer = QTimer(self)
        self._chrono_timer.setInterval(1000)
        self._chrono_timer.timeout.connect(self._mettre_a_jour_chronos)

        self._thread = QThread(self)
        self._travail = TravailResolution()
        self._travail.moveToThread(self._thread)
        self._thread.finished.connect(self._travail.deleteLater)
        self.demande_scan.connect(self._travail.scanner)
        self.demande_resolution.connect(self._travail.resoudre)
        self.demande_deconnexion.connect(self._travail.deconnecter_pour_fermeture)
        self._travail.image.connect(self._afficher_image)
        self._travail.etat.connect(self.etat_label.setText)
        self._travail.plan_pret.connect(self._plan_pret)
        self._travail.termine.connect(self._operation_terminee)
        self._travail.erreur.connect(self._afficher_erreur)
        self._travail.connexion.connect(self._connexion_changee)
        self._travail.resolution_demarre.connect(self._resolution_demarre)
        self._travail.resolution_terminee.connect(self._resolution_terminee)
        self._travail.avertissement_vision.connect(self._avertissement_vision)
        self._travail.scan_termine.connect(self._scan_termine)
        self._travail.deconnexion_terminee.connect(self._fermer_apres_deconnexion)
        self._thread.start()

        self._thread_apercu = QThread(self)
        self._travail_apercu = TravailApercu()
        self._travail_apercu.moveToThread(self._thread_apercu)
        self._thread_apercu.finished.connect(self._travail_apercu.deleteLater)
        self.demande_liste_cameras.connect(self._travail_apercu.lister_cameras)
        self.demande_ouverture_apercu.connect(self._travail_apercu.ouvrir)
        self.demande_fermeture_apercu.connect(self._travail_apercu.fermer)
        self._travail_apercu.image.connect(self._afficher_image)
        self._travail_apercu.cameras_listees.connect(self._cameras_listees)
        self._travail_apercu.apercu_ouvert.connect(self._apercu_ouvert)
        self._travail_apercu.apercu_ferme.connect(self._apercu_ferme)
        self._travail_apercu.erreur.connect(self._erreur_apercu)
        self._thread_apercu.start()

        self._rafraichir_cameras()

    def _construire_interface(self):
        page = QWidget(self)
        self.setCentralWidget(page)
        layout = QVBoxLayout(page)

        groupe_camera = QGroupBox("Caméra")
        camera_layout = QVBoxLayout(groupe_camera)
        choix_layout = QHBoxLayout()
        self.camera_combo = QComboBox()
        self.rafraichir_button = QPushButton("Actualiser")
        choix_layout.addWidget(self.camera_combo, 1)
        choix_layout.addWidget(self.rafraichir_button)
        camera_layout.addLayout(choix_layout)

        self.titre_camera_chrono = QLabel(
            "Remplacer les solutions chères généralistes par des solutions basique adoptées dans l'industrie.")
        self.titre_camera_chrono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.titre_camera_chrono.setWordWrap(True)
        police_titre = QFont()
        police_titre.setPointSize(22)
        police_titre.setBold(True)
        self.titre_camera_chrono.setFont(police_titre)
        layout.addWidget(self.titre_camera_chrono)

        zone_camera_chrono = QHBoxLayout()
        self.apercu = QLabel("Choisis une caméra pour afficher l'aperçu.")
        self.apercu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.apercu.setMinimumSize(640, 360)
        self.apercu.setObjectName("apercuCamera")
        zone_camera_chrono.addWidget(self.apercu, 4)

        panneau_chrono = QWidget()
        disposition_chrono = QVBoxLayout(panneau_chrono)
        disposition_chrono.addStretch()
        titre_total = QLabel("Temps total")
        titre_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disposition_chrono.addWidget(titre_total)
        self.chrono_total_label = QLabel("00:00")
        self.chrono_total_label.setObjectName("chrono")
        self.chrono_total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chrono_total_label.setMinimumWidth(190)
        police_chrono = QFont()
        police_chrono.setPointSize(32)
        police_chrono.setBold(True)
        self.chrono_total_label.setFont(police_chrono)
        disposition_chrono.addWidget(self.chrono_total_label)
        titre_resolution = QLabel("Temps résolution")
        titre_resolution.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disposition_chrono.addWidget(titre_resolution)
        self.chrono_resolution_label = QLabel("00:00")
        self.chrono_resolution_label.setObjectName("chrono")
        self.chrono_resolution_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chrono_resolution_label.setMinimumWidth(190)
        self.chrono_resolution_label.setFont(police_chrono)
        disposition_chrono.addWidget(self.chrono_resolution_label)
        disposition_chrono.addStretch()
        zone_camera_chrono.addWidget(panneau_chrono, 1)
        camera_layout.addLayout(zone_camera_chrono)
        layout.addWidget(groupe_camera)

        groupe_vitesse = QGroupBox("Vitesse du robot")
        vitesse_layout = QHBoxLayout(groupe_vitesse)
        self.vitesse_slider = QSlider(Qt.Orientation.Horizontal)
        self.vitesse_slider.setRange(1, 100)
        self.vitesse_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.vitesse_slider.setTickInterval(10)
        self.vitesse_spin = QSpinBox()
        self.vitesse_spin.setRange(1, 100)
        self.vitesse_spin.setSuffix(" %")
        self.vitesse_spin.setValue(round(VITESSE_GLOBALE * 100))
        self.vitesse_slider.setValue(self.vitesse_spin.value())
        self.vitesse_slider.valueChanged.connect(self.vitesse_spin.setValue)
        self.vitesse_spin.valueChanged.connect(self.vitesse_slider.setValue)
        vitesse_layout.addWidget(QLabel("Limites du Meca500 R3 :"))
        vitesse_layout.addWidget(self.vitesse_slider, 1)
        vitesse_layout.addWidget(self.vitesse_spin)
        layout.addWidget(groupe_vitesse)

        self.automatique = QCheckBox(
            "Tout faire : résoudre automatiquement après le scan, sans validation intermédiaire")
        self.automatique.setToolTip(
            "Décochée : le plan s'affiche après le scan et tu le valides avant l'exécution.")
        layout.addWidget(self.automatique)

        self.plan = QTextEdit()
        self.plan.setReadOnly(True)
        self.plan.setPlaceholderText("Le cubestring et le plan apparaîtront après le scan.")
        self.plan.setMinimumHeight(190)
        layout.addWidget(self.plan, 1)

        self.etat_label = QLabel("Prêt.")
        layout.addWidget(self.etat_label)
        self.lancer_button = QPushButton("Lancer le scan")
        self.lancer_button.setMinimumHeight(42)
        layout.addWidget(self.lancer_button)

        self.camera_combo.currentIndexChanged.connect(lambda _: self._camera_selectionnee())
        self.rafraichir_button.clicked.connect(self._rafraichir_cameras)
        self.automatique.toggled.connect(self._mettre_a_jour_libelle)
        self.lancer_button.clicked.connect(self._lancer)

    def _rafraichir_cameras(self):
        if self._operation_en_cours or self._validation_en_attente:
            return
        ancienne = self.camera_combo.currentData()
        self._ancien_index_camera = ancienne[0] if ancienne else None
        if self._annulation_apercu is not None:
            self._annulation_apercu.set()
            self._annulation_apercu = None
        self.camera_combo.setEnabled(False)
        self.rafraichir_button.setEnabled(False)
        self.lancer_button.setEnabled(False)
        self.apercu.setText("Détection des caméras…")
        self.etat_label.setText("Recherche des caméras disponibles…")
        self._generation_apercu += 1
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else None
        self.demande_liste_cameras.emit(self._generation_apercu, backend)

    @pyqtSlot(int, object, str)
    def _cameras_listees(self, generation, cameras, erreur):
        if generation != self._generation_apercu or self._fermeture_demandee:
            return
        self._cameras = cameras
        self._camera_apercu_ouverte = False
        self._ouverture_apercu_demandee = None
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        index_cameras = [index for index, _, _ in cameras]
        for index, nom, backend in cameras:
            self.camera_combo.addItem(
                "%s (index %s)" % (nom, index), (index, index_cameras, backend))
        if not cameras:
            self.camera_combo.addItem(
                "Erreur : %s" % erreur if erreur else "Aucune caméra détectée", None)
        elif self._ancien_index_camera in index_cameras:
            self.camera_combo.setCurrentIndex(index_cameras.index(self._ancien_index_camera))
        self.camera_combo.blockSignals(False)
        self._mettre_a_jour_controles(True)
        if cameras:
            self._demander_ouverture_apercu()
        else:
            self.apercu.setText(erreur or "Aucune caméra détectée.")
            self.etat_label.setText(erreur or "Aucune caméra détectée.")
            self.lancer_button.setEnabled(False)

    def _camera_selectionnee(self):
        if self._operation_en_cours or self._validation_en_attente or self._fermeture_demandee:
            return
        self._generation_apercu += 1
        if self._annulation_apercu is not None:
            self._annulation_apercu.set()
            self._annulation_apercu = None
        self._ouverture_apercu_demandee = None
        self._camera_apercu_ouverte = False
        self.apercu.setPixmap(QPixmap())
        self.apercu.setText("Sélection de caméra…")
        self.lancer_button.setEnabled(False)
        self._timer_apercu.start()

    def _demander_ouverture_apercu(self):
        if self._operation_en_cours or self._fermeture_demandee:
            return
        selection = self.camera_combo.currentData()
        if selection is None:
            return
        index_camera, index_cameras, backend = selection
        if self._camera_apercu_ouverte and self._ouverture_apercu_demandee == (
                index_camera, backend):
            self.lancer_button.setEnabled(bool(self._cameras))
            return
        self._generation_apercu += 1
        generation = self._generation_apercu
        self._ouverture_apercu_demandee = (index_camera, backend)
        self._camera_apercu_ouverte = False
        self.apercu.setPixmap(QPixmap())
        self.apercu.setText("Ouverture de la caméra…")
        if not self._validation_en_attente:
            self.lancer_button.setEnabled(False)
        if self._annulation_apercu is not None:
            self._annulation_apercu.set()
        self._annulation_apercu = threading.Event()
        self.demande_ouverture_apercu.emit(
            index_camera, backend, generation, self._annulation_apercu)

    def _demander_fermeture_apercu(self, suite=None):
        self._timer_apercu.stop()
        self._generation_apercu += 1
        generation = self._generation_apercu
        self._camera_apercu_ouverte = False
        self._ouverture_apercu_demandee = None
        if self._annulation_apercu is not None:
            self._annulation_apercu.set()
            self._annulation_apercu = None
        self._suite_apres_fermeture = suite
        self.demande_fermeture_apercu.emit(generation)

    @pyqtSlot(int)
    def _apercu_ouvert(self, generation):
        if generation != self._generation_apercu:
            return
        selection = self.camera_combo.currentData()
        if selection is None:
            return
        self._camera_apercu_ouverte = True
        self._ouverture_apercu_demandee = (selection[0], selection[2])
        self.apercu.setText("")
        if not self._validation_en_attente:
            self.lancer_button.setEnabled(bool(self._cameras))
            self.etat_label.setText("Aperçu caméra prêt.")

    @pyqtSlot(int)
    def _apercu_ferme(self, generation):
        if generation != self._generation_apercu:
            return
        self._camera_apercu_ouverte = False
        self._ouverture_apercu_demandee = None
        self._annulation_apercu = None
        self.apercu.setPixmap(QPixmap())
        suite = self._suite_apres_fermeture
        self._suite_apres_fermeture = None
        if suite is not None:
            suite(generation)

    @pyqtSlot(int, str)
    def _erreur_apercu(self, generation, message):
        if generation != self._generation_apercu:
            return
        self._camera_apercu_ouverte = False
        self._ouverture_apercu_demandee = None
        self._annulation_apercu = None
        self.apercu.setPixmap(QPixmap())
        self.apercu.setText("Aperçu indisponible : %s" % message)
        self.etat_label.setText("Erreur caméra : %s" % message)
        if not self._validation_en_attente:
            self.lancer_button.setEnabled(False)

    @pyqtSlot(object, int)
    def _afficher_image(self, frame, generation):
        if generation == self._generation_apercu:
            self.apercu.setPixmap(_pixmap_image(frame, self.apercu.size()))

    def _mettre_a_jour_libelle(self, automatique):
        if not self._operation_en_cours and not self._validation_en_attente:
            self.lancer_button.setText(
                "Lancer scan + résolution" if automatique else "Lancer le scan")

    def _mettre_a_jour_controles(self, actif):
        self.camera_combo.setEnabled(actif and bool(self._cameras))
        self.rafraichir_button.setEnabled(actif)
        self.vitesse_slider.setEnabled(actif)
        self.vitesse_spin.setEnabled(actif)
        self.automatique.setEnabled(actif)

    def _demarrer_chronos(self):
        self._temps_total = 0.0
        self._debut_total = monotonic()
        self._temps_resolution = 0.0
        self._debut_resolution = None
        self._chrono_timer.start()
        self._mettre_a_jour_chronos()

    @pyqtSlot()
    def _scan_termine(self):
        if self._debut_total is not None:
            self._temps_total += monotonic() - self._debut_total
            self._debut_total = None
            if self._debut_resolution is None:
                self._chrono_timer.stop()
            self._mettre_a_jour_chronos()

    def _reprendre_chrono_total(self):
        if self._debut_total is None:
            self._debut_total = monotonic()
        self._chrono_timer.start()

    @pyqtSlot()
    def _resolution_demarre(self):
        self._reprendre_chrono_total()
        if self._debut_resolution is None:
            self._debut_resolution = monotonic()
        self._mettre_a_jour_chronos()

    @pyqtSlot()
    def _resolution_terminee(self):
        if self._debut_resolution is not None:
            self._temps_resolution += monotonic() - self._debut_resolution
            self._debut_resolution = None
            self._mettre_a_jour_chronos()

    def _arreter_chronos(self):
        maintenant = monotonic()
        if self._debut_total is not None:
            self._temps_total += maintenant - self._debut_total
            self._debut_total = None
        if self._debut_resolution is not None:
            self._temps_resolution += maintenant - self._debut_resolution
            self._debut_resolution = None
        self._chrono_timer.stop()
        self._mettre_a_jour_chronos()

    def _mettre_a_jour_chronos(self):
        maintenant = monotonic()
        total = int(self._temps_total)
        if self._debut_total is not None:
            total += int(maintenant - self._debut_total)
        resolution = int(self._temps_resolution)
        if self._debut_resolution is not None:
            resolution += int(maintenant - self._debut_resolution)
        self.chrono_total_label.setText(self._formater_chrono(total))
        self.chrono_resolution_label.setText(self._formater_chrono(resolution))

    @staticmethod
    def _formater_chrono(total):
        heures, reste = divmod(total, 3600)
        minutes, secondes = divmod(reste, 60)
        return ("%02d:%02d:%02d" % (heures, minutes, secondes)
                if heures else "%02d:%02d" % (minutes, secondes))

    def _lancer(self):
        if self._validation_en_attente:
            reponse = QMessageBox.question(
                self, "Valider la résolution",
                "Le scan est terminé. Exécuter le plan affiché ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reponse != QMessageBox.StandardButton.Yes:
                return
            self._validation_en_attente = False
            self._operation_en_cours = True
            self._mettre_a_jour_controles(False)
            self.lancer_button.setText("Résolution en cours…")
            self.lancer_button.setEnabled(False)
            self.etat_label.setText("Exécution du plan validé…")
            self.demande_resolution.emit()
            return

        selection = self.camera_combo.currentData()
        if selection is None:
            QMessageBox.warning(self, "Caméra manquante", "Sélectionne une caméra avant de lancer.")
            return

        index_camera, cameras_disponibles, backend = selection
        facteur_vitesse = self.vitesse_spin.value() / 100
        automatique = self.automatique.isChecked()
        mode = "scan et résolution automatique" if automatique else "scan des faces"
        message = (
            "Caméra : %s\nVitesse : %d %% des limites R3\n\n"
            "Le robot va démarrer le %s. Vérifie le cube et garde l'arrêt d'urgence à portée."
            % (self.camera_combo.currentText(), self.vitesse_spin.value(), mode))
        reponse = QMessageBox.question(
            self, "Confirmer le lancement", message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reponse != QMessageBox.StandardButton.Yes:
            return

        self._operation_en_cours = True
        self._mettre_a_jour_controles(False)
        self.plan.clear()
        self.lancer_button.setText("Scan en cours…")
        self.lancer_button.setEnabled(False)
        self.etat_label.setText("Préparation du scan…")

        def lancer_scan(generation):
            self._demarrer_chronos()
            self.demande_scan.emit(
                index_camera, cameras_disponibles, facteur_vitesse,
                automatique, backend, generation)

        self._demander_fermeture_apercu(lancer_scan)

    @pyqtSlot(str, bool, bool)
    def _plan_pret(self, texte, contient_mouvements, automatique):
        self.plan.setPlainText(texte)
        if automatique:
            self.etat_label.setText("Plan calculé. Résolution automatique en cours…")
            self._demander_ouverture_apercu()
            self._demander_ouverture_apercu()
            return
        if contient_mouvements:
            self._validation_en_attente = True
            self._operation_en_cours = False
            self._mettre_a_jour_controles(False)
            self.lancer_button.setText("Valider et résoudre")
            self.lancer_button.setEnabled(True)
            self.etat_label.setText("Scan terminé. Vérifie le plan avant de le lancer.")
            self._demander_ouverture_apercu()

    @pyqtSlot(str)
    def _operation_terminee(self, message):
        self._arreter_chronos()
        self._operation_en_cours = False
        self._validation_en_attente = False
        self._mettre_a_jour_controles(True)
        self.lancer_button.setText(
            "Lancer scan + résolution" if self.automatique.isChecked() else "Lancer le scan")
        self.lancer_button.setEnabled(bool(self._cameras))
        self.etat_label.setText(message)
        if not self._fermeture_demandee:
            self._demander_ouverture_apercu()

    @pyqtSlot(str)
    def _afficher_erreur(self, message):
        self.etat_label.setText(message)
        QMessageBox.critical(self, "Erreur", message)

    @pyqtSlot(str, int)
    def _avertissement_vision(self, message, generation):
        if generation == self._generation_apercu:
            self.etat_label.setText(
                "Détection indisponible; flux brut conservé : %s" % message)

    @pyqtSlot(bool)
    def _connexion_changee(self, connecte):
        self._robot_connecte = connecte

    @pyqtSlot()
    def _fermer_apres_deconnexion(self):
        self._robot_connecte = False
        self._terminer_fermeture()

    def closeEvent(self, evenement):
        if self._fermeture_finalisee:
            evenement.accept()
            return

        if self._operation_en_cours:
            QMessageBox.warning(
                self, "Opération en cours",
                "Attends la fin du mouvement du robot avant de fermer l'interface.")
            evenement.ignore()
            return

        self._arreter_chronos()

        if self._robot_connecte and not self._fermeture_demandee:
            reponse = QMessageBox.question(
                self, "Robot connecté",
                "Déconnecter le robot et fermer l'interface ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reponse == QMessageBox.StandardButton.Yes:
                self._fermeture_demandee = True
                self._demander_fermeture_apercu(
                    lambda _: self.demande_deconnexion.emit())
            evenement.ignore()
            return

        if self._fermeture_demandee:
            evenement.ignore()
            return

        self._fermeture_demandee = True
        self._demander_fermeture_apercu(lambda _: self._terminer_fermeture())

    def _terminer_fermeture(self):
        self._thread_apercu.quit()
        self._thread_apercu.wait()
        self._thread.quit()
        self._thread.wait()
        self._fermeture_finalisee = True
        self.close()


def main():
    application = QApplication(sys.argv)
    application.setApplicationName("Rubik's cube — Meca500 R3")
    fenetre = InterfaceGraphique()
    fenetre.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
