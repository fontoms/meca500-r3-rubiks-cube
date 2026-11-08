import resoudre_cube
from meca500_rubiks import resolution


CUBESTRING_RESOLU = "U" * 9 + "R" * 9 + "F" * 9 + "D" * 9 + "L" * 9 + "B" * 9


def test_commande_complete_choisit_camera_et_vitesse_avant_de_lancer(monkeypatch, tmp_path):
    evenements = []
    cubestring_path = tmp_path / "cubestring.txt"
    selection_camera = (2, [0, 2])
    facteur_vitesse = 0.75

    class Robot:
        def WaitIdle(self, timeout):
            evenements.append(("attente", timeout))

    robot = Robot()

    def presenter(robot_connecte, selection):
        assert robot_connecte is robot
        assert selection == selection_camera
        evenements.append("presentation")
        cubestring_path.write_text(CUBESTRING_RESOLU, encoding="utf-8")

    monkeypatch.setattr(resoudre_cube, "CUBESTRING_PATH", cubestring_path)
    monkeypatch.setattr(resoudre_cube.resolution, "charger_solveur",
                        lambda: evenements.append("solveur_precharge"))
    monkeypatch.setattr(resoudre_cube, "choisir_camera",
                        lambda: evenements.append("choix_camera") or selection_camera)
    monkeypatch.setattr(resoudre_cube, "demander_facteur_vitesse",
                        lambda facteur: evenements.append(("choix_vitesse", facteur)) or facteur_vitesse)
    monkeypatch.setattr(resoudre_cube, "confirmer_demarrage",
                        lambda: evenements.append("confirmation_demarrage") or True)
    monkeypatch.setattr(resoudre_cube, "confirmer_execution", lambda: True)
    monkeypatch.setattr(resoudre_cube.rubiks, "connecter",
                        lambda facteur_vitesse: evenements.append(("connexion", facteur_vitesse)) or robot)
    monkeypatch.setattr(resoudre_cube.rubiks, "presenter_faces", presenter)
    monkeypatch.setattr(resoudre_cube.rubiks, "deconnecter",
                        lambda robot_connecte: evenements.append(("deconnexion", robot_connecte)))
    monkeypatch.setattr(resolution, "calculer_solution",
                        lambda cubestring: evenements.append(("calcul", cubestring)) or [("R", 1)])
    monkeypatch.setattr(resolution, "plan_robot",
                        lambda coups:
                        evenements.append(("plan", coups)) or [("tourner_haut", -90, 0)])
    monkeypatch.setattr(resolution, "executer",
                        lambda robot_connecte, etapes: evenements.append(("execution", robot_connecte, etapes)))
    assert resoudre_cube.main(["--presenter-faces"]) == 0
    assert evenements.index("solveur_precharge") < evenements.index(("connexion", facteur_vitesse))
    assert evenements.index("choix_camera") < evenements.index(
        ("choix_vitesse", resoudre_cube.rubiks.VITESSE_GLOBALE))
    assert evenements.index(("choix_vitesse", resoudre_cube.rubiks.VITESSE_GLOBALE)) < evenements.index(
        "confirmation_demarrage")
    assert evenements.index("confirmation_demarrage") < evenements.index(("connexion", facteur_vitesse))
    assert evenements.index("presentation") < evenements.index(("calcul", CUBESTRING_RESOLU))
    assert ("plan", [("R", 1)]) in evenements
    assert any(event[0] == "execution" and event[1] is robot for event in evenements
               if isinstance(event, tuple))
    assert any(event[0] == "deconnexion" and event[1] is robot for event in evenements
               if isinstance(event, tuple))


def test_commande_complete_refuse_de_bouger_si_les_tables_solveur_manquent(monkeypatch):
    def solveur_absent():
        raise resolution.ErreurResolution("tables absentes")

    monkeypatch.setattr(resoudre_cube.resolution, "charger_solveur", solveur_absent)
    monkeypatch.setattr(resoudre_cube.rubiks, "connecter",
                        lambda: (_ for _ in ()).throw(AssertionError("le robot ne doit pas démarrer")))

    assert resoudre_cube.main(["--presenter-faces"]) == 1
