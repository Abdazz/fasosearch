"""Configuration centrale : chemins et constantes du SRI (valeurs issues de la spec)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # .../Devoir/sri
DEVOIR = ROOT.parent                                 # .../Devoir

ORIGINAL_EXCEL = DEVOIR / "données textuelles.xlsx"
CORPUS_EXCEL = DEVOIR / "données textuelles - base complète.xlsx"

DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
STATIC_DIR = ROOT / "backend" / "static"
NLTK_DIR = ROOT / "nltk_data"
LANG_MODEL_DIR = ROOT / "lang_models" / "fr_en"

W2V_EXTRA = DATA_DIR / "w2v_extra.txt"
DOI_JSON = DATA_DIR / "doi.json"
AFFILIATIONS_TODO = DATA_DIR / "affiliations_a_verifier.txt"

# Word2Vec (skip-gram) — seed + 1 worker => entraînement reproductible
W2V_PARAMS = dict(vector_size=100, window=5, min_count=2, epochs=30, seed=42, sg=1, workers=1)
W2V_THRESHOLD = 0.40

# BM25 (bonus TP 3)
BM25_K1 = 1.5
BM25_B = 0.75

# Pagination
PER_PAGE_CHOICES = (10, 20, 50)
DEFAULT_PER_PAGE = 10

# Modèle de traduction fr->en (format Argos, exécuté avec ctranslate2)
ARGOS_FR_EN_URL = "https://argos-net.com/v1/translate-fr_en-1_9.argosmodel"

NLTK_PACKAGES = ["stopwords", "wordnet", "omw-1.4", "averaged_perceptron_tagger_eng"]
