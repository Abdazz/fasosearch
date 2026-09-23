"""Word2Vec (skip-gram, gensim) + similarité cosinus.

Vecteur d'un texte = moyenne des vecteurs de ses mots connus, pondérée par l'IDF,
puis normalisée (‖v‖ = 1) : le cosinus devient un simple produit scalaire.
"""
import numpy as np
from gensim.models import KeyedVectors, Word2Vec

from . import config


def train_word2vec(sentences: list[list[str]], params: dict = config.W2V_PARAMS) -> KeyedVectors:
    return Word2Vec(sentences=sentences, **params).wv


class Word2VecModel:
    def __init__(self, kv: KeyedVectors, docs_terms: list[list[str]], idf: dict[str, float]):
        self.kv = kv
        self.idf = idf
        self.default_idf = max(idf.values(), default=1.0)
        rows = []
        for terms in docs_terms:
            v, _ = self.text_vector(terms)
            rows.append(v if v is not None else np.zeros(kv.vector_size))
        self.doc_vectors = np.vstack(rows) if rows else np.zeros((0, kv.vector_size))

    def contains(self, word: str) -> bool:
        return word in self.kv.key_to_index

    def text_vector(self, terms: list[str]) -> tuple[np.ndarray | None, list[str]]:
        known = [t for t in terms if self.contains(t)]
        oov = [t for t in dict.fromkeys(terms) if not self.contains(t)]
        if not known:
            return None, oov
        weights = np.array([self.idf.get(t, self.default_idf) for t in known])
        if weights.sum() == 0:
            weights = np.ones(len(known))
        v = np.average(np.vstack([self.kv[t] for t in known]), axis=0, weights=weights)
        n = np.linalg.norm(v)
        return (v / n if n else None), oov

    def score(self, terms: list[str], threshold: float = config.W2V_THRESHOLD):
        q, oov = self.text_vector(terms)
        if q is None:
            return [], oov
        sims = self.doc_vectors @ q
        out = [(d, float(s)) for d, s in enumerate(sims)
               if np.any(self.doc_vectors[d]) and s >= threshold]
        return sorted(out, key=lambda x: (-x[1], x[0])), oov

    def neighbors(self, word: str, k: int = 5) -> list[tuple[str, float]]:
        if not self.contains(word):
            return []
        return [(w, float(s)) for w, s in self.kv.most_similar(word, topn=k)]

    def similarity(self, w1: str, w2: str) -> float | None:
        if not (self.contains(w1) and self.contains(w2)):
            return None
        return float(self.kv.similarity(w1, w2))

    def similar_documents(self, doc: int, k: int = 5) -> list[tuple[int, float]]:
        v = self.doc_vectors[doc]
        if not np.any(v):
            return []
        sims = self.doc_vectors @ v
        order = [d for d in np.argsort(-sims) if d != doc and np.any(self.doc_vectors[d])]
        return [(int(d), float(sims[d])) for d in order[:k]]
