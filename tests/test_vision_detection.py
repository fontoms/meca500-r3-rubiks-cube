import cv2
import numpy as np
import pytest

from meca500_rubiks import vision_capture


@pytest.mark.parametrize("angle", [-5, 0, 5])
def test_detection_et_couleurs_restent_stables_si_la_camera_tourne(angle):
    detection_module = vision_capture._module_vision("detection")
    grid_module = vision_capture._module_vision("grid")
    colors_module = vision_capture._module_vision("color_recognition")
    couleurs = [
        (255, 255, 255), (0, 0, 255), (0, 255, 0),
        (255, 0, 0), (11, 41, 227), (49, 147, 156),
        (255, 255, 255), (0, 255, 255), (0, 0, 255),
    ]
    image = np.full((480, 640, 3), (18, 18, 18), dtype=np.uint8)
    for index, couleur in enumerate(couleurs):
        ligne, colonne = divmod(index, 3)
        x, y = 250 + colonne * 70, 100 + ligne * 70
        cv2.rectangle(image, (x, y), (x + 58, y + 58), (0, 0, 0), -1)
        cv2.rectangle(image, (x + 4, y + 4), (x + 54, y + 54), couleur, -1)

    x, y = 180, 170
    cv2.rectangle(image, (x, y), (x + 58, y + 58), (0, 0, 0), -1)
    cv2.rectangle(image, (x + 4, y + 4), (x + 54, y + 54), (0, 255, 255), -1)

    hauteur, largeur = image.shape[:2]
    matrice = cv2.getRotationMatrix2D((largeur / 2, hauteur / 2), angle, 1)
    image = cv2.warpAffine(image, matrice, (largeur, hauteur),
                           borderValue=(18, 18, 18))
    detection = detection_module.detect_face(image)
    stickers = grid_module.extract_stickers(image, detection)

    assert detection is not None
    assert len(detection.stickers) == 9
    assert colors_module.recognize_face(stickers) == [
        "white", "red", "green",
        "blue", "orange", "yellow",
        "white", "yellow", "red",
    ]
