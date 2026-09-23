import pytest
from langdetect import DetectorFactory, detect

from backend.app import config
from backend.app.corpus import load_corpus

pytestmark = pytest.mark.skipif(not config.CORPUS_EXCEL.exists(), reason="base complète non générée")


@pytest.fixture(scope="module")
def docs():
    return load_corpus(config.CORPUS_EXCEL)


def test_first_30_rows_identical_to_original(docs):
    original = load_corpus(config.ORIGINAL_EXCEL)
    for o, d in zip(original, docs[:30]):
        assert (o.id, o.title, o.abstract, o.authors, o.year) == (d.id, d.title, d.abstract, d.authors, d.year)


def test_ids_unique_and_continuous(docs):
    assert [d.id for d in docs] == ["Document_%02d" % i for i in range(1, len(docs) + 1)]


def test_size_about_100(docs):
    assert 90 <= len(docs) <= 110


def test_new_documents_have_university(docs):
    assert all(d.university for d in docs[30:])


def test_everything_is_english(docs):
    DetectorFactory.seed = 0
    assert all(detect(d.abstract) == "en" for d in docs)


def test_no_field_contains_em_or_en_dash(docs):
    for d in docs:
        for value in (d.title, d.abstract, d.authors, d.university):
            assert "—" not in value and "–" not in value
