import pytest

from backend.app import config
from backend.app.authors import (AuthorIndex, clean_name, display_authors, highlight_name, name_tokens,
                                 parse_aliases, same_person, slugify)
from backend.app.corpus import Document, load_corpus


def doc(i, authors, year=2020, uni="Université Nazi Boni", title=None):
    return Document(f"Document_{i:02d}", title or f"Titre {i}", "Résumé. Deuxième phrase.", authors, year, uni)


# ---------------------------------------------------------------- nettoyage
def test_clean_name_reattaches_detached_accents():
    assert clean_name("Didier Bassol ́e") == "Didier Bassolé"
    assert clean_name("Tounwendyam Fr ́ed ́eric") == "Tounwendyam Frédéric"
    assert clean_name("Oumarou Si ́e") == "Oumarou Sié"


def test_clean_name_drops_orphan_mark_lamdi_and_spaces():
    assert clean_name("Franklin Tchakount ́") == "Franklin Tchakount"
    assert clean_name("  Souleymane   Kone Lamdi ") == "Souleymane Kone"
    assert clean_name("José Arthur Ouedraogo LAMDI") == "José Arthur Ouedraogo"
    assert clean_name("   ") == ""


def test_display_authors_cleans_each_part_and_drops_empty():
    assert display_authors("Didier Bassol ́e; ; Oumarou Si ́e") == "Didier Bassolé; Oumarou Sié"
    assert display_authors("") == ""
    assert display_authors("José Arthur Ouedraogo LAMDI") == "José Arthur Ouedraogo"


def test_name_tokens_and_slugify_are_ascii():
    assert name_tokens("Wend-Benedo Siméon ZONGO") == ["wend", "benedo", "simeon", "zongo"]
    assert slugify("Tounwendyam Frédéric Ouédraogo") == "tounwendyam-frederic-ouedraogo"
    assert slugify("") == "auteur"


# ---------------------------------------------------------------- règle de fusion
@pytest.mark.parametrize("a,b", [
    ("Frédéric Ouédraogo", "Tounwendyam Frédéric Ouédraogo"),
    ("Frédéric T. Ouédraogo", "Tounwendyam Frédéric Ouédraogo"),
    ("Ouédraogo Tounwendyam Frédéric", "Tounwendyam Frédéric Ouédraogo"),
    ("Frédéric Ouédraogo", "Frédéric T. Ouédraogo"),
    ("Abdoulaye Sere", "Abdoulaye Séré"),
])
def test_same_person_positive(a, b):
    assert same_person(a, b) and same_person(b, a)


@pytest.mark.parametrize("a,b", [
    ("José Arthur Ouedraogo", "Tounwendyam Frédéric Ouédraogo"),
    ("Ouédraogo", "Frédéric Ouédraogo"),          # un seul mot complet
    ("A. B", "A. B. C"),                           # uniquement des initiales
    ("Didier Bassol", "Didier Bassolé"),           # nom tronqué : réservé au fichier d'alias
])
def test_same_person_negative(a, b):
    assert not same_person(a, b)


# ---------------------------------------------------------------- index (données synthétiques)
def test_index_groups_variants_and_picks_most_frequent_name():
    docs = [doc(1, "Frédéric Ouédraogo; Oumarou Sié"), doc(2, "Tounwendyam Frédéric Ouédraogo"),
            doc(3, "Tounwendyam Frédéric Ouédraogo; José Arthur Ouedraogo")]
    idx = AuthorIndex(docs)
    fo = idx.by_id["tounwendyam-frederic-ouedraogo"]
    assert fo.name == "Tounwendyam Frédéric Ouédraogo"
    assert fo.variants == ["Frédéric Ouédraogo"]
    assert fo.doc_ids == ["Document_01", "Document_02", "Document_03"]
    assert idx.by_doc["Document_03"] == [("tounwendyam-frederic-ouedraogo", "Tounwendyam Frédéric Ouédraogo"),
                                         ("jose-arthur-ouedraogo", "José Arthur Ouedraogo")]


def test_display_name_avoids_all_caps_word_over_frequency_tie():
    # "Moise OUEDRAOGO" et "Moïse Ouedraogo" apparaissent chacun une fois (même fréquence) :
    # celle sans mot tout en majuscules est préférée, puis, à égalité, celle avec accents.
    idx = AuthorIndex([doc(1, "Moise OUEDRAOGO"), doc(2, "Moïse Ouedraogo")])
    a = idx.by_id["moise-ouedraogo"]
    assert a.name == "Moïse Ouedraogo" and a.variants == ["Moise OUEDRAOGO"]


def test_same_author_twice_in_one_doc_counts_once():
    idx = AuthorIndex([doc(1, "Frédéric Ouédraogo; Tounwendyam Frédéric Ouédraogo; Oumarou Sié")])
    fo = idx.by_id["tounwendyam-frederic-ouedraogo"]
    assert fo.doc_ids == ["Document_01"]
    assert [i for i, _ in idx.by_doc["Document_01"]] == ["tounwendyam-frederic-ouedraogo", "oumarou-sie"]


