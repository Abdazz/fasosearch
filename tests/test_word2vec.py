import numpy as np
import pytest

from backend.app import config
from backend.app.word2vec import Word2VecModel, train_word2vec

SECURITY = ["network", "intrusion", "attack", "detection", "malware", "traffic"]
FARM = ["cattle", "breed", "farmer", "crop", "livestock", "maize"]


@pytest.fixture(scope="module")
def model():
    rng = np.random.default_rng(0)
    sentences = [[str(w) for w in rng.choice(SECURITY, 6)] for _ in range(400)] + \
                [[str(w) for w in rng.choice(FARM, 6)] for _ in range(400)]
    params = {**config.W2V_PARAMS, "vector_size": 20, "epochs": 20}
    kv = train_word2vec(sentences, params)
    docs = [["intrusion", "attack", "traffic"], ["cattle", "maize", "farmer"], ["unknownword"]]
    return Word2VecModel(kv, docs, idf={"intrusion": 1.0, "cattle": 1.0})


def test_related_words_are_closer(model):
    assert model.similarity("intrusion", "attack") > model.similarity("intrusion", "cattle")


def test_score_ranks_semantic_document_first_even_without_shared_word(model):
    ranked, oov = model.score(["malware", "network"], threshold=0.0)
    assert ranked[0][0] == 0 and oov == []


def test_out_of_vocabulary_terms_reported_and_all_oov_is_safe(model):
    ranked, oov = model.score(["zzzz", "yyyy"])
    assert ranked == [] and oov == ["zzzz", "yyyy"]


def test_empty_doc_vector_never_matches(model):
    assert not np.any(model.doc_vectors[2])
    ranked, _ = model.score(["intrusion"], threshold=-1.0)
    assert 2 not in [d for d, _ in ranked]


def test_threshold_filters(model):
    ranked, _ = model.score(["intrusion"], threshold=0.99)
    assert all(s >= 0.99 for _, s in ranked)


def test_neighbors_and_similar_documents(model):
    assert model.neighbors("zzzz") == []
    assert len(model.neighbors("intrusion", k=3)) == 3
    assert model.similar_documents(0, k=1)[0][0] == 1
