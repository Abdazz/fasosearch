import requests

from backend.app import config
from scripts.augment_data import QuotaExceeded
from scripts.fetch_w2v_cs import (MAX_PAGES_PER_SUBFIELD, MIN_WORDS, SUBFIELDS,
                                  fetch_subfield_raw, indexed_titles, keep_line, main)


def test_subfields_match_spec():
    assert SUBFIELDS == {
        "1702": "Artificial Intelligence",
        "1705": "Computer Networks and Communications",
        "1707": "Computer Vision and Pattern Recognition",
        "1710": "Information Systems",
        "1712": "Software",
        "1711": "Signal Processing",
        "1708": "Hardware and Architecture",
        "1706": "Computer Science Applications",
    }


def test_keep_line_rejects_short_abstract():
    work = {"title": "Short one", "abstract_inverted_index": {"a": [0], "b": [1]}}
    seen = set()
    assert keep_line(work, seen, min_words=MIN_WORDS) is None
    assert seen == set()


def test_keep_line_formats_title_dot_abstract():
    words = {str(i): [i] for i in range(MIN_WORDS)}
    work = {"title": "A Great Paper", "abstract_inverted_index": words}
    seen = set()
    line = keep_line(work, seen, min_words=MIN_WORDS)
    assert line.startswith("A Great Paper. ")
    assert len(line.split(". ", 1)[1].split()) == MIN_WORDS
    assert seen  # le titre normalisé a été ajouté


def test_keep_line_dedupes_by_normalized_title():
    words = {str(i): [i] for i in range(MIN_WORDS)}
    seen = set()
    work1 = {"title": "Same Title!", "abstract_inverted_index": words}
    work2 = {"title": "same title", "abstract_inverted_index": words}
    assert keep_line(work1, seen, min_words=MIN_WORDS) is not None
    assert keep_line(work2, seen, min_words=MIN_WORDS) is None  # doublon normalisé


def test_keep_line_rejects_titles_already_in_seen_set():
    words = {str(i): [i] for i in range(MIN_WORDS)}
    work = {"title": "Already Indexed", "abstract_inverted_index": words}
    seen = {"alreadyindexed"}
    assert keep_line(work, seen, min_words=MIN_WORDS) is None


def test_keep_line_requires_a_title():
    words = {str(i): [i] for i in range(MIN_WORDS)}
    work = {"title": None, "abstract_inverted_index": words}
    assert keep_line(work, set(), min_words=MIN_WORDS) is None


def test_indexed_titles_uses_normalized_corpus_titles(monkeypatch):
    class FakeDoc:
        def __init__(self, title):
            self.title = title

    import scripts.fetch_w2v_cs as mod
    monkeypatch.setattr(mod, "load_corpus", lambda path: [FakeDoc("Hello World!"), FakeDoc("Other")])
    assert indexed_titles() == {"helloworld", "other"}


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json


def _page(results, next_cursor):
    return {"results": results, "meta": {"next_cursor": next_cursor}}


def test_fetch_subfield_raw_paginates_until_cursor_exhausted(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OPENALEX_CACHE_DIR", tmp_path / "cache")
    pages = [_page([{"id": 1}], "c2"), _page([{"id": 2}], "c3"), _page([{"id": 3}], None)]
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        return _FakeResponse(json_data=pages[len(calls) - 1])

    monkeypatch.setattr(requests, "get", fake_get)
    out = fetch_subfield_raw("1702", max_pages=MAX_PAGES_PER_SUBFIELD, per_page=200)
    assert [w["id"] for w in out] == [1, 2, 3]
    assert len(calls) == 3  # s'arrête dès que next_cursor est vide, sans consommer le budget


def test_fetch_subfield_raw_stops_at_max_pages_even_if_more_available(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OPENALEX_CACHE_DIR", tmp_path / "cache")
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        return _FakeResponse(json_data=_page([{"id": len(calls)}], f"c{len(calls) + 1}"))

    monkeypatch.setattr(requests, "get", fake_get)
    out = fetch_subfield_raw("1702", max_pages=3, per_page=200)
    assert len(calls) == 3  # respecte le budget malgré un curseur toujours non vide
    assert len(out) == 3


def test_main_propagates_quota_exceeded_and_writes_no_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "W2V_CS", tmp_path / "w2v_cs.txt")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    def boom():
        raise QuotaExceeded(120)

    import scripts.fetch_w2v_cs as mod
    monkeypatch.setattr(mod, "_run", boom)
    try:
        main()
        assert False, "main() aurait dû sys.exit(1)"
    except SystemExit as e:
        assert e.code == 1
    assert not (tmp_path / "w2v_cs.txt").exists()
    assert "Quota" in capsys.readouterr().out