def test_slug_collisions_get_suffix():
    idx = AuthorIndex([doc(1, "Ali Sawadogo; Alí Sawadogo Ouattara"), doc(2, "Ali Sawadogo Ouattara")])
    # "Ali Sawadogo" ⊆ "Alí Sawadogo Ouattara" : fusion, un seul auteur, pas de collision
    assert len(idx.authors) == 1
    idx2 = AuthorIndex([doc(1, "Kà Bé"), doc(2, "Ka Be")])
    # "ka" et "be" sont deux mots complets identiques après normalisation : fusion
    assert len(idx2.authors) == 1
    idx3 = AuthorIndex([doc(1, "Zongo"), doc(2, "Zóngo")])
    # un seul mot complet : pas de fusion automatique, même identifiant de base
    assert sorted(a.id for a in idx3.authors) == ["zongo", "zongo-2"]


def test_search_prefix_exact_first_then_count():
    docs = [doc(1, "Oumarou Sié"), doc(2, "Oumarou Sié"), doc(3, "Oumarou Sanou"), doc(4, "Sié Oumar")]
    idx = AuthorIndex(docs)
    assert [a.name for a in idx.search("oumar")] == ["Oumarou Sié", "Oumarou Sanou", "Sié Oumar"]
    assert [a.name for a in idx.search("sie oumar")][0] == "Sié Oumar"      # correspondance exacte d'abord
    assert idx.search("x") == [] and idx.search(" - ") == [] and idx.search("") == []
    assert idx.search("zzz") == []


def test_search_ignores_accents_and_case():
    idx = AuthorIndex([doc(1, "Tounwendyam Frédéric Ouédraogo")])
    for q in ("ouedraogo", "OUÉDRAOGO", "oued", "frederic ouedraogo", "Ouédraogo T"):
        assert [a.id for a in idx.search(q)] == ["tounwendyam-frederic-ouedraogo"], q


def test_highlight_name_marks_matching_words():
    segs = highlight_name("Tounwendyam Frédéric Ouédraogo", "oued fred")
    assert [s["text"] for s in segs if s["hit"]] == ["Frédéric", "Ouédraogo"]
    assert "".join(s["text"] for s in segs) == "Tounwendyam Frédéric Ouédraogo"
    assert highlight_name("Oumarou Sié", "") == [{"text": "Oumarou Sié", "hit": False}]


def test_profile_sorted_with_coauthors_years_universities():
    docs = [doc(1, "Oumarou Sié; Yaya Traoré", 2019, "Université Norbert Zongo", "B"),
            doc(2, "Oumarou Sié; Yaya Traoré; Didier Bassolé", 2023, "Université Joseph Ki-Zerbo; Université Norbert Zongo", "A"),
            doc(3, "Oumarou Sié", None, "", "C"),
            doc(4, "Yaya Traoré", 2024)]
    idx = AuthorIndex(docs)
    p = idx.profile("oumarou-sie")
    assert p["count"] == 3 and p["years"] == [2019, 2023]
    assert p["doc_ids"] == ["Document_02", "Document_01", "Document_03"]
    assert p["universities"] == ["Université Norbert Zongo", "Université Joseph Ki-Zerbo"]
    assert p["coauthors"] == [{"id": "yaya-traore", "name": "Yaya Traoré", "count": 2},
                              {"id": "didier-bassole", "name": "Didier Bassolé", "count": 1}]
    assert p["variants"] == []
    assert idx.profile("inconnu") is None
    assert idx.summary(idx.by_id["oumarou-sie"]) == {
        "id": "oumarou-sie", "name": "Oumarou Sié", "count": 3,
        "universities": ["Université Norbert Zongo", "Université Joseph Ki-Zerbo"], "years": [2019, 2023]}


def test_years_none_when_unknown():
    idx = AuthorIndex([doc(1, "Oumarou Sié", None)])
    assert idx.profile("oumarou-sie")["years"] is None


# ---------------------------------------------------------------- fichier d'alias
def test_alias_fusion_and_separation(tmp_path):
    docs = [doc(1, "Didier Bassol"), doc(2, "Didier Bassolé"),
            doc(3, "Frédéric Ouédraogo"), doc(4, "Tounwendyam Frédéric Ouédraogo"), doc(5, "Frédéric T. Ouédraogo")]
    f = tmp_path / "aliases.txt"
    f.write_text("# commentaire\n\nfusion: Didier Bassol = Didier Bassole\n"
                 "separer: Frédéric Ouédraogo | Tounwendyam Frédéric Ouédraogo\n", encoding="utf-8")
    idx = AuthorIndex(docs, f)
    assert idx.by_id["didier-bassole"].doc_ids == ["Document_01", "Document_02"]
    assert idx.by_id["tounwendyam-frederic-ouedraogo"].variants == []
    # "Frédéric T. Ouédraogo" partage autant de mots avec les deux : rejoint la première écriture citée ;
    # à fréquence égale, le nom affiché est l'écriture la plus longue
    assert idx.by_id["frederic-t-ouedraogo"].variants == ["Frédéric Ouédraogo"]


