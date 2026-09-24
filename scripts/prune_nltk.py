"""Réduit nltk_data/ aux seuls paquets utiles, décompressés (image Docker plus légère).

Usage : python scripts/prune_nltk.py
"""
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import config  # noqa: E402


def prune(nltk_dir: Path, keep: list[str]) -> None:
    for category in [p for p in nltk_dir.iterdir() if p.is_dir()]:
        for archive in list(category.glob("*.zip")):
            name = archive.stem
            if name in keep and not (category / name).is_dir():
                with zipfile.ZipFile(archive) as z:
                    z.extractall(category)
            archive.unlink()
        for entry in list(category.iterdir()):
            if entry.name not in keep:
                shutil.rmtree(entry) if entry.is_dir() else entry.unlink()


if __name__ == "__main__":
    prune(config.NLTK_DIR, config.NLTK_PACKAGES)
    from backend.app.resources import missing_resources
    left = missing_resources()
    size = sum(f.stat().st_size for f in config.NLTK_DIR.rglob("*") if f.is_file()) / 1e6
    print(f"nltk_data réduit à {size:.0f} Mo ; manquant : {left or 'rien'}")
    sys.exit(1 if left else 0)
