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
