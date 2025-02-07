#!/usr/bin/env python3
"""
Script pour automatiser la création et la gestion de conteneurs Docker sous Linux ou Windows.

Utilisations :
  - Lister tous les conteneurs :
      python conteneurcreator.py --list

  - Créer un conteneur (exemple avec l'image nginx, nom "mon_nginx" et mapping de port 8080:80) :
      python conteneurcreator.py --create --image nginx --name mon_nginx --ports 8080:80

  - Démarrer un conteneur existant (par ID ou nom) :
      python conteneurcreator.py --start mon_nginx

  - Arrêter un conteneur existant :
      python conteneurcreator.py --stop mon_nginx

  - Supprimer un conteneur existant :
      python conteneurcreator.py --remove mon_nginx
"""

import docker
import argparse
import sys


def list_containers(client, all_containers=False):
    """Liste les conteneurs Docker."""
    containers = client.containers.list(all=all_containers)
    if containers:
        for container in containers:
            print(
                f"Conteneur: {container.name} (ID: {container.short_id}) - Statut: {container.status}"
            )
    else:
        print("Aucun conteneur trouvé.")


def create_container(client, image, name=None, command=None, detach=True, ports=None):
    """Crée un conteneur à partir de l'image spécifiée."""
    try:
        container = client.containers.create(
            image=image, command=command, name=name, detach=detach, ports=ports
        )
        print(
            f"Conteneur créé avec succès: {container.name} (ID: {container.short_id})"
        )
        return container
    except docker.errors.APIError as e:
        print(f"Erreur lors de la création du conteneur: {e.explanation}")
        return None


def start_container(container):
    """Démarre le conteneur spécifié."""
    try:
        container.start()
        print(f"Conteneur démarré: {container.name}")
    except docker.errors.APIError as e:
        print(f"Erreur lors du démarrage du conteneur: {e.explanation}")


def stop_container(container):
    """Arrête le conteneur spécifié."""
    try:
        container.stop()
        print(f"Conteneur arrêté: {container.name}")
    except docker.errors.APIError as e:
        print(f"Erreur lors de l'arrêt du conteneur: {e.explanation}")


def remove_container(container):
    """Supprime le conteneur spécifié."""
    try:
        container.remove(force=True)
        print(f"Conteneur supprimé: {container.name}")
    except docker.errors.APIError as e:
        print(f"Erreur lors de la suppression du conteneur: {e.explanation}")


def main():
    parser = argparse.ArgumentParser(
        description="Automatise la création et la gestion de conteneurs Docker sous Linux ou Windows."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lister tous les conteneurs (actifs et inactifs)",
    )
    parser.add_argument(
        "--create", action="store_true", help="Créer un nouveau conteneur"
    )
    parser.add_argument(
        "--start", type=str, help="Démarrer un conteneur existant (ID ou nom)"
    )
    parser.add_argument(
        "--stop", type=str, help="Arrêter un conteneur existant (ID ou nom)"
    )
    parser.add_argument(
        "--remove", type=str, help="Supprimer un conteneur existant (ID ou nom)"
    )
    parser.add_argument(
        "--image",
        type=str,
        help="Image Docker à utiliser pour la création du conteneur",
    )
    parser.add_argument("--name", type=str, help="Nom du conteneur")
    parser.add_argument(
        "--command", type=str, help="Commande à exécuter dans le conteneur"
    )
    parser.add_argument(
        "--ports",
        nargs="+",
        help="Mapping de ports au format host_port:container_port, ex: 8080:80",
    )
    args = parser.parse_args()

    # Connexion au daemon Docker
    try:
        client = docker.from_env()
    except Exception as e:
        print("Erreur de connexion à Docker:", e)
        sys.exit(1)

    # Traitement des options
    if args.list:
        list_containers(client, all_containers=True)
        sys.exit(0)

    if args.create:
        if not args.image:
            print("L'argument --image est obligatoire pour créer un conteneur.")
            sys.exit(1)
        ports = {}
        if args.ports:
            for port_mapping in args.ports:
                try:
                    host_port, container_port = port_mapping.split(":")
                    ports[int(host_port)] = int(container_port)
                except ValueError:
                    print(
                        f"Mapping de port invalide: {port_mapping}. Utilisez le format host_port:container_port"
                    )
                    sys.exit(1)
        container = create_container(
            client, image=args.image, name=args.name, command=args.command, ports=ports
        )
        if container:
            start_container(container)
        sys.exit(0)

    if args.start:
        try:
            container = client.containers.get(args.start)
            start_container(container)
        except docker.errors.NotFound:
            print(f"Conteneur {args.start} non trouvé.")
        sys.exit(0)

    if args.stop:
        try:
            container = client.containers.get(args.stop)
            stop_container(container)
        except docker.errors.NotFound:
            print(f"Conteneur {args.stop} non trouvé.")
        sys.exit(0)

    if args.remove:
        try:
            container = client.containers.get(args.remove)
            remove_container(container)
        except docker.errors.NotFound:
            print(f"Conteneur {args.remove} non trouvé.")
        sys.exit(0)

    # Si aucune option n'est fournie, afficher l'aide
    parser.print_help()


if __name__ == "__main__":
    main()
