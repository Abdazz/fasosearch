"""Index inversé : terme -> {document: fréquence}."""
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class InvertedIndex:
    postings: dict[str, dict[int, int]] = field(default_factory=dict)
    doc_lengths: list[int] = field(default_factory=list)
    max_tf: list[int] = field(default_factory=list)

    @classmethod
    def build(cls, docs_terms: list[list[str]]) -> "InvertedIndex":
        idx = cls()
        for d, terms in enumerate(docs_terms):
            counts = Counter(terms)
            for term, tf in counts.items():
                idx.postings.setdefault(term, {})[d] = tf
            idx.doc_lengths.append(len(terms))
            idx.max_tf.append(max(counts.values(), default=0))
        return idx

    @property
    def n_docs(self) -> int:
        return len(self.doc_lengths)

    @property
    def avg_length(self) -> float:
        return sum(self.doc_lengths) / self.n_docs if self.n_docs else 0.0

    @property
    def vocabulary(self) -> list[str]:
        return sorted(self.postings)

    def df(self, term: str) -> int:
        return len(self.postings.get(term, {}))

    def tf(self, term: str, doc: int) -> int:
        return self.postings.get(term, {}).get(doc, 0)

    def candidates(self, terms: list[str]) -> set[int]:
        out: set[int] = set()
        for t in terms:
            out.update(self.postings.get(t, {}))
        return out
