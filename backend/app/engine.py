"""Orchestration : requête → langue → prétraitement → scores → classement → pagination."""
import json
import math
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np
from gensim.models import KeyedVectors

from . import config
from .authors import AuthorIndex, highlight_name
from .bm25 import BM25Model
from .corpus import Document, load_corpus
from .index import InvertedIndex
from .language import Translator, analyze_language
from .preprocess import STOPWORDS, preprocess, word_forms
from .tfidf import TfidfModel
from .word2vec import Word2VecModel

MODELS = ("tfidf", "w2v", "bm25")
WORD_RE = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


# ---------------------------------------------------------------- fonctions pures
def paginate(n: int, page: int, per_page: int) -> tuple[int, int, int, int]:
    per_page = per_page if per_page in config.PER_PAGE_CHOICES else config.DEFAULT_PER_PAGE
    pages = max(1, math.ceil(n / per_page))
    page = min(max(1, page), pages)
    return page, per_page, (page - 1) * per_page, pages


def highlight(text: str, terms: set[str]) -> list[dict]:
    """Découpe le texte en segments ; hit=True si le mot a un lemme présent dans `terms`."""
    segs, last = [], 0
    for m in WORD_RE.finditer(text):
        w = m.group()
        if w.lower() not in STOPWORDS and word_forms(w) & terms:
            if m.start() > last:
                segs.append({"text": text[last:m.start()], "hit": False})
            segs.append({"text": w, "hit": True})
            last = m.end()
    if last < len(text):
        segs.append({"text": text[last:], "hit": False})
    return segs


def make_snippet(text: str, terms: set[str], max_chars: int = 320) -> list[dict]:
    text = text.strip()
    sentences = SENTENCE_RE.split(text)
    start = next((i for i, s in enumerate(sentences) if any(h["hit"] for h in highlight(s, terms))), 0)
    snippet = ""
    for s in sentences[start:]:
        if snippet and len(snippet) + len(s) > max_chars:
            break
        snippet = f"{snippet} {s}".strip()
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rsplit(" ", 1)[0]
    prefix = "… " if start > 0 else ""
    suffix = " …" if len(prefix + snippet) < len(text) and not text.endswith(snippet) else ""
    return highlight(prefix + snippet + suffix, terms)


def _public_url(url: str | None) -> str | None:
    """URL affichable via le bouton "Source" : seulement une page en https, jamais vide et
    jamais un schéma risqué (javascript:, http: non chiffré...)."""
    return url if url and url.startswith("https://") else None


def _check_alignment(ids_stored: list[str], ids_docs: list[str]) -> None:
    """Vérifie que l'index en cache (doc_terms.json) correspond au corpus actuel.

    Lève systématiquement (contrairement à un `assert`, qui disparaît sous `python -O`).
    """
    if ids_stored != ids_docs:
        raise RuntimeError("index obsolète : relancer scripts/build_index.py")


