from types import SimpleNamespace

import pytest

import meca500_rubiks as rubiks
import meca500_rubiks.briques as briques
import meca500_rubiks.vision_capture as vision_capture
from conftest import FauxRobot


class FauxRobotSansCamera(FauxRobot):
    def __getattr__(self, nom):
        if nom == "prendre_photo":
            raise AttributeError(nom)
        return super().__getattr__(nom)


def test_presenter_faces_capture_les_six_images_avec_une_camera(monkeypatch, capsys):
    evenements = []
    robot = FauxRobotSansCamera()
    references = object()
    couleurs_par_face = {
        "droite": "red", "loin_du_robot": "blue", "gauche": "orange",
        "dessous": "yellow", "vers_robot": "green", "dessus": "white",
    }

    class Camera:
        def __init__(self, index):
            evenements.append(("camera_index", index))

        def __enter__(self):
            evenements.append("camera_ouverte")
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            evenements.append("camera_liberee")

    def enumerer_cameras(module_camera):
        evenements.append("detection")
        return [(0, "Caméra intégrée", 0), (2, "Logitech C920", 0)]

    def module_vision(nom):
        if nom == "camera":
            return SimpleNamespace(Camera=Camera, CameraError=RuntimeError,
                                   DEFAULT_BACKEND=0)
        if nom == "cube":
            return cube_module
        raise AssertionError(nom)

    def parse_args(argv):
        evenements.append(("arguments", argv))
        return SimpleNamespace(camera=int(argv[1]), scan=False)

    def capturer_face(camera, face, couleurs_references):
        evenements.append(("capture", face, couleurs_references))
        return "captures/{}.png".format(face), [couleurs_par_face[face]] * 9

    callback_apercu = lambda frame: None

    def run_on_camera(requested_index, scan=False, references=None, action=None,
                      available_indexes=None, frame_callback=None, show_window=True,
                      camera_backend=None, overlay_error_callback=None):
        assert frame_callback is callback_apercu
        assert not show_window
        assert camera_backend == 0
        assert overlay_error_callback is None
        evenements.append(("run_on_camera", requested_index, scan, references,
                           available_indexes, camera_backend))
        assert not robot.commandes
        with Camera(requested_index) as camera:
            action(camera)
        return 0

    cube_module = vision_capture._module_vision("cube")
    cubestrings = []
    monkeypatch.setattr(
        cube_module, "save_cubestring",
        lambda cubestring, path=None: cubestrings.append(cubestring) or "cubestring.txt")
    monkeypatch.setattr(vision_capture, "_module_vision", module_vision)
    monkeypatch.setattr(vision_capture, "_enumerer_cameras", enumerer_cameras)
    monkeypatch.setattr(vision_capture, "_module_main", lambda: SimpleNamespace(
        parse_args=parse_args,
        load_references=lambda: references,
        run_on_camera=run_on_camera,
    ))
    monkeypatch.setattr(briques, "capturer_face", capturer_face)
    monkeypatch.setattr(briques.time, "sleep", lambda duree: None)

    choix = iter(["1", "2"])

    def demander_choix(prompt):
        assert not robot.commandes
        evenements.append(("choix", prompt))
        return next(choix)

    monkeypatch.setattr("builtins.input", demander_choix)
    faces = rubiks.presenter_faces(
        robot, callback_apercu=callback_apercu, afficher_fenetre=False)

    photos = [evenement[1] for evenement in evenements
              if isinstance(evenement, tuple) and evenement[0] == "capture"]
    attendu = "U" * 9 + "R" * 9 + "F" * 9 + "D" * 9 + "L" * 9 + "B" * 9
    assert len(photos) == 6
    assert set(photos) == set(faces)
    assert cubestrings == [attendu]
    assert evenements[0] == "detection"
    assert ("run_on_camera", 2, False, references, [0, 2], 0) in evenements
    assert evenements.index(("run_on_camera", 2, False, references, [0, 2], 0)) < evenements.index(
        ("camera_index", 2))
    assert ("camera_index", 2) in evenements
    assert evenements[-1] == "camera_liberee"
    sortie = capsys.readouterr().out
    assert "Caméra intégrée" in sortie
    assert "Logitech C920" in sortie


def test_backend_camera_windows_est_msmf():
    camera = vision_capture._module_vision("camera")
    if camera.sys.platform == "win32":
        assert camera.DEFAULT_BACKEND == camera.cv2.CAP_MSMF


