"""Localisation des ressources hors ligne (données NLTK, modèle de traduction)."""
import nltk

from . import config


def ensure_nltk_path() -> None:
    """Fait pointer NLTK vers sri/nltk_data (idempotent)."""
    p = str(config.NLTK_DIR)
    if p not in nltk.data.path:
        nltk.data.path.insert(0, p)


def missing_resources() -> list[str]:
    """Liste lisible des ressources absentes (vide si tout est prêt)."""
    ensure_nltk_path()
    missing = []
    probes = {
        "stopwords": "corpora/stopwords",
        "wordnet": "corpora/wordnet",
        "omw-1.4": "corpora/omw-1.4",
        "averaged_perceptron_tagger_eng": "taggers/averaged_perceptron_tagger_eng",
    }
    for name, path in probes.items():
        try:
            nltk.data.find(path)
        except LookupError:
            missing.append(f"nltk:{name}")
    if not (config.LANG_MODEL_DIR / "model" / "model.bin").exists():
        missing.append("modèle de traduction fr→en")
    return missing