# ---------------------------------------------------------------- moteur
class SearchEngine:
    def __init__(self, docs: list[Document], doc_terms: list[list[str]], kv: KeyedVectors,
                 translator: Translator | None = None, aliases: Path | None = None):
        self.docs = docs
        self.doc_terms = doc_terms
        self.by_id = {d.id: i for i, d in enumerate(docs)}
        self.index = InvertedIndex.build(doc_terms)
        self.tfidf = TfidfModel(self.index)
        self.bm25 = BM25Model(self.index)
        self.w2v = Word2VecModel(kv, doc_terms, self.tfidf.idf_map())
        self.translator = translator or Translator()
        self.translator.warm_up()
        self.author_index = AuthorIndex(docs, aliases)
        self._map = self._compute_map()

    @classmethod
    def load(cls) -> "SearchEngine":
        from scripts.build_index import DOC_TERMS, W2V_FILE
        docs = load_corpus(config.CORPUS_EXCEL)
        stored = json.loads(DOC_TERMS.read_text(encoding="utf-8"))
        _check_alignment(stored["ids"], [d.id for d in docs])
        return cls(docs, stored["terms"], KeyedVectors.load(str(W2V_FILE)), aliases=config.AUTHOR_ALIASES)

    # -- requête
    def analyze_query(self, query: str, lang: str = "auto", model: str = "tfidf") -> dict:
        info = analyze_language(query.strip(), lang, self.translator)
        pre = preprocess(info.english)
        oov = [t for t in dict.fromkeys(pre.terms) if not self.w2v.contains(t)] if model == "w2v" else []
        return {"original": info.original, "language": info.language, "forced": info.forced,
                "translated": info.translated, "method": info.method, "english": info.english,
                "preprocessing": pre.to_dict(), "terms": pre.terms, "oov": oov}

    def _rank(self, model: str, terms: list[str]) -> list[tuple[int, float]]:
        if model == "w2v":
            return self.w2v.score(terms)[0]
        if model == "bm25":
            return self.bm25.score(terms)
        return self.tfidf.score(terms)

    def _contributions(self, model: str, terms: list[str], d: int) -> list[dict]:
        if model == "w2v":
            return []
        src = self.bm25 if model == "bm25" else self.tfidf
        c = src.contributions(terms, d)
        return [{"term": t, "value": v} for t, v in sorted(c.items(), key=lambda x: -x[1])]

    def search(self, query: str, model: str = "tfidf", lang: str = "auto",
               page: int = 1, per_page: int = config.DEFAULT_PER_PAGE) -> dict:
        t0 = time.perf_counter()
        model = model if model in MODELS else "tfidf"
        q = self.analyze_query(query, lang, model)
        terms = q["terms"]
        ranked = self._rank(model, terms) if terms else []
        message = None
        if not terms:
            message = "no_terms"
        elif model == "w2v" and len(q["oov"]) == len(set(terms)):
            message = "all_oov"
        elif not ranked:
            message = "no_match"
        page, per_page, start, pages = paginate(len(ranked), page, per_page)
        top = ranked[0][1] if ranked else 1.0
        tset = set(terms)
        results = []
        for rank, (d, s) in enumerate(ranked[start:start + per_page], start=start + 1):
            doc = self.docs[d]
            results.append({
                "rank": rank, "id": doc.id, "title": doc.title, "authors": doc.authors,
                "university": doc.university, "year": doc.year, "score": s,
                "score_ratio": s / top if top > 0 else 0.0,
                "snippet": make_snippet(doc.abstract, tset),
                "contributions": self._contributions(model, terms, d),
            })
        return {"query": q, "model": model,
                "threshold": config.W2V_THRESHOLD if model == "w2v" else None,
                "total": len(ranked), "page": page, "per_page": per_page, "pages": pages,
                "results": results, "message": message,
                "took_ms": round((time.perf_counter() - t0) * 1000, 1)}

    def compare(self, query: str, lang: str = "auto", k: int = 10) -> dict:
        q = self.analyze_query(query, lang, "tfidf")
        out = {}
        for m in MODELS:
            ranked = self._rank(m, q["terms"])[:k] if q["terms"] else []
            out[m] = [{"rank": i + 1, "id": self.docs[d].id, "title": self.docs[d].title,
                       "university": self.docs[d].university, "score": s}
                      for i, (d, s) in enumerate(ranked)]
        return {"query": q, "models": out}

    def document(self, doc_id: str, query: str = "", model: str = "tfidf", lang: str = "auto") -> dict | None:
        d = self.by_id.get(doc_id)
        if d is None:
            return None
        model = model if model in MODELS else "tfidf"
        doc = self.docs[d]
        terms = self.analyze_query(query, lang, model)["terms"] if query.strip() else []
        explanation = None
        if terms:
            if model == "w2v":
                # `_rank`/`w2v.score` appliquent le seuil de pertinence (W2V_THRESHOLD) et
                # renvoient 0.0 pour tout document en dessous : ici, on veut expliquer le
                # score même pour un document hors classement (panneau ouvert depuis
                # "documents similaires", ou changement de modèle après coup), donc on
                # recalcule le cosinus brut directement plutôt que de lire le classement.
                q, _ = self.w2v.text_vector(terms)
                score = float(self.w2v.doc_vectors[d] @ q) if q is not None else 0.0
                below_threshold = score < config.W2V_THRESHOLD
            else:
                score = dict(self._rank(model, terms)).get(d, 0.0)
                below_threshold = False
            explanation = {"model": model, "score": score, "below_threshold": below_threshold,
                           "threshold": config.W2V_THRESHOLD if model == "w2v" else None,
                           "contributions": self._contributions(model, terms, d)}
        return {
            "document": {**doc.to_dict(), "url": _public_url(doc.url),
                         "author_links": [{"id": i, "name": n} for i, n in self.author_index.by_doc[doc_id]],
                         "abstract": highlight(doc.abstract, set(terms))},
            "explanation": explanation,
            "neighbors": {t: [{"word": w, "similarity": round(s, 3)} for w, s in self.w2v.neighbors(t)]
                          for t in dict.fromkeys(terms)},
            "similar": [{"id": self.docs[j].id, "title": self.docs[j].title,
                         "university": self.docs[j].university, "year": self.docs[j].year,
                         "similarity": round(s, 3)} for j, s in self.w2v.similar_documents(d)],
        }

    # -- auteurs
    def search_authors(self, q: str) -> list[dict]:
        return [{**self.author_index.summary(a), "segments": highlight_name(a.name, q)}
                for a in self.author_index.search(q)]

    def author(self, author_id: str) -> dict | None:
        p = self.author_index.profile(author_id)
        if p is None:
            return None
        docs = [self.docs[self.by_id[i]] for i in p.pop("doc_ids")]
        p["documents"] = [{**{k: v for k, v in d.to_dict().items() if k not in ("abstract", "url")},
                           "url": _public_url(d.url),
                           "snippet": make_snippet(d.abstract, set())} for d in docs]
        return p

    # -- laboratoire
    def preprocess(self, text: str, mode: str = "lemma") -> dict:
        return preprocess(text, "stem" if mode == "stem" else "lemma").to_dict()

    def neighbors(self, word: str) -> dict:
        terms = preprocess(word).terms
        term = terms[0] if terms else word.lower().strip()
        return {"word": word, "term": term, "in_vocabulary": self.w2v.contains(term),
                "neighbors": [{"word": w, "similarity": round(s, 3)} for w, s in self.w2v.neighbors(term, k=10)]}

    # -- corpus
    def _universities(self) -> Counter:
        c = Counter()
        for d in self.docs:
            for u in (d.university or "").split(";"):
                if u.strip():
                    c[u.strip()] += 1
        return c

    def stats(self) -> dict:
        years = [d.year for d in self.docs if d.year]
        return {"documents": len(self.docs), "universities": len(self._universities()),
                "vocabulary": len(self.index.postings), "w2v_vocabulary": len(self.w2v.kv.key_to_index),
                "year_min": min(years, default=None), "year_max": max(years, default=None)}

    def corpus(self) -> dict:
        years = Counter(d.year for d in self.docs if d.year)
        return {"documents": [{**{k: v for k, v in d.to_dict().items() if k != "abstract"},
                               "url": _public_url(d.url)} for d in self.docs],
                "universities": [{"name": n, "count": c} for n, c in self._universities().most_common()],
                "years": [{"year": y, "count": years[y]} for y in sorted(years)],
                "vocabulary_size": len(self.index.postings)}

    def _compute_map(self) -> list[dict]:
        X = self.w2v.doc_vectors
        if len(X) < 2:
            coords = np.zeros((len(X), 2))
        else:
            Xc = X - X.mean(axis=0)
            _, _, vt = np.linalg.svd(Xc, full_matrices=False)   # ACP
            coords = Xc @ vt[:2].T
            span = np.ptp(coords, axis=0)
            span[span == 0] = 1
            coords = (coords - coords.min(axis=0)) / span
        return [{"id": d.id, "title": d.title, "university": (d.university or "").split(";")[0].strip(),
                 "year": d.year, "x": round(float(x), 4), "y": round(float(y), 4)}
                for d, (x, y) in zip(self.docs, coords)]

    def doc_map(self) -> dict:
        return {"points": self._map}
