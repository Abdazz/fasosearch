"""Lance FasoSearch en une commande : python run.py

Mode dev (défaut) : vérifie les ressources, (re)construit l'index si nécessaire, démarre le
serveur sur 127.0.0.1:8000 et ouvre le navigateur.
Mode prod (FASOSEARCH_MODE=prod, image Docker) : jamais de reconstruction de l'index ni de
navigateur ; échec immédiat si l'index est absent ou obsolète.
"""
import os
import socket
import sys
import threading
import webbrowser

import uvicorn

from backend.app import config
from backend.app.resources import missing_resources
from scripts import build_index

MODES = ("dev", "prod")


def settings() -> tuple[str, int, str]:
    mode = os.environ.get("FASOSEARCH_MODE", "dev")
    if mode not in MODES:
        sys.exit(f"FASOSEARCH_MODE invalide : {mode!r} (valeurs possibles : dev, prod)")
    host = os.environ.get("FASOSEARCH_HOST", "127.0.0.1")
    port = int(os.environ.get("FASOSEARCH_PORT", "8000"))
    return host, port, mode


def prepare(mode: str) -> None:
    missing = missing_resources()
    if missing:
        sys.exit(f"Ressources manquantes : {missing}\n→ lancez une fois : python scripts/setup_resources.py")
    if not config.CORPUS_EXCEL.exists():
        sys.exit(f"Base introuvable : {config.CORPUS_EXCEL}")
    if build_index.is_stale():
        if mode == "prod":
            sys.exit("Index absent ou obsolète : en production, l'index n'est jamais reconstruit "
                     "au démarrage. Reconstruisez l'image (python scripts/build_index.py avant docker build).")
        print("Construction de l'index (première exécution ou base modifiée)...")
        build_index.build()


def _port_in_use(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def main() -> None:
    host, port, mode = settings()
    url = f"http://{host}:{port}"
    # En dev, vérifier le port AVANT une éventuelle reconstruction de 15-25 min.
    if mode == "dev" and _port_in_use(host, port):
        sys.exit(f"Le port {port} est déjà utilisé : FasoSearch tourne peut-être déjà ({url})")
    prepare(mode)
    from backend.app.api import create_app
    from backend.app.engine import SearchEngine
    print("Chargement du moteur...")
    app = create_app(SearchEngine.load())
    print(f"FasoSearch prêt : {url} (mode {mode})")
    if mode == "dev" and "--no-browser" not in sys.argv:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
