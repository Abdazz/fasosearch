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
    assert 100 <= len(docs) <= 120


def test_new_documents_have_university(docs):
    assert all(d.university for d in docs[30:])


def test_everything_is_english(docs):
    DetectorFactory.seed = 0
    assert all(detect(d.abstract) == "en" for d in docs)


def test_no_field_contains_em_or_en_dash():
    """Lit les cellules brutes de la base (avant `load_corpus`, qui normalise d\u00e9j\u00e0 les tirets
    cadratins/demi-cadratins en tiret simple : passer par `load_corpus` rendrait ce test
    incapable d'\u00e9chouer, quel que soit le contenu r\u00e9el du fichier)."""
    import openpyxl

    em, en = chr(0x2014), chr(0x2013)
    wb = openpyxl.load_workbook(config.CORPUS_EXCEL, read_only=True)
    violations = [cell for row in wb.active.iter_rows(values_only=True) for cell in row
                  if isinstance(cell, str) and (em in cell or en in cell)]
    assert not violations, violations


def test_url_column_after_university():
    import openpyxl
    header = [c.value for c in next(openpyxl.load_workbook(config.CORPUS_EXCEL, read_only=True).active.iter_rows(max_row=1))]
    assert header[header.index("University") + 1] == "URL"


def test_urls_are_https_and_never_openalex(docs):
    urls = [d.url for d in docs if d.url]
    assert len(urls) >= 110
    assert all(u.startswith("https://") and "openalex.org" not in u for u in urls)


def test_no_bogus_author_entries(docs):
    """Chaque écriture d'auteur (séparée par ';') doit désigner une personne, pas une entité
    géographique ou un espace réservé : au moins 2 mots, jamais vide, 'Unknown' ou
    'Burkina Faso'."""
    for d in docs:
        for entry in d.authors.split(";"):
            name = entry.strip()
            assert name, f"{d.id} : écriture d'auteur vide"
            assert name.lower() != "unknown", f"{d.id} : 'Unknown' comme auteur"
            assert name.lower() != "burkina faso", f"{d.id} : 'Burkina Faso' comme auteur"
            assert len(name.split()) >= 2, f"{d.id} : écriture d'auteur à un seul mot ({name!r})"