def test_orientation_des_photos_correspond_aux_faces_du_cubestring():
    from meca500_rubiks import modele_cube, resolution
    cube = vision_capture._module_vision("cube")
    vues_attendues = {
        "droite": ("droite", "dessus", "loin_du_robot"),
        "loin_du_robot": ("loin_du_robot", "dessus", "gauche"),
        "gauche": ("gauche", "dessus", "vers_robot"),
        "dessus": ("dessus", "droite", "vers_robot"),
        "vers_robot": ("vers_robot", "droite", "dessous"),
        "dessous": ("dessous", "droite", "loin_du_robot"),
    }
    grille = list(range(9))
    grille_tournee = [grille[(2 - colonne) * 3 + ligne]
                      for ligne in range(3) for colonne in range(3)]
    for face, orientation in resolution.orientations_presenter_faces():
        vue = resolution.vue_camera(orientation)
        assert vue == vues_attendues[face]
        attendu = grille_tournee if face in ("dessus", "vers_robot", "dessous") else grille
        assert vision_capture._orienter_couleurs(grille, vue, cube, modele_cube) == attendu


def test_cubestring_est_converti_apres_la_presentation(monkeypatch):
    from meca500_rubiks import modele_cube, resolution

    cube = vision_capture._module_vision("cube")
    melange = modele_cube.ModeleCube()
    melange.coup("R", 1)
    cubestring_apres = melange.facelets()
    enregistres = []
    monkeypatch.setattr(
        resolution, "cubestring_apres_presenter_faces",
        lambda cubestring: cubestring_apres)
    monkeypatch.setattr(
        cube, "save_cubestring",
        lambda cubestring, path=None: enregistres.append(cubestring) or "cubestring.txt")
    photos = {
        "droite": ["red"] * 9,
        "loin_du_robot": ["blue"] * 9,
        "gauche": ["orange"] * 9,
        "dessus": ["white"] * 9,
        "vers_robot": ["green"] * 9,
        "dessous": ["yellow"] * 9,
    }

    resultat = vision_capture.creer_cubestring(photos)

    assert resultat == cubestring_apres
    assert enregistres == [cubestring_apres]


def test_detection_des_stickers_bleus_sombres():
    import cv2
    import numpy as np

    detection = vision_capture._module_vision("detection")
    extraction = vision_capture._module_vision("grid")
    reconnaissance = vision_capture._module_vision("color_recognition")
    frame = np.full((480, 640, 3), (20, 20, 20), dtype=np.uint8)
    for ligne in range(3):
        for colonne in range(3):
            x, y = 190 + colonne * 70, 70 + ligne * 70
            cv2.rectangle(frame, (x, y), (x + 60, y + 60), (5, 5, 5), -1)
            cv2.rectangle(frame, (x + 4, y + 4), (x + 56, y + 56), (80, 25, 0), -1)

    stickers = extraction.extract_stickers(frame, detection.detect_face(frame))

    assert stickers is not None
    assert reconnaissance.recognize_face(stickers) == ["blue"] * 9


def test_cubestring_refuse_une_photo_avec_couleurs_mal_lues():
    cube = vision_capture._module_vision("cube")
    faces = {
        "U": ["white"] * 9,
        "R": ["red"] * 9,
        "F": ["green"] * 9,
        "D": ["yellow"] * 9,
        "L": ["orange"] * 9,
        "B": ["blue"] * 9,
    }
    faces["B"][0] = "white"

    with pytest.raises(cube.CubeError, match="Répartition des couleurs invalide"):
        cube.to_cubestring(faces)


