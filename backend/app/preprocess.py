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

# Incrémenté à chaque changement de comportement du pipeline (tokenisation, stopwords,
# lemmatisation...) : scripts/build_index.py l'inclut dans son empreinte pour que l'index
# soit reconstruit automatiquement quand le prétraitement change, même si le corpus source
# et les paramètres Word2Vec n'ont pas bougé.
PREPROCESS_VERSION = 2

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


@lru_cache(maxsize=100_000)
def _keeps_ing_noun_reading(tag: str, word: str) -> bool:
    """« learning », « routing », « processing »... : le tagueur grammatical les étiquette
    tantôt nom (NN), tantôt verbe (VBG) selon un contexte parfois perdu ici (le POS-tagging
    s'exécute après le retrait des mots vides, ex. "the routing of packets" -> ["routing",
    "packets"]) — ce qui les lemmatisait en verbe ("learn", "rout") dans un cas et les
    laissait intacts dans l'autre, alors qu'ils désignent le même concept nominal partout
    ("machine learning", "learning algorithms" et "is learning fast" doivent produire le
    même terme "learning").
    Règle : un mot en "-ing" étiqueté verbe mais reconnu comme mot du vocabulaire anglais
    garde sa forme telle quelle (lecture nominale) plutôt que d'être lemmatisé en verbe.
    Note : `wordnet.synsets(word, pos=wordnet.NOUN)` ne suffit pas seul — certains termes
    techniques comme "routing" n'ont aucun sens nominal propre dans ce WordNet (seulement
    des sens verbaux "route"/"rout"), on teste donc `wordnet.synsets(word)` (toute nature)
    pour les couvrir aussi ; les formes verbales sans aucune entrée WordNet (rares) restent
    lemmatisées normalement.
    """
    return tag.startswith("V") and word.endswith("ing") and bool(wordnet.synsets(word))


def preprocess(text: str, mode: str = "lemma") -> Preprocessed:
    out = Preprocessed(mode=mode)
    kept: list[TokenTrace] = []
    # Normalize typographic apostrophes (U+2019) to straight apostrophe (U+0027)
    text = (text or "").replace("’", "'")
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
            if "-" in t.normalized or _keeps_ing_noun_reading(tag, t.normalized):
                t.term = t.normalized
            else:
                t.term = _lemma(t.normalized, _wordnet_pos(tag))
    out.terms = [t.term for t in kept]
    return out


def analyze(text: str) -> list[str]:
    return preprocess(text).terms


def word_forms(word: str) -> set[str]:
    """Lemmes possibles d'un mot isolé (nom, verbe, adjectif) — pour surligner un texte."""
    low = word.lower()
    return {low} | {_lemma(low, p) for p in (wordnet.NOUN, wordnet.VERB, wordnet.ADJ)}
