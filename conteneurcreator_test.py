import pytest
import sys
import docker
from conteneurcreator import (
    list_containers,
    create_container,
    start_container,
    stop_container,
    remove_container,
    main,
)

##############################################
# Classes factices pour simuler Docker Client
##############################################


class FakeContainer:
    def __init__(self, name, short_id, status="created"):
        self.name = name
        self.short_id = short_id
        self.status = status

    def start(self):
        self.status = "running"

    def stop(self):
        self.status = "exited"

    def remove(self, force=False):
        self.status = "removed"


class FakeContainers:
    def __init__(self):
        self.containers = {}

    def list(self, all=False):
        return list(self.containers.values())

    def create(self, image, command=None, name=None, detach=True, ports=None):
        container = FakeContainer(name=name or "fake", short_id="fakeid")
        self.containers[name or "fake"] = container
        return container

    def get(self, identifier):
        if identifier in self.containers:
            return self.containers[identifier]
        # Pour simuler l'exception de docker.errors.NotFound
        raise docker.errors.NotFound(f"Container {identifier} not found")


class FakeClient:
    def __init__(self):
        self.containers = FakeContainers()


##############################################
# Exception factice (sous-classe de docker.errors.APIError)
##############################################


class FakeAPIError(docker.errors.APIError):
    def __init__(self, explanation):
        # On passe un dummy "response" à la super-classe (peut être None)
        super().__init__(explanation, response=None)
        self.explanation = explanation


##############################################
# Tests pour la fonction list_containers
##############################################


def test_list_containers_non_empty(capsys):
    fake_client = FakeClient()
    # Ajout de deux conteneurs factices
    fake_client.containers.containers["container1"] = FakeContainer(
        "container1", "id1", "running"
    )
    fake_client.containers.containers["container2"] = FakeContainer(
        "container2", "id2", "exited"
    )

    list_containers(fake_client, all_containers=True)
    captured = capsys.readouterr().out
    assert "Conteneur: container1" in captured
    assert "Conteneur: container2" in captured


def test_list_containers_empty(capsys):
    fake_client = FakeClient()
    list_containers(fake_client, all_containers=True)
    captured = capsys.readouterr().out
    assert "Aucun conteneur trouvé." in captured


##############################################
# Tests pour la fonction create_container
##############################################


def test_create_container_success(capsys):
    fake_client = FakeClient()
    container = create_container(fake_client, image="nginx", name="mon_nginx")
    captured = capsys.readouterr().out
    assert container is not None
    assert "Conteneur créé avec succès: mon_nginx" in captured


def test_create_container_failure(monkeypatch, capsys):
    fake_client = FakeClient()

    # Remplacer la méthode create pour qu'elle lève une exception de type FakeAPIError
    def fake_create(*args, **kwargs):
        raise FakeAPIError("Erreur test")

    monkeypatch.setattr(fake_client.containers, "create", fake_create)

    container = create_container(fake_client, image="nginx", name="fail_container")
    captured = capsys.readouterr().out
    assert container is None
    assert "Erreur lors de la création du conteneur: Erreur test" in captured


##############################################
# Tests pour la fonction start_container
##############################################


def test_start_container_success(capsys):
    container = FakeContainer("test_container", "id123")
    start_container(container)
    captured = capsys.readouterr().out
    assert container.status == "running"
    assert "Conteneur démarré: test_container" in captured


def test_start_container_failure(monkeypatch, capsys):
    container = FakeContainer("test_container", "id123")

    # Remplacer start() pour lever une exception
    def fake_start():
        raise FakeAPIError("Erreur démarrage")

    monkeypatch.setattr(container, "start", fake_start)

    start_container(container)
    captured = capsys.readouterr().out
    assert "Erreur lors du démarrage du conteneur: Erreur démarrage" in captured


##############################################
# Tests pour la fonction stop_container
##############################################


def test_stop_container_success(capsys):
    container = FakeContainer("test_container", "id123", status="running")
    stop_container(container)
    captured = capsys.readouterr().out
    assert container.status == "exited"
    assert "Conteneur arrêté: test_container" in captured


def test_stop_container_failure(monkeypatch, capsys):
    container = FakeContainer("test_container", "id123", status="running")

    def fake_stop():
        raise FakeAPIError("Erreur arrêt")

    monkeypatch.setattr(container, "stop", fake_stop)

    stop_container(container)
    captured = capsys.readouterr().out
    assert "Erreur lors de l'arrêt du conteneur: Erreur arrêt" in captured


##############################################
# Tests pour la fonction remove_container
##############################################


def test_remove_container_success(capsys):
    container = FakeContainer("test_container", "id123", status="running")
    remove_container(container)
    captured = capsys.readouterr().out
    assert container.status == "removed"
    assert "Conteneur supprimé: test_container" in captured


def test_remove_container_failure(monkeypatch, capsys):
    container = FakeContainer("test_container", "id123", status="running")

    def fake_remove(force=False):
        raise FakeAPIError("Erreur suppression")

    monkeypatch.setattr(container, "remove", fake_remove)

    remove_container(container)
    captured = capsys.readouterr().out
    assert "Erreur lors de la suppression du conteneur: Erreur suppression" in captured


##############################################
# Tests pour la fonction main
##############################################


def test_main_list(monkeypatch, capsys):
    fake_client = FakeClient()
    # Ajout d'un conteneur factice pour la liste
    fake_client.containers.containers["container1"] = FakeContainer(
        "container1", "id1", "running"
    )

    # Remplacer docker.from_env pour retourner notre fake client
    monkeypatch.setattr(docker, "from_env", lambda: fake_client)

    # Simuler l'appel de la commande avec l'argument --list
    test_args = ["conteneurcreator.py", "--list"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as e:
        main()
    # main() s'arrête avec sys.exit(0)
    assert e.value.code == 0
    captured = capsys.readouterr().out
    assert "Conteneur: container1" in captured


def test_main_no_args(monkeypatch, capsys):
    fake_client = FakeClient()
    monkeypatch.setattr(docker, "from_env", lambda: fake_client)
    test_args = ["conteneurcreator.py"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Appel de main() sans arguments devrait simplement afficher l'aide.
    main()
    captured = capsys.readouterr().out
    # Vérifier que l'aide est affichée (on cherche par exemple le mot "usage")
    assert "usage:" in captured
