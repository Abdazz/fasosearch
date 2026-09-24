import pytest

import run


@pytest.fixture
def ok_resources(monkeypatch, tmp_path):
    excel = tmp_path / "base.xlsx"
    excel.write_bytes(b"x")
    monkeypatch.setattr(run, "missing_resources", lambda: [])
    monkeypatch.setattr(run.config, "CORPUS_EXCEL", excel)


def test_settings_defaults(monkeypatch):
    for k in ("FASOSEARCH_MODE", "FASOSEARCH_HOST", "FASOSEARCH_PORT"):
        monkeypatch.delenv(k, raising=False)
    assert run.settings() == ("127.0.0.1", 8000, "dev")


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("FASOSEARCH_MODE", "prod")
    monkeypatch.setenv("FASOSEARCH_HOST", "0.0.0.0")
    monkeypatch.setenv("FASOSEARCH_PORT", "9123")
    assert run.settings() == ("0.0.0.0", 9123, "prod")


def test_settings_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("FASOSEARCH_MODE", "staging")
    with pytest.raises(SystemExit) as e:
        run.settings()
    assert e.value.code not in (0, None)


def test_prod_refuses_to_rebuild_stale_index(monkeypatch, ok_resources):
    monkeypatch.setattr(run.build_index, "is_stale", lambda: True)
    monkeypatch.setattr(run.build_index, "build", lambda: pytest.fail("build() ne doit pas être appelé en prod"))
    with pytest.raises(SystemExit) as e:
        run.prepare("prod")
    assert e.value.code not in (0, None)
    assert "production" in str(e.value.code)


def test_dev_rebuilds_stale_index(monkeypatch, ok_resources):
    calls = []
    monkeypatch.setattr(run.build_index, "is_stale", lambda: True)
    monkeypatch.setattr(run.build_index, "build", lambda: calls.append(1))
    run.prepare("dev")
    assert calls == [1]


def test_prod_ok_when_index_fresh(monkeypatch, ok_resources):
    monkeypatch.setattr(run.build_index, "is_stale", lambda: False)
    run.prepare("prod")


def test_missing_resources_exit(monkeypatch):
    monkeypatch.setattr(run, "missing_resources", lambda: ["nltk:wordnet"])
    with pytest.raises(SystemExit) as e:
        run.prepare("prod")
    assert "setup_resources" in str(e.value.code)
