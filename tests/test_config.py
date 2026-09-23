from backend.app import config


def test_paths_are_coherent():
    assert config.ROOT.name == "sri"
    assert config.DEVOIR == config.ROOT.parent
    assert config.ORIGINAL_EXCEL.name == "données textuelles.xlsx"
    assert config.CORPUS_EXCEL.name == "données textuelles - base complète.xlsx"
    assert config.CORPUS_EXCEL.parent == config.DEVOIR


def test_constants_match_spec():
    assert config.W2V_PARAMS == dict(vector_size=100, window=5, min_count=2,
                                     epochs=30, seed=42, sg=1, workers=1)
    assert config.W2V_THRESHOLD == 0.40
    assert (config.BM25_K1, config.BM25_B) == (1.5, 0.75)
    assert config.PER_PAGE_CHOICES == (10, 20, 50)
    assert config.DEFAULT_PER_PAGE == 10
