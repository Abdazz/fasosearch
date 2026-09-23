"""Lance FasoSearch en une commande : python run.py

1. vérifie les ressources hors ligne ; 2. (re)construit l'index si nécessaire ;
3. démarre le serveur ; 4. ouvre le navigateur.
"""
import sys
import threading
import webbrowser

import uvicorn

from backend.app import config
from backend.app.resources import missing_resources
from scripts import build_index

HOST, PORT = "127.0.0.1", 8000


def main() -> None:
    missing = missing_resources()
    if missing:
        sys.exit(f"Ressources manquantes : {missing}\n→ lancez une fois : python scripts/setup_resources.py")
    if not config.CORPUS_EXCEL.exists():
        sys.exit(f"Base introuvable : {config.CORPUS_EXCEL}\n→ lancez une fois : python scripts/augment_data.py")
    if build_index.is_stale():
        print("Construction de l'index (première exécution ou base modifiée)...")
        build_index.build()
    from backend.app.api import create_app
    from backend.app.engine import SearchEngine
    print("Chargement du moteur...")
    app = create_app(SearchEngine.load())
    url = f"http://{HOST}:{PORT}"
    print(f"FasoSearch prêt : {url}")
    if "--no-browser" not in sys.argv:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
