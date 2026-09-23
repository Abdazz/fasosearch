from scripts.augment_data import (bf_institutions, clean, next_ids, norm_title,
                                  rebuild_abstract, select_diverse)


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
