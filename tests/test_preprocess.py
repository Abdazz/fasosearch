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


def test_contractions_removed_as_stopwords_straight_apostrophe():
    assert preprocess("don't stop networks").terms == ["stop", "network"]


def test_contractions_removed_as_stopwords_typographic_apostrophe():
    assert preprocess("don’t stop networks").terms == ["stop", "network"]


def test_ing_nouns_get_consistent_lemma_regardless_of_pos_context():
    # "learning"/"routing" sont tantôt étiquetés nom, tantôt verbe selon le contexte
    # (perdu ici après le retrait des mots vides) : les trois formulations doivent
    # donner le même terme.
    assert analyze("machine learning") == ["machine", "learning"]
    assert analyze("learning algorithms") == ["learning", "algorithm"]
    assert analyze("is learning fast") == ["learning", "fast"]
    assert analyze("routing protocols") == ["routing", "protocol"]
    assert analyze("the routing of packets") == ["routing", "packet"]


def test_past_tense_verbs_still_lemmatize_normally():
    assert analyze("detected") == ["detect"]


def test_verbal_ing_forms_still_lemmatize_to_the_verb():
    # Round 2 (contrôle) : la première version de la règle testait `wordnet.synsets(word)`
    # (toute nature), ce qui classait aussi "detecting" comme nom (WordNet le liste comme
    # synonyme secondaire du synset "detection"), cassant l'appariement detect/detecting
    # ("detecting intrusions" restait "detecting" au lieu de "detect", contrairement à
    # "detected intrusions"). "detecting"/"attacking" n'ont pas de lecture nominale
    # principale dans WordNet (contrairement à "learning"/"routing") et doivent donc rester
    # lemmatisés en verbe dans tous les contextes.
    assert analyze("detecting intrusions") == ["detect", "intrusion"]
    assert analyze("detected intrusions") == ["detect", "intrusion"]
    assert analyze("attacking") == ["attack"]
    assert analyze("attacked systems") == ["attack", "system"]


def test_cs_ing_nouns_outside_wordnet_still_kept_as_nouns():
    # "routing" et consorts n'ont aucun sens nominal dans WordNet (seulement verbal) : la
    # liste explicite CS_ING_NOUNS les couvre quand même, sans réintroduire le faux positif
    # "detecting" corrigé ci-dessus.
    assert analyze("cloud computing") == ["cloud", "computing"]
    assert analyze("is computing fast") == ["computing", "fast"]
    assert analyze("social networking") == ["social", "networking"]
