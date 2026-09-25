import re

import numpy as np
import pytest

from backend.app import config
from backend.app.corpus import Document
from backend.app.engine import SearchEngine, highlight, make_snippet, paginate
from backend.app.preprocess import analyze
from backend.app.word2vec import train_word2vec

DOCS = [
    Document("Document_01", "Network intrusion detection", "Intrusion detection systems detect attacks on networks.", "A. B", 2023, "Université Norbert Zongo", "https://doi.org/x"),
    Document("Document_02", "Cattle breed recognition", "Machine learning classifies cattle breeds from morphology.", "C. D", 2022, "Université Nazi Boni"),
    Document("Document_03", "Malware traffic analysis", "Encrypted traffic reveals malware attacks and anomalies.", "E. F", 2024, "Université Joseph Ki-Zerbo"),
]


@pytest.fixture(scope="module")
def engine():
    terms = [analyze(d.text) for d in DOCS]
    rng = np.random.default_rng(1)
    sec = ["network", "intrusion", "attack", "detection", "malware", "traffic", "anomaly", "encrypted"]
    farm = ["cattle", "breed", "morphology", "classify", "livestock"]
    sents = terms * 50 + [[str(w) for w in rng.choice(sec, 6)] for _ in range(300)] + [[str(w) for w in rng.choice(farm, 6)] for _ in range(300)]
    kv = train_word2vec(sents, {**config.W2V_PARAMS, "vector_size": 20, "epochs": 15})
    return SearchEngine(DOCS, terms, kv)


def test_paginate_clamps_page_and_validates_per_page():
    assert paginate(23, 1, 10) == (1, 10, 0, 3)
    assert paginate(23, 99, 10) == (3, 10, 20, 3)
    assert paginate(23, 1, 7) == (1, 10, 0, 3)
    assert paginate(0, 5, 20) == (1, 20, 0, 1)


def test_highlight_marks_lemma_matches():
    segs = highlight("Networks were attacked.", {"network", "attack"})
    assert [s["text"] for s in segs if s["hit"]] == ["Networks", "attacked"]
    assert "".join(s["text"] for s in segs) == "Networks were attacked."


def test_snippet_starts_at_first_matching_sentence():
    text = "First sentence here. Second talks about cattle. Third."
    segs = make_snippet(text, {"cattle"}, max_chars=200)
    joined = "".join(s["text"] for s in segs)
    assert joined.startswith("… Second")


def test_search_tfidf_with_pagination_and_details(engine):
    r = engine.search("intrusion detection", model="tfidf", per_page=10)
    assert r["results"][0]["id"] == "Document_01"
    assert r["total"] >= 1 and r["page"] == 1 and r["pages"] >= 1
    first = r["results"][0]
    assert first["rank"] == 1 and 0 < first["score"] <= 1 and first["score_ratio"] == 1.0
    assert first["university"] == "Université Norbert Zongo"
    assert any(s["hit"] for s in first["snippet"])
    assert {c["term"] for c in first["contributions"]} <= {"intrusion", "detection"}
    assert r["query"]["terms"] == ["intrusion", "detection"] and r["message"] is None


def test_search_french_query_is_translated(engine):
    r = engine.search("détection d'intrusion", model="tfidf")
    assert r["query"]["language"] == "fr" and r["query"]["translated"]
    assert r["results"] and r["results"][0]["id"] == "Document_01"


def test_search_messages(engine):
    assert engine.search("the of and", model="tfidf")["message"] == "no_terms"
    assert engine.search("zebra", model="tfidf")["message"] == "no_match"
    assert engine.search("zebra", model="w2v")["message"] == "all_oov"


def test_search_w2v_and_bm25(engine):
    w = engine.search("malware anomaly", model="w2v")
    assert w["threshold"] == config.W2V_THRESHOLD
    assert w["results"] and w["results"][0]["id"] in {"Document_01", "Document_03"}
    b = engine.search("cattle", model="bm25")
    assert b["results"][0]["id"] == "Document_02" and b["results"][0]["score_ratio"] == 1.0


def test_invalid_model_falls_back_to_tfidf(engine):
    assert engine.search("intrusion", model="xxx")["model"] == "tfidf"


def test_compare_returns_three_rankings(engine):
    c = engine.compare("intrusion attack", k=2)
    assert set(c["models"]) == {"tfidf", "w2v", "bm25"}
    assert all(len(v) <= 2 for v in c["models"].values())


def test_document_detail(engine):
    d = engine.document("Document_01", query="intrusion", model="tfidf")
    assert d["document"]["url"] == "https://doi.org/x"
    assert d["explanation"]["score"] > 0
    assert "intrusion" in d["neighbors"]
    assert len(d["similar"]) == 2
    assert engine.document("Document_99") is None