def test_run_on_camera_partage_l_apercu_et_le_flux_avec_l_action(monkeypatch):
    module_main = vision_capture._module_main()
    evenements = []
    numero_image = 0

    class Camera:
        def __init__(self, index):
            self.index = index

        def __enter__(self):
            evenements.append("camera_ouverte")
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            evenements.append("camera_liberee")

        def info(self):
            return {"index": self.index, "backend": "test", "width": 1,
                    "height": 1, "fps": 30}

    monkeypatch.setattr(module_main, "list_cameras",
                        lambda: pytest.fail("ne doit pas rescanner les caméras"))
    monkeypatch.setattr(module_main, "Camera", Camera)

    def lire_camera(camera):
        nonlocal numero_image
        numero_image += 1
        return bytearray(str(numero_image).encode())

    monkeypatch.setattr(module_main, "capture_frame", lire_camera)
    monkeypatch.setattr(module_main, "describe_frame", lambda frame: {
        "width": 1, "height": 1, "channels": 1, "format": "GRAY", "dtype": "uint8",
    })
    monkeypatch.setattr(module_main, "show_detection", lambda frame, references=None: frame)
    monkeypatch.setattr(module_main, "_preview_window_closed", lambda: False)
    monkeypatch.setattr(module_main.cv2, "namedWindow",
                        lambda *args: evenements.append("fenetre_ouverte"))
    monkeypatch.setattr(module_main.cv2, "imshow",
                        lambda *args: evenements.append("apercu"))
    monkeypatch.setattr(module_main.cv2, "waitKey", lambda *args: 255)
    monkeypatch.setattr(module_main.cv2, "destroyWindow",
                        lambda *args: evenements.append("fenetre_fermee"))

    def action(camera):
        premiere = camera.read()
        suivante = camera.read()
        evenements.append(("action", bytes(premiere), bytes(suivante)))

    statut = module_main.run_on_camera(2, action=action, available_indexes=[2])

    assert statut == 0
    index_action = next(index for index, event in enumerate(evenements)
                        if isinstance(event, tuple) and event[0] == "action")
    assert evenements.index("apercu") < index_action
    action = evenements[index_action]
    assert action[1] != action[2]
    assert evenements[-1] == "camera_liberee"


def test_run_on_camera_transmet_l_apercu_sans_ouvrir_de_fenetre(monkeypatch):
    module_main = vision_capture._module_main()
    frames = []
    numero_image = 0

    class Camera:
        def __init__(self, index):
            self.index = index

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def info(self):
            return {"index": self.index, "backend": "test", "width": 1,
                    "height": 1, "fps": 30}

    def lire_camera(camera):
        nonlocal numero_image
        numero_image += 1
        return bytearray(str(numero_image).encode())

    monkeypatch.setattr(module_main, "list_cameras",
                        lambda: pytest.fail("ne doit pas rescanner les caméras"))
    monkeypatch.setattr(module_main, "Camera", Camera)
    monkeypatch.setattr(module_main, "capture_frame", lire_camera)
    monkeypatch.setattr(module_main, "describe_frame", lambda frame: {
        "width": 1, "height": 1, "channels": 1, "format": "GRAY", "dtype": "uint8",
    })
    monkeypatch.setattr(module_main, "show_detection", lambda frame, references=None: frame)
    for nom in ("namedWindow", "imshow", "waitKey", "destroyWindow"):
        monkeypatch.setattr(
            module_main.cv2, nom,
            lambda *args, _nom=nom: pytest.fail("ne doit pas appeler cv2.%s" % _nom))

    def action(camera):
        camera.read()
        camera.read()

    statut = module_main.run_on_camera(
        2, action=action, available_indexes=[2],
        frame_callback=lambda frame: frames.append(bytes(frame)), show_window=False)

    assert statut == 0
    assert frames
    assert len(set(frames)) > 1


def test_run_on_camera_garde_le_flux_brut_si_la_detection_echoue(monkeypatch):
    module_main = vision_capture._module_main()
    frames = []
    erreurs = []
    numero_image = 0

    class Camera:
        def __init__(self, index):
            self.index = index

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def info(self):
            return {"index": self.index, "backend": "test", "width": 1,
                    "height": 1, "fps": 30}

    def lire_camera(camera):
        nonlocal numero_image
        numero_image += 1
        return bytearray(str(numero_image).encode())

    monkeypatch.setattr(module_main, "list_cameras",
                        lambda: pytest.fail("ne doit pas rescanner les caméras"))
    monkeypatch.setattr(module_main, "Camera", Camera)
    monkeypatch.setattr(module_main, "capture_frame", lire_camera)
    monkeypatch.setattr(module_main, "describe_frame", lambda frame: {
        "width": 1, "height": 1, "channels": 1, "format": "GRAY", "dtype": "uint8",
    })
    monkeypatch.setattr(
        module_main, "show_detection",
        lambda frame, references=None: (_ for _ in ()).throw(ValueError("détection en panne")))

    def action(source):
        source.read()
        source.read()

    statut = module_main.run_on_camera(
        2, action=action, available_indexes=[2],
        frame_callback=lambda frame: frames.append(bytes(frame)), show_window=False,
        overlay_error_callback=erreurs.append)

    assert statut == 0
    assert len(erreurs) == 1
    assert "détection en panne" in str(erreurs[0])
    assert len(set(frames)) > 1
