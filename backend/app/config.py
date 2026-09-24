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
W2V_CS = DATA_DIR / "w2v_cs.txt"  # résumés anglais d'informatique (entraînement Word2Vec uniquement, task 17b)
DOI_JSON = DATA_DIR / "doi.json"
AFFILIATIONS_TODO = DATA_DIR / "affiliations_a_verifier.txt"
OPENALEX_CACHE_DIR = DATA_DIR / "openalex_cache"
EXCLUSIONS = DATA_DIR / "exclusions.txt"

# Word2Vec (skip-gram) — seed + 1 worker => entraînement reproductible
# min_count=5 (task 17b) : élimine les mots rares parasites (ex. "sorobouly", "liido") des
# voisins, maintenant que le corpus d'entraînement est plus large (+ data/w2v_cs.txt).
W2V_PARAMS = dict(vector_size=100, window=5, min_count=5, epochs=30, seed=42, sg=1, workers=1)
# Seuil réglé via scripts/smoke_demo.py (task 18) : à 0.40, les requêtes de démo renvoyaient
# quasiment tout le corpus (jusqu'à 90/90 documents) car les vecteurs moyens (IDF) de ce
# vocabulaire restent globalement proches. Relevé par pas de 0.05 jusqu'à ce qu'au plus 2
# requêtes de démo significatives sortent de l'intervalle [3, 40] documents : 0.60 -> 1 seule
# requête hors intervalle (« Internet exchange points in Africa », 46), voir README.
W2V_THRESHOLD = 0.60

# BM25 (bonus TP 3)
BM25_K1 = 1.5
BM25_B = 0.75

# Pagination
PER_PAGE_CHOICES = (10, 20, 50)
DEFAULT_PER_PAGE = 10

# Modèle de traduction fr->en (format Argos, exécuté avec ctranslate2)
ARGOS_FR_EN_URL = "https://argos-net.com/v1/translate-fr_en-1_9.argosmodel"

NLTK_PACKAGES = ["stopwords", "wordnet", "omw-1.4", "averaged_perceptron_tagger_eng"]
