import openpyxl

from backend.app import config
from backend.app.corpus import COLUMNS, Document, load_corpus


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