def test_document_url_comes_from_document(engine):
    assert engine.document("Document_01")["document"]["url"] == "https://doi.org/x"
    assert engine.document("Document_02")["document"]["url"] is None


def test_corpus_url_matches_document_rule(engine):
    # corpus() doit appliquer la même règle que document() : URL vide -> None (fix I4).
    urls = {d["id"]: d["url"] for d in engine.corpus()["documents"]}
    assert urls["Document_01"] == "https://doi.org/x"
    assert urls["Document_02"] is None


NON_HTTPS_DOCS = [
    Document("Document_01", "Network intrusion detection",
             "Intrusion detection systems detect attacks on networks.", "A. B", 2023,
             "Université Norbert Zongo", "javascript:alert(1)"),
    Document("Document_02", "Cattle breed recognition",
             "Machine learning classifies cattle breeds from morphology.", "C. D", 2022,
             "Université Nazi Boni", "data:text/html,alert(1)"),
    Document("Document_03", "Malware traffic analysis",
             "Encrypted traffic reveals malware attacks and anomalies.", "E. F", 2024,
             "Université Joseph Ki-Zerbo", "http://article.sapub.org/x"),
]


@pytest.fixture(scope="module")
def unsafe_url_engine():
    terms = [analyze(d.text) for d in NON_HTTPS_DOCS]
    kv = train_word2vec(terms, {**config.W2V_PARAMS, "vector_size": 8, "min_count": 1, "epochs": 5})
    return SearchEngine(NON_HTTPS_DOCS, terms, kv)


def test_document_url_rejects_unsafe_schemes_but_accepts_http(unsafe_url_engine):
    # javascript: et data: ne doivent jamais être servis comme URL "Source" ; http:// (page
    # éditeur sans https, ex. Document_84) est désormais accepté au même titre que https://.
    assert unsafe_url_engine.document("Document_01")["document"]["url"] is None
    assert unsafe_url_engine.document("Document_02")["document"]["url"] is None
    assert unsafe_url_engine.document("Document_03")["document"]["url"] == "http://article.sapub.org/x"


def test_corpus_url_rejects_unsafe_schemes_but_accepts_http(unsafe_url_engine):
    urls = {d["id"]: d["url"] for d in unsafe_url_engine.corpus()["documents"]}
    assert urls["Document_01"] is None
    assert urls["Document_02"] is None
    assert urls["Document_03"] == "http://article.sapub.org/x"


def test_stats_corpus_map(engine):
    s = engine.stats()
    assert s["documents"] == 3 and s["universities"] == 3
    c = engine.corpus()
    assert len(c["documents"]) == 3 and {u["name"] for u in c["universities"]} >= {"Université Nazi Boni"}
    m = engine.doc_map()
    assert len(m["points"]) == 3 and {"x", "y", "id", "university", "title"} <= set(m["points"][0])


def test_check_alignment_raises_on_mismatch():
    from backend.app.engine import _check_alignment

    _check_alignment(["Document_01", "Document_02"], ["Document_01", "Document_02"])  # no raise
    with pytest.raises(RuntimeError):
        _check_alignment(["Document_01", "Document_02"], ["Document_01", "Document_99"])


def test_document_invalid_model_falls_back_to_tfidf(engine):
    d = engine.document("Document_01", query="intrusion", model="xxx")
    assert d["explanation"]["model"] == "tfidf"


def test_snippet_no_trailing_ellipsis_when_last_sentence_included():
    segs = make_snippet("AAA BBB. CCC DDD. ", {"ccc"})
    joined = "".join(s["text"] for s in segs)
    assert joined == "… CCC DDD."


def test_score_matches_top_contribution_exactly(engine):
    # I1 : la bague de score et la puce de contribution affichaient des valeurs
    # différentes ("0.253" vs "0.252") car le score était arrondi côté serveur alors
    # que les contributions restaient brutes. Pour une requête à un seul terme, le
    # score total ET la contribution de ce terme doivent être rigoureusement égaux.
    r = engine.search("intrusion", model="tfidf")
    assert r["results"] and r["results"][0]["score"] == r["results"][0]["contributions"][0]["value"]

    d = engine.document("Document_01", query="intrusion", model="tfidf")
    assert d["explanation"]["score"] == d["explanation"]["contributions"][0]["value"]


def test_document_w2v_explanation_uses_raw_cosine_even_below_threshold(engine):
    # I2 : document() lisait le score dans `_rank()`, qui applique le seuil Word2Vec et
    # renvoie 0.0 pour tout document sous ce seuil -- le panneau affichait donc "0.000"
    # pour un cosinus réel proche de 0.5. Le score expliqué doit être le cosinus brut,
    # identique qu'il soit ou non au-dessus du seuil de classement.
    terms = engine.analyze_query("cattle", model="w2v")["terms"]
    doc_idx = engine.by_id["Document_01"]
    q, _ = engine.w2v.text_vector(terms)
    raw_cosine = float(engine.w2v.doc_vectors[doc_idx] @ q)

    d = engine.document("Document_01", query="cattle", model="w2v")
    assert d["explanation"]["score"] == pytest.approx(raw_cosine)
    assert d["explanation"]["below_threshold"] == (raw_cosine < config.W2V_THRESHOLD)
    assert d["explanation"]["threshold"] == config.W2V_THRESHOLD


