# -*- coding: utf-8 -*-
"""Adaptateur vers l'aperçu et les primitives de capture de rubicks-resolve."""
from datetime import datetime
import importlib
import importlib.util
import sys
from pathlib import Path

_PACKAGE = __package__ + "._rubicks_resolve"
CUBESTRING_PATH = Path(__file__).resolve().parent.parent / "cubestring.txt"
_FACE_CUBE = {
    "droite": "R", "loin_du_robot": "B", "gauche": "L",
    "dessous": "D", "vers_robot": "F", "dessus": "U",
}


class ErreurCamera(RuntimeError):
    """Énumération ou sélection de caméra impossible."""


def _charger_package():
    if _PACKAGE in sys.modules:
        return

    source = Path(__file__).resolve().parent.parent / "rubicks-resolve" / "src"
    init = source / "__init__.py"
    if not init.is_file():
        raise ImportError("Le module de capture rubicks-resolve est introuvable : %s" % source)

    spec = importlib.util.spec_from_file_location(
        _PACKAGE, init, submodule_search_locations=[str(source)])
    if spec is None or spec.loader is None:
        raise ImportError("Impossible de charger le module de capture : %s" % source)
    package = importlib.util.module_from_spec(spec)
    sys.modules[_PACKAGE] = package
    spec.loader.exec_module(package)


def _module_vision(nom):
    _charger_package()
    return importlib.import_module("{}.{}".format(_PACKAGE, nom))


def _module_main():
    nom_module = __package__ + "._rubicks_resolve_main"
    if nom_module in sys.modules:
        return sys.modules[nom_module]

    chemin = Path(__file__).resolve().parent.parent / "rubicks-resolve" / "main.py"
    repertoire = str(chemin.parent)
    ajoute = repertoire not in sys.path
    if ajoute:
        sys.path.insert(0, repertoire)
    try:
        spec = importlib.util.spec_from_file_location(nom_module, chemin)
        if spec is None or spec.loader is None:
            raise ImportError("Impossible de charger l'application rubicks-resolve : %s" % chemin)
        module = importlib.util.module_from_spec(spec)
        sys.modules[nom_module] = module
        spec.loader.exec_module(module)
    finally:
        if ajoute:
            sys.path.remove(repertoire)
    return module


def executer_avec_apercu(robot, action, selection_camera=None, callback_apercu=None,
                         afficher_fenetre=True, callback_erreur_vision=None):
    if callable(getattr(robot, "prendre_photo", None)):
        return action(None, None)

    module_camera = _module_vision("camera")
    if selection_camera is None:
        selection_camera = _choisir_camera(module_camera)
    if len(selection_camera) == 2:
        index, disponibles = selection_camera
        backend = None
    else:
        index, disponibles, backend = selection_camera
    if index not in disponibles:
        raise ErreurCamera("La caméra sélectionnée n'est plus disponible (index %s)." % index)
    module_main = _module_main()
    args = module_main.parse_args(["--camera", str(index)])
    references = module_main.load_references()
    resultat = []

    def executer(camera):
        resultat.append(action(camera, references))

    statut = module_main.run_on_camera(
        args.camera, scan=args.scan, references=references, action=executer,
        available_indexes=disponibles, frame_callback=callback_apercu,
        show_window=afficher_fenetre, camera_backend=backend,
        overlay_error_callback=callback_erreur_vision)
    if statut != 0:
        raise module_camera.CameraError(
            "L'aperçu ou la capture rubicks-resolve a échoué (code %s)." % statut)
    if not resultat:
        raise RuntimeError("La séquence du robot ne s'est pas exécutée.")
    return resultat[0]


def choisir_camera():
    """Affiche les noms et renvoie l'index choisi, les index disponibles et leur backend."""
    return _choisir_camera(_module_vision("camera"))


def lister_cameras(backend=None):
    """Renvoie les triplets (index OpenCV, nom, backend) des caméras disponibles."""
    return _enumerer_cameras(_module_vision("camera"), backend)


def ouvrir_camera(index, backend=None):
    """Ouvre le flux d'une caméra pour l'aperçu graphique."""
    module_camera = _module_vision("camera")
    try:
        if backend is None:
            camera = module_camera.Camera(index)
        else:
            camera = module_camera.Camera(index, backend=backend)
        return camera.open()
    except module_camera.CameraError as exc:
        raise ErreurCamera(str(exc)) from exc


