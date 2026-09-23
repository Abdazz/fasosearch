import openpyxl

from backend.app import config
from backend.app.corpus import COLUMNS, Document, load_corpus, normalize_dashes


def _write(path, header, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(r)
    wb.save(path)


def test_load_corpus_with_university(tmp_path):
    p = tmp_path / "c.xlsx"
    _write(p, COLUMNS, [["Document_01", "T1", "A1", "X; Y", 2024, "Université Norbert Zongo"]])
    docs = load_corpus(p)
    assert docs == [Document("Document_01", "T1", "A1", "X; Y", 2024, "Université Norbert Zongo")]
    assert docs[0].text == "T1. A1"


def test_load_corpus_without_university_column(tmp_path):
    p = tmp_path / "c.xlsx"
    _write(p, COLUMNS[:5], [["Document_02", "T2", "A2", "Z", None], [None, None, None, None, None]])
    docs = load_corpus(p)
    assert len(docs) == 1
    assert docs[0].university == "" and docs[0].year is None


def test_original_excel_has_30_documents():
    docs = load_corpus(config.ORIGINAL_EXCEL)
    assert len(docs) == 30
    assert docs[0].id == "Document_01" and docs[-1].id == "Document_30"


def test_normalize_dashes_spaced_em_and_en_dash_become_spaced_hyphen():
    assert normalize_dashes("Burkina Faso — le cas") == "Burkina Faso - le cas"
    assert normalize_dashes("Burkina Faso – le cas") == "Burkina Faso - le cas"


def test_normalize_dashes_unspaced_dash_becomes_unspaced_hyphen():
    assert normalize_dashes("2010–2020") == "2010-2020"
    assert normalize_dashes("2010—2020") == "2010-2020"


def test_normalize_dashes_leaves_plain_text_untouched():
    assert normalize_dashes("no dash here") == "no dash here"


def test_load_corpus_normalizes_dashes_in_text_fields_but_not_id():
    p = None
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "c.xlsx"
        _write(p, COLUMNS, [["Document_01", "Title — with dash", "Abs – tract",
                              "A — B", 2024, "Uni – versity"]])
        docs = load_corpus(p)
    doc = docs[0]
    assert doc.id == "Document_01"
    assert doc.title == "Title - with dash"
    assert doc.abstract == "Abs - tract"
    assert doc.authors == "A - B"
    assert doc.university == "Uni - versity"
