from backend.app.index import InvertedIndex

DOCS = [["network", "intrusion", "network"], ["cattle", "breed"], ["intrusion", "attack"]]


def test_postings_and_stats():
    idx = InvertedIndex.build(DOCS)
    assert idx.postings["network"] == {0: 2}
    assert idx.postings["intrusion"] == {0: 1, 2: 1}
    assert idx.df("intrusion") == 2 and idx.df("unknown") == 0
    assert idx.tf("network", 0) == 2 and idx.tf("network", 1) == 0
    assert idx.doc_lengths == [3, 2, 2]
    assert idx.max_tf == [2, 1, 1]
    assert idx.n_docs == 3 and abs(idx.avg_length - 7 / 3) < 1e-9
    assert idx.vocabulary == ["attack", "breed", "cattle", "intrusion", "network"]


def test_candidates_union_of_postings():
    idx = InvertedIndex.build(DOCS)
    assert idx.candidates(["intrusion", "breed", "zzz"]) == {0, 1, 2}
    assert idx.candidates(["zzz"]) == set()


def test_empty_document_is_allowed():
    idx = InvertedIndex.build([["a"], []])
    assert idx.doc_lengths == [1, 0] and idx.max_tf == [1, 0]
