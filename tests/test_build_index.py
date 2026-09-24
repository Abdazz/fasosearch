from scripts import build_index


def test_fingerprint_changes_with_file(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a")
    f1 = build_index.fingerprint(p)
    p.write_text("abc")
    assert build_index.fingerprint(p) != f1


def test_fingerprint_of_missing_file():
    assert build_index.fingerprint(build_index.config.ROOT / "nope.xyz") == "absent"


def test_read_extra_lines_filters_blank_and_tolerates_missing_file(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("a\n\nb\n   \nc")
    assert build_index._read_extra_lines(p) == ["a", "b", "c"]
    assert build_index._read_extra_lines(tmp_path / "missing.txt") == []


def test_current_fingerprint_includes_w2v_cs(tmp_path, monkeypatch):
    monkeypatch.setattr(build_index.config, "CORPUS_EXCEL", tmp_path / "corpus.xlsx")
    monkeypatch.setattr(build_index.config, "W2V_EXTRA", tmp_path / "extra.txt")
    cs = tmp_path / "cs.txt"
    monkeypatch.setattr(build_index.config, "W2V_CS", cs)
    before = build_index._current()
    cs.write_text("hello")
    after = build_index._current()
    assert before != after