def test_document_explanation_below_threshold_is_false_for_non_w2v_models(engine):
    d = engine.document("Document_01", query="intrusion", model="tfidf")
    assert d["explanation"]["below_threshold"] is False
    assert d["explanation"]["threshold"] is None


@pytest.mark.integration
def test_real_engine_semantics():
    from scripts.build_index import is_stale
    if not config.CORPUS_EXCEL.exists() or is_stale():
        pytest.skip("modèles non construits")
    real = SearchEngine.load()
    assert real.search("intrusion detection")["results"]
    assert real.search("détection d'intrusion")["query"]["language"] == "fr"

    # Comparaison de groupes plutôt qu'une seule paire de mots (plus robuste : dans ce corpus
    # burkinabè, "intrusion" désigne aussi l'intrusion saline en hydrologie, ce qui rendait la
    # comparaison ponctuelle intrusion/cattle fragile).
    SEC_WORDS = ["attack", "malware", "intrusion", "security", "encryption", "authentication",
                 "threat", "vulnerability"]
    AGR_WORDS = ["cattle", "crop", "maize", "soil", "farmer", "livestock", "yield", "agriculture"]
    sec = [w for w in SEC_WORDS if real.w2v.contains(w)]
    agr = [w for w in AGR_WORDS if real.w2v.contains(w)]
    if len(sec) < 4 or len(agr) < 4:
        pytest.skip("mots de test insuffisamment présents dans le vocabulaire")

    def mean_pairwise(words):
        pairs = [real.w2v.similarity(a, b) for i, a in enumerate(words) for b in words[i + 1:]]
        return sum(pairs) / len(pairs)

    def mean_cross(words_a, words_b):
        pairs = [real.w2v.similarity(a, b) for a in words_a for b in words_b]
        return sum(pairs) / len(pairs)

    sec_internal = mean_pairwise(sec)
    agr_internal = mean_pairwise(agr)
    cross = mean_cross(sec, agr)
    assert sec_internal > cross
    assert agr_internal > cross


@pytest.mark.integration
def test_real_engine_ia_acronym_queries_return_results():
    # Bug sigles : "l'ia", "ia", "IA" renvoyaient 0 résultat car le sigle français IA
    # (intelligence artificielle) n'était ni détecté comme marqueur FR, ni traduit en "AI"
    # avant la traduction neuronale/glossaire. "l'IA" fonctionnait déjà (8 résultats) : on
    # vérifie que les variantes cassées retrouvent au moins ce même nombre de résultats.
    from scripts.build_index import is_stale
    if not config.CORPUS_EXCEL.exists() or is_stale():
        pytest.skip("modèles non construits")
    real = SearchEngine.load()
    baseline = real.search("l'IA", model="tfidf")
    assert baseline["total"] >= 8
    for q in ["l'ia", "ia", "IA", "L'IA", "détection par IA"]:
        r = real.search(q, model="tfidf")
        assert r["query"]["language"] == "fr"
        assert "ai" in r["query"]["terms"]
    assert real.search("l'ia", model="tfidf")["total"] >= 8


