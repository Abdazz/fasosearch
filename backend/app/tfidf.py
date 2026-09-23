"""Modèle vectoriel TF-IDF + similarité cosinus (implémentation manuelle, formules du cours).

TF(t,d)  = tf(t,d) / max_t' tf(t',d)          (slide 69)
IDF(t)   = log(N / df(t))
w(t,d)   = TF(t,d) × IDF(t)
score    = cos(q, d) = q·d / (‖q‖ ‖d‖)
"""
import math
from collections import Counter

import numpy as np

from .index import InvertedIndex


def tf_normalized(terms: list[str]) -> dict[str, float]:
    counts = Counter(terms)
    m = max(counts.values(), default=0)
    return {t: c / m for t, c in counts.items()} if m else {}


class TfidfModel:
    def __init__(self, index: InvertedIndex):
        self.index = index
        self.vocab = index.vocabulary
        self.term_idx = {t: i for i, t in enumerate(self.vocab)}
        n = index.n_docs
        self.idf = np.array([math.log(n / index.df(t)) for t in self.vocab])
        self.doc_matrix = np.zeros((n, len(self.vocab)))
        for term, post in index.postings.items():
            j = self.term_idx[term]
            for d, tf in post.items():
                self.doc_matrix[d, j] = (tf / index.max_tf[d]) * self.idf[j]
        self.doc_norms = np.linalg.norm(self.doc_matrix, axis=1)

    def idf_of(self, term: str) -> float:
        j = self.term_idx.get(term)
        return float(self.idf[j]) if j is not None else 0.0

    def idf_map(self) -> dict[str, float]:
        return {t: float(self.idf[j]) for t, j in self.term_idx.items()}

    def query_vector(self, terms: list[str]) -> np.ndarray:
        q = np.zeros(len(self.vocab))
        for t, w in tf_normalized([t for t in terms if t in self.term_idx]).items():
            j = self.term_idx[t]
            q[j] = w * self.idf[j]
        return q

    def score(self, terms: list[str]) -> list[tuple[int, float]]:
        q = self.query_vector(terms)
        qn = np.linalg.norm(q)
        if qn == 0:
            return []
        out = []
        for d in sorted(self.index.candidates(terms)):
            if self.doc_norms[d] == 0:
                continue
            s = float(self.doc_matrix[d] @ q / (self.doc_norms[d] * qn))
            if s > 0:
                out.append((d, s))
        return sorted(out, key=lambda x: (-x[1], x[0]))

    def contributions(self, terms: list[str], doc: int) -> dict[str, float]:
        q = self.query_vector(terms)
        denom = np.linalg.norm(q) * self.doc_norms[doc]
        if denom == 0:
            return {}
        out = {}
        for t in dict.fromkeys(terms):
            j = self.term_idx.get(t)
            if j is not None and self.doc_matrix[doc, j] > 0 and q[j] > 0:
                out[t] = float(q[j] * self.doc_matrix[doc, j] / denom)
        return out
