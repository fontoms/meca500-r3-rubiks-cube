import importlib
from pathlib import Path

import cv2
import numpy as np
import pytest

from meca500_rubiks import vision_capture


@pytest.fixture
def vision():
    return vision_capture._module_vision("color_recognition")


@pytest.fixture
def references():
    return {
        "white": (255, 255, 255),
        "yellow": (0, 255, 255),
        "red": (0, 0, 255),
        "orange": (0, 128, 255),
        "green": (0, 255, 0),
        "blue": (255, 0, 0),
    }


@pytest.mark.parametrize("color", ["white", "yellow", "red", "orange", "green", "blue"])
def test_reference_calibree_est_reconnue(vision, references, color):
    assert vision.classify_with_references(references[color], references) == color


def test_tolerance_adaptative_selon_la_proximite_des_references(vision, references):
    seuils = vision.reference_thresholds(references)

    assert 0 < seuils["red"] < vision.MAX_REFERENCE_DISTANCE
    assert 0 < seuils["orange"] < vision.MAX_REFERENCE_DISTANCE
    assert all(0 < seuil <= vision.MAX_REFERENCE_DISTANCE for seuil in seuils.values())


def test_couleur_entre_rouge_et_orange_reste_indeterminee(vision, references):
    lab_rouge = vision.bgr_to_lab(references["red"])
    lab_orange = vision.bgr_to_lab(references["orange"])
    milieu_lab = np.rint((lab_rouge + lab_orange) / 2).astype(np.uint8)
    milieu_bgr = cv2.cvtColor(milieu_lab[None, None, :],
                              cv2.COLOR_LAB2BGR)[0, 0]

    assert vision.classify_with_references(milieu_bgr, references) is None


def test_variation_moderee_de_l_eclairage_reste_reconnue(vision, references):
    assert vision.classify_with_references((0, 0, 190), references) == "red"


def test_couleur_trop_sombre_ou_trop_eloignee_reste_inconnue(vision, references):
    assert vision.classify_with_references((20, 20, 20), references) is None
    assert vision.classify_with_references((100, 100, 100), references) is None


def test_seuils_hsv_separent_les_references_calibrees_rouge_et_orange(vision):
    rouge_calibre = (19, 25, 160)
    orange_calibre = (11, 41, 227)

    assert vision.classify_hsv(vision.bgr_to_hsv(rouge_calibre)) == vision.RED
    assert vision.classify_hsv(vision.bgr_to_hsv(orange_calibre)) == vision.ORANGE


def test_reference_orange_calibree_est_reconnue(vision):
    references = {
        "red": (19, 25, 160),
        "orange": (11, 41, 227),
    }

    assert vision.classify_with_references(references["orange"], references) == "orange"


def test_fichier_calibration_est_independant_du_dossier_de_lancement(monkeypatch, tmp_path):
    module_main = vision_capture._module_main()
    calibration = importlib.import_module(module_main.load_calibration.__module__)
    expected = Path(calibration.__file__).resolve().parents[1] / "config" / "colors.json"
    monkeypatch.chdir(tmp_path)

    assert calibration.DEFAULT_CONFIG_PATH == expected
