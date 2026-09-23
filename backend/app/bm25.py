"""BM25 (modèle probabiliste, bonus TP 3) — comparaison avec TF-IDF.

score(q,d) = Σ_t IDF(t) · tf·(k1+1) / (tf + k1·(1 − b + b·|d|/avgdl))
IDF(t)     = log((N − df + 0.5)/(df + 0.5) + 1)
"""
import math

from . import config
from .index import InvertedIndex


class BM25Model:
    def __init__(self, index: InvertedIndex, k1: float = config.BM25_K1, b: float = config.BM25_B):
        self.index, self.k1, self.b = index, k1, b

    def idf(self, term: str) -> float:
        n, df = self.index.n_docs, self.index.df(term)
        return math.log((n - df + 0.5) / (df + 0.5) + 1)

    def term_score(self, term: str, doc: int) -> float:
        tf = self.index.tf(term, doc)
        if tf == 0:
            return 0.0
        norm = self.k1 * (1 - self.b + self.b * self.index.doc_lengths[doc] / self.index.avg_length)
        return self.idf(term) * tf * (self.k1 + 1) / (tf + norm)

    def contributions(self, terms: list[str], doc: int) -> dict[str, float]:
        out = {}
        for t in dict.fromkeys(terms):
            s = self.term_score(t, doc)
            if s > 0:
                out[t] = s
        return out

    def score(self, terms: list[str]) -> list[tuple[int, float]]:
        out = []
        for d in sorted(self.index.candidates(terms)):
            s = sum(self.contributions(terms, d).values())
            if s > 0:
                out.append((d, s))
        return sorted(out, key=lambda x: (-x[1], x[0]))