def _enumerer_cameras(module_camera, backend=None):
    from cv2_enumerate_cameras import enumerate_cameras

    backend = module_camera.DEFAULT_BACKEND if backend is None else backend
    return [(camera.index, camera.name or "Nom indisponible", camera.backend)
            for camera in enumerate_cameras(backend)]


def _choisir_camera(module_camera):
    cameras = _enumerer_cameras(module_camera)
    if not cameras:
        raise ErreurCamera("Aucune caméra détectée.")

    disponibles = [index for index, _, _ in cameras]
    choix_valides = ", ".join(str(index) for index in disponibles)
    print("Caméras détectées :")
    for index, nom, _ in cameras:
        print("  %s : %s" % (index, nom))
    while True:
        choix = input("Index de la caméra à utiliser avant le mouvement : ").strip()
        try:
            index = int(choix)
        except ValueError:
            index = None
        if index in disponibles:
            backend = next(backend for index_camera, _, backend in cameras if index_camera == index)
            return index, disponibles, backend
        print("Choix invalide. Choisir parmi : {}".format(choix_valides))


def capturer_face(camera, face, references=None):
    capture = _module_vision("capture")
    frame = capture.capture_frame(camera)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    nom = "{}_{}".format(face, horodatage)
    chemin = capture.save_frame(frame, name=nom)
    detection = _module_vision("detection").detect_face(frame)
    stickers = _module_vision("grid").extract_stickers(frame, detection)
    couleurs = None
    if stickers is not None:
        couleurs = _module_vision("color_recognition").recognize_face(
            stickers, references=references)
    return chemin, couleurs


def _orienter_couleurs(couleurs, vue, cube, modele):
    if len(couleurs) != 9:
        return couleurs

    face, haut_image, droite_image = vue
    lettre = _FACE_CUBE[face]
    top_attendu = cube.TOP_NEIGHBOR[lettre]
    droite_attendue = modele.FACE_DIR[modele.cross(
        tuple(-v for v in modele.DIR_FACE[lettre]), modele.DIR_FACE[top_attendu])]

    def opposee(face_image):
        direction = modele.DIR_FACE[_FACE_CUBE[face_image]]
        return modele.FACE_DIR[tuple(-v for v in direction)]

    haut, droite = _FACE_CUBE[haut_image], _FACE_CUBE[droite_image]
    orientations = (
        (haut, droite),
        (opposee(droite_image), haut),
        (opposee(haut_image), opposee(droite_image)),
        (droite, opposee(haut_image)),
    )
    for rotation_horaire, orientation in enumerate(orientations):
        if orientation == (top_attendu, droite_attendue):
            for _ in range(rotation_horaire):
                couleurs = [couleurs[(2 - colonne) * 3 + ligne]
                            for ligne in range(3) for colonne in range(3)]
            return couleurs
    raise cube.CubeError("Orientation caméra incohérente pour la face %s." % face)


def creer_cubestring(photos):
    cube = _module_vision("cube")
    from . import modele_cube, resolution

    faces = {}
    for nom, orientation in resolution.orientations_presenter_faces():
        if nom is None:
            continue
        couleurs = photos.get(nom)
        if couleurs is None:
            raise cube.CubeError("Face %s non détectée." % nom)
        vue = resolution.vue_camera(orientation)
        if vue[0] != nom:
            raise cube.CubeError("La face annoncée %s ne correspond pas à la caméra (%s)." %
                                 (nom, vue[0]))
        couleurs = _orienter_couleurs(couleurs, vue, cube, modele_cube)
        face = _FACE_CUBE[vue[0]]
        cube.check_face(couleurs, faces)
        faces[face] = couleurs

    cubestring_avant = cube.to_cubestring(faces)
    cubestring = resolution.cubestring_apres_presenter_faces(cubestring_avant)
    chemin = cube.save_cubestring(cubestring, CUBESTRING_PATH)
    print(cube.format_net(faces))
    print("Chaîne après présentation : %s" % cubestring)
    print("Enregistrée dans %s" % chemin)
    return cubestring
