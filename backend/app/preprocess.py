"""Prétraitement : tokenisation → minuscules/nettoyage → stopwords → lemmatisation.

Le MÊME pipeline est appliqué aux documents (indexation) et aux requêtes.
Chaque token garde sa trace pour que l'interface montre chaque étape.
"""
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache

from nltk import pos_tag
from nltk.corpus import stopwords, wordnet
from nltk.stem import PorterStemmer, WordNetLemmatizer

from .resources import ensure_nltk_path

ensure_nltk_path()

# mots vides propres aux résumés scientifiques (spec §4.1)
DOMAIN_STOPWORDS = {
    "paper", "study", "propose", "proposed", "approach", "authors", "results", "result",
    "based", "using", "use", "used", "also", "work", "research", "article", "present",
    "presents", "show", "shows", "however", "thus", "therefore", "within", "may", "can",
}
STOPWORDS = frozenset(stopwords.words("english")) | frozenset(DOMAIN_STOPWORDS)

# un mot (lettres/chiffres, tirets internes autorisés) OU un signe de ponctuation isolé
TOKEN_RE = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*|[^\w\s]")

_lemmatizer = WordNetLemmatizer()
_stemmer = PorterStemmer()


@dataclass
class TokenTrace:
    raw: str
    normalized: str | None = None
    term: str | None = None
    removed_by: str | None = None


@dataclass
class Preprocessed:
    tokens: list[TokenTrace] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)
    mode: str = "lemma"

    def to_dict(self) -> dict:
        return {"mode": self.mode, "terms": list(self.terms), "tokens": [asdict(t) for t in self.tokens]}


def _wordnet_pos(tag: str) -> str:
    return {"J": wordnet.ADJ, "V": wordnet.VERB, "R": wordnet.ADV}.get(tag[:1], wordnet.NOUN)


@lru_cache(maxsize=100_000)
def _lemma(word: str, pos: str) -> str:
    return _lemmatizer.lemmatize(word, pos)


def preprocess(text: str, mode: str = "lemma") -> Preprocessed:
    out = Preprocessed(mode=mode)
    kept: list[TokenTrace] = []
    # Normalize typographic apostrophes (U+2019) to straight apostrophe (U+0027)
    text = (text or "").replace("'", "'")
    # 1. tokenisation
    for raw in TOKEN_RE.findall(text):
        t = TokenTrace(raw=raw)
        out.tokens.append(t)
        # 2. normalisation : minuscules, retrait ponctuation / nombres isolés
        if not any(c.isalnum() for c in raw):
            t.removed_by = "punctuation"
            continue
        low = raw.lower().replace("'", "")
        t.normalized = low
        if not any(c.isalpha() for c in low):
            t.removed_by = "number"
            continue
        # 3. stopwords (et mots d'une seule lettre)
        # Check both with apostrophe and without (for contractions like "don't")
        if raw.lower() in STOPWORDS or low in STOPWORDS or len(low) < 2:
            t.removed_by = "stopword"
            continue
        kept.append(t)
    # 4. lemmatisation guidée par la nature grammaticale (ou stemming)
    if mode == "stem":
        for t in kept:
            t.term = _stemmer.stem(t.normalized)
    else:
        tags = pos_tag([t.normalized for t in kept]) if kept else []
        for t, (_, tag) in zip(kept, tags):
            t.term = t.normalized if "-" in t.normalized else _lemma(t.normalized, _wordnet_pos(tag))
    out.terms = [t.term for t in kept]
    return out


def analyze(text: str) -> list[str]:
    return preprocess(text).terms


def word_forms(word: str) -> set[str]:
    """Lemmes possibles d'un mot isolé (nom, verbe, adjectif) — pour surligner un texte."""
    low = word.lower()
    return {low} | {_lemma(low, p) for p in (wordnet.NOUN, wordnet.VERB, wordnet.ADJ)}