def test_alias_errors_name_the_line(tmp_path):
    f = tmp_path / "aliases.txt"
    f.write_text("fusion: A = B\nnimporte quoi\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ligne 2"):
        parse_aliases(f)
    f.write_text("fusion: Personne Inconnue = Oumarou Sié\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ligne 1.*Personne Inconnue"):
        AuthorIndex([doc(1, "Oumarou Sié")], f)


def test_missing_alias_file_is_ignored(tmp_path):
    assert len(AuthorIndex([doc(1, "Oumarou Sié")], tmp_path / "absent.txt").authors) == 1


# ---------------------------------------------------------------- base réelle
EXPECTED_GROUPS = [
    {"Abdou Romaric Tapsoba", "Tapsoba Abdou Romaric"},
    {"Abdoulaye Sere", "Abdoulaye Séré", "Séré Abdoulaye"},
    {"Aminata Sabané", "Sabané Aminata"},
    {"Bassole Didier", "Didier Bassol", "Didier Bassolé"},
    {"Boureima Zerbo", "Zerbo Boureima"},
    {"Doda Afoussatou Rollande", "Doda Afoussatou Rollande Sanou"},
    {"Ferdinand Tonguim Guinko", "Tonguim Ferdinand"},
    {"Frédéric Ouédraogo", "Frédéric T. Ouédraogo", "Ouedraogo Tounwendyam Frederic", "Ouédraogo Tounwendyam Frédéric",
     "Tounwendyam F. Ouédraogo", "Tounwendyam Frédéric", "Tounwendyam Frédéric Ouédraogo"},
    {"Gouayon Koala", "Koala Gouayon"},
    {"Hamidou Harouna Omar", "Omar Harouna Hamidou"},
    {"Jean Louis Ebongue Kedieng Fendji", "Jean Louis Kedieng Ebongue Fendji"},
    {"Jose Arthur", "José Arthur Ouedraogo"},
    {"Kabre Laciné", "Lacine KABRE"},
    {"Kouraogo Justin Pegdwindé", "Pegdwindé Justin Kouraogo"},
    {"Lydie Simone Kone/Tapsoba", "Tapsoba Lydie Simone"},
    {"Mesmin Dandjinou", "Toundé Mesmin Dandjinou"},
    {"Moise OUEDRAOGO", "Moïse Ouedraogo"},
    {"Souleymane Kone", "Souleymane Koné"},
    {"Tegawende Bissyande", "Tegawendé Bissyandé", "Tegawendé F. Bissyandé", "Tegawendé François Bissyandé"},
    {"Tiguiane Yélémou", "Yélémou Tiguiane"},
    {"Wend-Benedo Simeon Zongo", "Zongo Wend-Benedo Simeon"},
]


@pytest.fixture(scope="module")
def real_docs():
    return load_corpus(config.CORPUS_EXCEL)


@pytest.fixture(scope="module")
def real(real_docs):
    return AuthorIndex(real_docs, config.AUTHOR_ALIASES)


def test_real_counts(real_docs, real):
    # "Franklin Tchakount" (nom tronqué) et "Franklin Tchakounté" fusionnent maintenant
    # automatiquement (même écriture complète dans les 3 documents), sans alias : un seul
    # groupe séparé de moins que sans cette correction.
    assert len(AuthorIndex(real_docs).authors) == 185
    assert len(real.authors) == 184
    assert sum(len(a.doc_ids) for a in real.authors) == 394 == sum(len(v) for v in real.by_doc.values())


def test_real_expected_groups(real):
    merged = [{a.name, *a.variants} for a in real.authors if a.variants]
    assert sorted(map(sorted, merged)) == sorted(map(sorted, EXPECTED_GROUPS))


def test_real_key_authors(real):
    fo = real.by_id["tounwendyam-frederic-ouedraogo"]
    assert fo.name == "Tounwendyam Frédéric Ouédraogo" and len(fo.doc_ids) == 28
    assert len(real.by_id["oumarou-sie"].doc_ids) == 17
    assert "José Arthur Ouedraogo" not in fo.variants
    assert real.by_id["jose-arthur-ouedraogo"].name == "José Arthur Ouedraogo"
    names = {a.name for a in real.authors} | {v for a in real.authors for v in a.variants}
    assert not any("́" in n or n.lower().endswith("lamdi") for n in names)


def test_real_ids_unique_ascii(real):
    import re
    ids = [a.id for a in real.authors]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z]+(-[a-z0-9]+)*", i) for i in ids)


def test_real_moise_ouedraogo_display(real):
    a = real.by_id["moise-ouedraogo"]
    assert a.name == "Moïse Ouedraogo" and a.variants == ["Moise OUEDRAOGO"]


def test_real_document_61_authors_display(real_docs):
    d61 = next(d for d in real_docs if d.id == "Document_61")
    assert display_authors(d61.authors) == "Gouayon Koala; Didier Bassolé; Telesphore Tiendrebeogo; Oumarou Sié"


def test_real_search_ouedraogo(real):
    ids = [a.id for a in real.search("ouedraogo")]
    assert ids[0] == "tounwendyam-frederic-ouedraogo" and "jose-arthur-ouedraogo" in ids
