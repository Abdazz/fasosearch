"""Routes HTTP de FasoSearch."""
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .engine import SearchEngine


class SearchBody(BaseModel):
    query: str
    model: str = "tfidf"
    lang: str = "auto"
    page: int = 1
    per_page: int = config.DEFAULT_PER_PAGE


class CompareBody(BaseModel):
    query: str
    lang: str = "auto"
    k: int = 10


class PreprocessBody(BaseModel):
    text: str
    mode: str = "lemma"


def _require_query(q: str) -> None:
    if not q or not q.strip():
        raise HTTPException(422, "La requête est vide : saisissez au moins un mot.")


def create_app(engine: SearchEngine) -> FastAPI:
    app = FastAPI(title="FasoSearch", version="1.0")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        field_names = ", ".join(str(e["loc"][-1]) for e in exc.errors())
        return JSONResponse(
            status_code=422,
            content={"detail": f"Paramètres invalides : {field_names}"}
        )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "documents": len(engine.docs)}

    @app.get("/api/stats")
    def stats():
        return engine.stats()

    @app.post("/api/search")
    def search(body: SearchBody):
        _require_query(body.query)
        return engine.search(body.query, body.model, body.lang, body.page, body.per_page)

    @app.post("/api/compare")
    def compare(body: CompareBody):
        _require_query(body.query)
        return engine.compare(body.query, body.lang, max(1, min(body.k, 20)))

    @app.get("/api/documents/{doc_id}")
    def document(doc_id: str, query: str = "", model: str = "tfidf", lang: str = "auto"):
        d = engine.document(doc_id, query, model, lang)
        if d is None:
            raise HTTPException(404, f"Document introuvable : {doc_id}")
        return d

    @app.get("/api/authors")
    def authors(q: str = ""):
        return engine.search_authors(q)

    @app.get("/api/authors/{author_id}")
    def author(author_id: str):
        a = engine.author(author_id)
        if a is None:
            raise HTTPException(404, "Auteur introuvable.")
        return a

    @app.post("/api/preprocess")
    def preprocess(body: PreprocessBody):
        return engine.preprocess(body.text, body.mode)

    @app.get("/api/w2v/neighbors")
    def neighbors(word: str):
        return engine.neighbors(word)

    @app.get("/api/corpus")
    def corpus():
        return engine.corpus()

    @app.get("/api/map")
    def doc_map():
        return engine.doc_map()

    if (config.STATIC_DIR / "index.html").exists():
        app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="static")
    else:
        @app.get("/")
        def no_frontend():
            return JSONResponse({"detail": "Interface non compilée : cd frontend && npm run build"})

    return app