@pytest.mark.integration
def test_real_engine_cs_neighbors_are_specific_and_frequent():
    """Task 17b : le corpus d'entraînement Word2Vec inclut des résumés d'informatique
    (data/w2v_cs.txt) et min_count=5 -- les voisins de mots-clés informatiques doivent
    devenir spécifiques au domaine (et non plus agriculture/hydrologie), et aucun voisin ne
    doit être un mot rare apparaissant moins de 5 fois (conséquence directe de min_count=5)."""
    from scripts.build_index import is_stale
    if not config.CORPUS_EXCEL.exists() or is_stale():
        pytest.skip("modèles non construits")
    real = SearchEngine.load()

    # Ensembles bénis par le contrôleur (task 17b, round 1 de revue) : la liste "security" du
    # brief d'origine, telle quelle (elle passe déjà via "privacy") ; la liste "intrusion"
    # bénie comme vocabulaire IDS standard (signature-based/anomaly-based/idss/nidss/intruder/
    # botnet), sans les extensions ajoutées lors de la première implémentation
    # (host-based/behavior-based/network-based/nids/hids/intruders) qui n'étaient pas
    # autorisées.
    expected = {
        "security": {"attack", "attacks", "privacy", "authentication", "encryption",
                      "threat", "threats", "vulnerability", "cryptographic", "malicious"},
        "intrusion": {"detection", "attack", "attacks", "anomaly", "ids", "malicious",
                      "intrusions", "ddos", "idss", "nidss", "intruder", "botnet",
                      "signature-based", "anomaly-based"},
        "network": {"networks", "wireless", "routing", "protocol", "node", "nodes",
                    "sensor", "topology"},
    }
    # Round 2 (corpus CS doublé) : "security" ne doit plus être polluée par le thème "sécurité
    # alimentaire" burkinabè (constat initial du contrôleur). Vérifié séparément de `expected`
    # ci-dessus car c'est une exigence négative (absence), pas une exigence positive.
    FORBIDDEN_SECURITY_NEIGHBORS = {"food", "livelihood", "insecurity"}

    tested = 0
    for word, expected_terms in expected.items():
        if not real.w2v.contains(word):
            continue
        tested += 1
        neighbors = real.w2v.neighbors(word, k=10)
        neighbor_words = {w for w, _ in neighbors}
        assert neighbor_words & expected_terms, f"voisins de '{word}' : {neighbor_words}"
        for w, _ in neighbors:
            count = real.w2v.kv.get_vecattr(w, "count")
            assert count >= 5, f"voisin '{w}' de '{word}' apparaît {count} fois (< min_count=5)"
        if word == "security":
            polluted = neighbor_words & FORBIDDEN_SECURITY_NEIGHBORS
            assert not polluted, (
                f"voisins de 'security' encore pollués par le thème 'sécurité alimentaire' : "
                f"{polluted} (top 10 complet : {neighbors})")
    if tested == 0:
        pytest.skip("aucun des mots testés n'est dans le vocabulaire")


def test_author_links_in_document(engine):
    d = engine.document("Document_01")["document"]
    assert d["author_links"] == [{"id": "a-b", "name": "A. B"}]


def test_search_authors_returns_summary_and_segments(engine):
    r = engine.search_authors("c d")
    assert [a["id"] for a in r] == ["c-d"]
    assert r[0]["count"] == 1 and r[0]["years"] == [2022, 2022]
    assert r[0]["universities"] == ["Université Nazi Boni"]
    assert "".join(s["text"] for s in r[0]["segments"]) == "C. D"
    assert engine.search_authors("x") == []


def test_author_profile_documents_have_snippet(engine):
    p = engine.author("e-f")
    assert "doc_ids" not in p
    assert [d["id"] for d in p["documents"]] == ["Document_03"]
    doc = p["documents"][0]
    assert "abstract" not in doc and doc["title"] == "Malware traffic analysis"
    assert "url" in doc and doc["url"] is None
    assert "".join(s["text"] for s in doc["snippet"]).startswith("Encrypted traffic")
    assert engine.author("inconnu") is None


# ---------------------------------------------------------------- auteurs : accents détachés
# Écriture brute avec accent détaché de sa lettre (artefact d'extraction PDF) : "Bassol ́e".
ACCENT_DOC = Document("Document_01", "Detached accent title", "Abstract sentence about detection systems.",
                      "Didier Bassol ́e; Oumarou Si ́e", 2023, "Université X")
# Second document sans le terme recherché : évite un idf nul (un seul document contenant
# "detection" donnerait df = N, donc idf = log(N/df) = 0, et aucun résultat en tfidf).
ACCENT_FILLER_DOC = Document("Document_02", "Unrelated title", "Something about cattle breeding methods.",
                             "A. B", 2022, "Université Y")


@pytest.fixture(scope="module")
def accent_engine():
    docs = [ACCENT_DOC, ACCENT_FILLER_DOC]
    terms = [analyze(d.text) for d in docs]
    kv = train_word2vec(terms * 20, {**config.W2V_PARAMS, "vector_size": 10, "epochs": 5, "min_count": 1})
    return SearchEngine(docs, terms, kv)


def test_authors_are_cleaned_for_display_everywhere(accent_engine):
    """Aucune chaîne 'authors' renvoyée à l'API ne garde un accent détaché (marque combinante
    U+0300-U+036F précédée d'une espace)."""
    combining = re.compile(r" [̀-ͯ]")
    expected = "Didier Bassolé; Oumarou Sié"

    r = accent_engine.search("detection")
    assert r["results"] and r["results"][0]["authors"] == expected
    assert not combining.search(r["results"][0]["authors"])

    d = accent_engine.document("Document_01")["document"]
    assert d["authors"] == expected and not combining.search(d["authors"])

    c = accent_engine.corpus()["documents"][0]
    assert c["authors"] == expected and not combining.search(c["authors"])

    author_id = accent_engine.author_index.by_doc["Document_01"][0][0]
    p = accent_engine.author(author_id)
    assert p["documents"][0]["authors"] == expected
    assert not combining.search(p["documents"][0]["authors"])
