import os

from scripts import build_index
from backend.app.preprocess import PREPROCESS_VERSION


def test_fingerprint_depends_on_content_not_mtime(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("même contenu")
    b.write_text("même contenu")
    os.utime(a, (1_000_000_000, 1_000_000_000))
    os.utime(b, (2_000_000_000, 2_000_000_000))
    assert build_index.fingerprint(a) == build_index.fingerprint(b)
    assert len(build_index.fingerprint(a)) == 64


def test_index_cache_key_is_stable_and_content_based(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus.xlsx"
    corpus.write_bytes(b"v1")
    monkeypatch.setattr(build_index.config, "CORPUS_EXCEL", corpus)
    monkeypatch.setattr(build_index.config, "W2V_EXTRA", tmp_path / "extra.txt")
    monkeypatch.setattr(build_index.config, "W2V_CS", tmp_path / "cs.txt")
    k1 = build_index.index_cache_key()
    os.utime(corpus, (1_500_000_000, 1_500_000_000))
    assert build_index.index_cache_key() == k1
    corpus.write_bytes(b"v2")
    assert build_index.index_cache_key() != k1
    assert len(k1) == 32


def test_restored_index_is_not_stale_after_touch(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus.xlsx"
    corpus.write_bytes(b"data")
    monkeypatch.setattr(build_index.config, "CORPUS_EXCEL", corpus)
    monkeypatch.setattr(build_index.config, "W2V_EXTRA", tmp_path / "extra.txt")
    monkeypatch.setattr(build_index.config, "W2V_CS", tmp_path / "cs.txt")
    for name in ("DOC_TERMS", "W2V_FILE"):
        p = tmp_path / name
        p.write_text("x")
        monkeypatch.setattr(build_index, name, p)
    fp = tmp_path / "fingerprint.txt"
    fp.write_text(build_index._current())
    monkeypatch.setattr(build_index, "FINGERPRINT", fp)
    os.utime(corpus, (2_100_000_000, 2_100_000_000))   # simule un nouveau clone
    assert build_index.is_stale() is False


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


def test_current_fingerprint_includes_preprocess_version(tmp_path, monkeypatch):
    monkeypatch.setattr(build_index.config, "CORPUS_EXCEL", tmp_path / "corpus.xlsx")
    monkeypatch.setattr(build_index.config, "W2V_EXTRA", tmp_path / "extra.txt")
    monkeypatch.setattr(build_index.config, "W2V_CS", tmp_path / "cs.txt")
    assert f"preprocess={PREPROCESS_VERSION}" in build_index._current()


def test_build_warns_loudly_when_extra_training_corpora_missing(tmp_path, monkeypatch, capsys):
    from backend.app.corpus import Document

    class FakeKV:
        key_to_index: dict = {}

        def save(self, path):
            pass

    monkeypatch.setattr(build_index.config, "CORPUS_EXCEL", tmp_path / "corpus.xlsx")
    monkeypatch.setattr(build_index.config, "W2V_EXTRA", tmp_path / "missing_extra.txt")
    monkeypatch.setattr(build_index.config, "W2V_CS", tmp_path / "missing_cs.txt")
    monkeypatch.setattr(build_index.config, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(build_index, "DOC_TERMS", tmp_path / "doc_terms.json")
    monkeypatch.setattr(build_index, "W2V_FILE", tmp_path / "w2v.kv")
    monkeypatch.setattr(build_index, "FINGERPRINT", tmp_path / "fingerprint.txt")
    docs = [Document("Document_01", "T", "Networks are secure systems.", "A", 2024, "U")]
    monkeypatch.setattr(build_index, "load_corpus", lambda path: docs)
    monkeypatch.setattr(build_index, "train_word2vec", lambda sentences: FakeKV())

    build_index.build()

    out = capsys.readouterr().out
    assert "ATTENTION" in out and "w2v_extra.txt" in out and "w2v_cs.txt" in out
    assert "—" not in out and "–" not in out
