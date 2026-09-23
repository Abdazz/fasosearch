"""Phase d'indexation (hors ligne) : prétraitement du corpus + entraînement Word2Vec.

Usage : python scripts/build_index.py
L'index inversé, TF-IDF et BM25 sont recalculés en mémoire au démarrage (rapide) ;
seul l'entraînement de Word2Vec (≈ 1-2 min) est mis en cache dans models/.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import config  # noqa: E402
from backend.app.corpus import load_corpus  # noqa: E402
from backend.app.preprocess import analyze  # noqa: E402
from backend.app.word2vec import train_word2vec  # noqa: E402

DOC_TERMS = config.MODELS_DIR / "doc_terms.json"
W2V_FILE = config.MODELS_DIR / "w2v.kv"
FINGERPRINT = config.MODELS_DIR / "fingerprint.txt"


def fingerprint(path: Path) -> str:
    if not path.exists():
        return "absent"
    st = path.stat()
    return f"{st.st_size}-{st.st_mtime_ns}"


def _current() -> str:
    return f"{fingerprint(config.CORPUS_EXCEL)}|{fingerprint(config.W2V_EXTRA)}|{config.W2V_PARAMS}"


def is_stale() -> bool:
    if not (DOC_TERMS.exists() and W2V_FILE.exists() and FINGERPRINT.exists()):
        return True
    return FINGERPRINT.read_text() != _current()


def build() -> None:
    t0 = time.time()
    docs = load_corpus(config.CORPUS_EXCEL)
    print(f"Prétraitement de {len(docs)} documents...")
    doc_terms = [analyze(d.text) for d in docs]
    extra_lines = config.W2V_EXTRA.read_text(encoding="utf-8").splitlines() if config.W2V_EXTRA.exists() else []
    # Filter out empty lines from w2v_extra.txt
    extra_lines = [line for line in extra_lines if line.strip()]
    print(f"Prétraitement de {len(extra_lines)} résumés d'entraînement Word2Vec...")
    extra_terms = [analyze(line) for line in extra_lines]
    print("Entraînement Word2Vec (skip-gram)...")
    kv = train_word2vec(doc_terms + extra_terms)
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DOC_TERMS.write_text(json.dumps({"ids": [d.id for d in docs], "terms": doc_terms}), encoding="utf-8")
    kv.save(str(W2V_FILE))
    FINGERPRINT.write_text(_current())
    print(f"Index construit en {time.time() - t0:.0f} s — vocabulaire Word2Vec : {len(kv.key_to_index)} mots")


if __name__ == "__main__":
    build()
