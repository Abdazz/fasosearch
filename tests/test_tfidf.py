import math

import numpy as np

from backend.app.index import InvertedIndex
from backend.app.tfidf import TfidfModel, tf_normalized


def test_tf_matches_course_slide_69():
    tf = tf_normalized("le chat mange le poisson et le chat dort".split())
    assert tf["chat"] == 2 / 3 and tf["le"] == 1.0


def _model():
    docs = [["network", "intrusion", "network"], ["cattle", "breed"], ["intrusion", "attack"]]
    return TfidfModel(InvertedIndex.build(docs))


def test_idf_is_log_n_over_df():
    m = _model()
    assert math.isclose(m.idf_of("intrusion"), math.log(3 / 2))
    assert math.isclose(m.idf_of("cattle"), math.log(3))
    assert m.idf_of("unknown") == 0.0


def test_document_against_itself_scores_one():
    m = _model()
    ranked = m.score(["cattle", "breed"])
    assert ranked[0][0] == 1 and math.isclose(ranked[0][1], 1.0)


def test_no_common_term_scores_zero_and_is_excluded():
    m = _model()
    assert m.score(["zzz"]) == []
    assert all(d != 1 for d, _ in m.score(["intrusion"]))


def test_ranking_and_contributions_sum_to_score():
    m = _model()
    ranked = m.score(["intrusion", "network"])
    assert ranked[0][0] == 0
    contrib = m.contributions(["intrusion", "network"], 0)
    assert math.isclose(sum(contrib.values()), ranked[0][1])
    assert contrib["network"] > contrib["intrusion"]


def test_doc_matrix_uses_course_tf():
    m = _model()
    j = m.vocab.index("intrusion")
    assert np.isclose(m.doc_matrix[0, j], (1 / 2) * math.log(3 / 2))
