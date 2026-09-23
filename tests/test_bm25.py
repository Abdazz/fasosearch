import math

from backend.app.bm25 import BM25Model
from backend.app.index import InvertedIndex


def test_idf_formula():
    m = BM25Model(InvertedIndex.build([["a"], ["b"], ["a", "c"]]))
    assert math.isclose(m.idf("a"), math.log((3 - 2 + 0.5) / (2 + 0.5) + 1))


def test_shorter_document_wins_at_equal_frequency():
    docs = [["intrusion", "x", "y", "z", "w", "v"], ["intrusion", "x"], ["other"]]
    ranked = BM25Model(InvertedIndex.build(docs)).score(["intrusion"])
    assert [d for d, _ in ranked] == [1, 0]


def test_contributions_sum_to_score_and_unknown_terms_ignored():
    m = BM25Model(InvertedIndex.build([["a", "b"], ["b"], ["c"]]))
    ranked = dict(m.score(["a", "b", "zzz"]))
    c = m.contributions(["a", "b", "zzz"], 0)
    assert set(c) == {"a", "b"} and math.isclose(sum(c.values()), ranked[0])
    assert m.score(["zzz"]) == []
