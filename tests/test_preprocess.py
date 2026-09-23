from backend.app.preprocess import STOPWORDS, analyze, preprocess, word_forms


def test_pipeline_removes_stopwords_and_lemmatizes():
    p = preprocess("The networks were detected in the study.")
    assert p.terms == ["network", "detect"]
    removed = {t.raw: t.removed_by for t in p.tokens if t.removed_by}
    assert removed == {"The": "stopword", "were": "stopword", "in": "stopword",
                       "the": "stopword", "study": "stopword", ".": "punctuation"}


def test_keeps_hyphenated_technical_terms():
    assert analyze("COVID-19 tweets and NSL-KDD") == ["covid-19", "tweet", "nsl-kdd"]


def test_numbers_and_punctuation_only_gives_no_terms():
    p = preprocess("2024 !!! 3.5")
    assert p.terms == []
    assert {t.removed_by for t in p.tokens} == {"number", "punctuation"}


def test_stem_mode_uses_porter():
    assert preprocess("detection networks", mode="stem").terms == ["detect", "network"]


def test_same_pipeline_for_query_and_document():
    assert analyze("Intrusion Detection Systems") == analyze("intrusion detection systems")


def test_domain_stopwords_present():
    assert {"paper", "study", "propose", "approach", "authors"} <= STOPWORDS


def test_word_forms_covers_verbs_and_nouns():
    assert "detect" in word_forms("detected")
    assert "network" in word_forms("Networks")


def test_to_dict_shape():
    d = preprocess("Networks").to_dict()
    assert d == {"mode": "lemma", "terms": ["network"],
                 "tokens": [{"raw": "Networks", "normalized": "networks", "term": "network", "removed_by": None}]}
