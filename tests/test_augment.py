import json

import pytest
import requests

from backend.app import config
from scripts.augment_data import (CS_LEXICON, PER_SUBFIELD, QuotaExceeded, bf_institutions,
                                  clean, is_computer_science, next_ids, norm_title,
                                  rebuild_abstract, select_diverse, _get)


def test_rebuild_abstract_orders_words():
    inv = {"world": [1], "hello": [0], "again": [3], "hello_": [2]}
    assert rebuild_abstract(inv) == "hello world hello_ again"
    assert rebuild_abstract(None) == ""


def test_norm_title_ignores_case_accents_punctuation():
    assert norm_title("Réseaux: l'Étude!") == norm_title("reseaux letude")


def test_clean_strips_tags_and_abstract_prefix():
    assert clean("<p>Abstract: Hello   <b>world</b></p>") == "Hello world"


def test_bf_institutions_keeps_only_burkina():
    work = {"authorships": [
        {"institutions": [{"display_name": "Université Norbert Zongo", "country_code": "BF"}]},
        {"institutions": [{"display_name": "Sorbonne", "country_code": "FR"},
                          {"display_name": "Université Norbert Zongo", "country_code": "BF"}]},
        {"institutions": [{"display_name": "Université Joseph Ki-Zerbo", "country_code": "BF"}]},
    ]}
    assert bf_institutions(work) == ["Université Norbert Zongo", "Université Joseph Ki-Zerbo"]


def test_select_diverse_caps_subfields_and_prefers_recent():
    cands = [{"id": i, "year": 2000 + i, "subfield": "A" if i < 6 else "B"} for i in range(10)]
    chosen = select_diverse(cands, n=5, per_subfield=2)
    assert [c["id"] for c in chosen] == [9, 8, 5, 4]  # 2 de B, 2 de A ; plus assez pour 5
    assert len(select_diverse(cands, n=3, per_subfield=5)) == 3


def test_next_ids_continue_numbering():
    assert next_ids(31, 3) == ["Document_31", "Document_32", "Document_33"]
    assert next_ids(100, 1) == ["Document_100"]


def test_per_subfield_is_15():
    assert PER_SUBFIELD == 15


def test_cs_lexicon_has_at_least_60_terms():
    assert len(CS_LEXICON) >= 60
    assert all(t == t.lower() for t in CS_LEXICON)


def test_is_computer_science_true_with_two_distinct_terms():
    text = "This paper presents a machine learning model for network intrusion detection."
    assert is_computer_science(text) is True


def test_is_computer_science_false_with_fewer_than_two_terms():
    assert is_computer_science("Only one keyword here: algorithm.") is False
    assert is_computer_science("Cattle farming and agriculture in rural areas.") is False


def test_is_computer_science_is_case_insensitive():
    text = "MACHINE LEARNING and NEURAL networks for classification"
    assert is_computer_science(text) is True


# ---------------------------------------------------------------- cache disque / quota
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


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    d = tmp_path / "openalex_cache"
    monkeypatch.setattr(config, "OPENALEX_CACHE_DIR", d)
    return d


def test_get_reads_from_cache_without_network_call(cache_dir, monkeypatch):
    calls = []
    monkeypatch.setattr(requests, "get", lambda *a, **k: calls.append(1) or _FakeResponse())
    first = _get("works", {"filter": "x", "per-page": 1})
    assert len(calls) == 1
    second = _get("works", {"filter": "x", "per-page": 1})
    assert len(calls) == 1  # pas de second appel réseau : lu depuis le cache
    assert first == second


def test_get_writes_cache_file_on_success(cache_dir, monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResponse(json_data={"ok": True}))
    _get("works", {"filter": "y"})
    files = list(cache_dir.glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text()) == {"ok": True}


def test_get_raises_quota_exceeded_on_429_without_retry_loop(cache_dir, monkeypatch):
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        return _FakeResponse(status_code=429, headers={"Retry-After": "120"})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with pytest.raises(QuotaExceeded) as exc_info:
        _get("works", {"filter": "z"})
    assert exc_info.value.retry_after_seconds == 120
    assert len(calls) == 1  # aucune nouvelle tentative sur 429


def test_get_retries_three_times_on_other_network_errors(cache_dir, monkeypatch):
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    result = _get("works", {"filter": "w"})
    assert result == {}
    assert len(calls) == 4  # 1 essai + 3 nouvelles tentatives
