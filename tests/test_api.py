import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from tests.test_engine import engine  # noqa: F401  (réutilise la fixture)


@pytest.fixture(scope="module")
def client(engine):  # noqa: F811
    return TestClient(create_app(engine))


def test_search_endpoint_paginates(client):
    r = client.post("/api/search", json={"query": "intrusion", "model": "tfidf", "page": 99, "per_page": 7})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == body["pages"] and body["per_page"] == 10


def test_search_rejects_empty_query(client):
    r = client.post("/api/search", json={"query": "   "})
    assert r.status_code == 422 and "requête" in r.json()["detail"]


def test_document_404(client):
    r = client.get("/api/documents/Document_99")
    assert r.status_code == 404 and "Document_99" in r.json()["detail"]


def test_other_endpoints(client):
    assert client.get("/api/stats").json()["documents"] == 3
    assert set(client.post("/api/compare", json={"query": "intrusion"}).json()["models"]) == {"tfidf", "w2v", "bm25"}
    assert client.post("/api/preprocess", json={"text": "Networks!", "mode": "stem"}).json()["terms"] == ["network"]
    assert client.get("/api/w2v/neighbors", params={"word": "attacks"}).json()["term"] == "attack"
    assert len(client.get("/api/corpus").json()["documents"]) == 3
    assert len(client.get("/api/map").json()["points"]) == 3


def test_validation_error_missing_param(client):
    r = client.get("/api/w2v/neighbors")
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str) and "word" in r.json()["detail"]


def test_validation_error_invalid_type(client):
    r = client.post("/api/search", json={"query": "x", "per_page": "abc"})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "documents": 3}


def test_health_not_shadowed_by_static_mount(engine, tmp_path, monkeypatch):  # noqa: F811
    from backend.app import api as api_module
    (tmp_path / "index.html").write_text("<html>spa</html>")
    monkeypatch.setattr(api_module.config, "STATIC_DIR", tmp_path)
    c = TestClient(api_module.create_app(engine))
    assert c.get("/api/health").json()["status"] == "ok"
    assert "spa" in c.get("/").text


def test_authors_endpoints(client):
    r = client.get("/api/authors", params={"q": "a b"})
    assert r.status_code == 200 and [a["id"] for a in r.json()] == ["a-b"]
    assert client.get("/api/authors", params={"q": "x"}).json() == []
    assert client.get("/api/authors").json() == []
    p = client.get("/api/authors/a-b")
    assert p.status_code == 200 and p.json()["documents"][0]["id"] == "Document_01"
    r = client.get("/api/authors/personne")
    assert r.status_code == 404 and r.json() == {"detail": "Auteur introuvable."}


def test_document_has_author_links(client):
    assert client.get("/api/documents/Document_02").json()["document"]["author_links"] == [{"id": "c-d", "name": "C. D"}]
