"""Installation unique des ressources hors ligne : données NLTK + modèle fr→en.

Usage : python scripts/setup_resources.py   (nécessite internet une seule fois)
"""
import io
import shutil
import sys
import zipfile
from pathlib import Path

import nltk
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import config  # noqa: E402
from backend.app.resources import missing_resources  # noqa: E402


def setup_nltk():
    config.NLTK_DIR.mkdir(parents=True, exist_ok=True)
    for pkg in config.NLTK_PACKAGES:
        nltk.download(pkg, download_dir=str(config.NLTK_DIR), quiet=True)


def setup_translation_model():
    target = config.LANG_MODEL_DIR
    if (target / "model" / "model.bin").exists():
        return
    print("Téléchargement du modèle de traduction fr→en (~66 Mo)...")
    r = requests.get(config.ARGOS_FR_EN_URL, timeout=600)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        tmp = target.parent / "_tmp"
        z.extractall(tmp)
    inner = next(p for p in tmp.iterdir() if p.is_dir())  # translate-fr_en-1_9/
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(inner / "model", target / "model", dirs_exist_ok=True)
    shutil.copy(inner / "sentencepiece.model", target / "sentencepiece.model")
    shutil.rmtree(tmp)


if __name__ == "__main__":
    setup_nltk()
    setup_translation_model()
    left = missing_resources()
    print("OK : toutes les ressources sont installées." if not left else f"Manquant : {left}")
