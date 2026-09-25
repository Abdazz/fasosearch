import pytest

from backend.app.language import (
    Translator,
    _apply_fixes,
    analyze_language,
    detect_language,
    expand_acronyms,
    glossary_translate,
)


@pytest.mark.parametrize("text,expected", [
    ("détection d'intrusion", "fr"),
    ("apprentissage automatique pour la santé", "fr"),
    ("l'apprentissage d'une ontologie", "fr"),
    ("réseaux", "fr"),
    ("intrusion detection", "en"),
    ("machine learning for health", "en"),
    ("data", "en"),
    ("internet", "en"),
    ("", "en"),
    ("ia", "fr"),
    ("IA", "fr"),
    ("AI for health", "en"),
])
def test_detect_language(text, expected):
    assert detect_language(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("via media digital signal", "via media digital signal"),
    ("l'ia", "l'AI"),
    ("l’IA", "l’AI"),
    ("d'IA", "d'AI"),
    ("ia", "AI"),
    ("Ia", "AI"),
    ("IA", "AI"),
    ("détection par ia", "détection par AI"),
])
def test_expand_acronyms(text, expected):
    assert expand_acronyms(text) == expected


def test_glossary_translation_handles_elision_and_phrases():
    out = glossary_translate("détection d'intrusion dans les réseaux")
    assert "intrusion" in out and "detection" in out and "network" in out
    assert " d " not in f" {out} " and " l " not in f" {out} "
    assert "machine learning" in glossary_translate("l'apprentissage automatique")


def test_glossary_translation_ontology_no_stray_tokens():
    out = glossary_translate("l'apprentissage d'une ontologie")
    assert "ontology" in out
    tokens = out.split()
    assert "l" not in tokens and "d" not in tokens


def test_apply_fixes_does_not_duplicate_words_already_correct():
    out = _apply_fixes("the search for information retrieval system")
    assert out.count("retrieval") == 1


def test_apply_fixes_still_corrects_known_mistranslation():
    assert _apply_fixes("automatic learning for health") == "machine learning for health"


def test_apply_fixes_is_case_insensitive():
    assert _apply_fixes("Detection of intrusion") == "intrusion detection"


def test_translator_neural_or_fallback_always_returns_english():
    tr = Translator()
    text, method = tr.translate("détection d'intrusion")
    assert method in {"neural", "glossary"}
    assert "intrusion" in text.lower() and "detection" in text.lower()
    assert "▁" not in text


def test_neural_fixes_machine_learning():
    tr = Translator()
    if not tr.available:
        pytest.skip("modèle neuronal non installé")
    text, method = tr.translate("apprentissage automatique pour la santé")
    assert method == "neural" and "machine learning" in text.lower()


def test_analyze_language_auto_and_forced():
    tr = Translator()
    info = analyze_language("détection d'intrusion", "auto", tr)
    assert info.language == "fr" and not info.forced and info.translated and info.english == info.translated
    en = analyze_language("intrusion detection", "auto", tr)
    assert en.language == "en" and en.translated is None and en.english == "intrusion detection"
    forced = analyze_language("data", "fr", tr)
    assert forced.language == "fr" and forced.forced


@pytest.mark.parametrize("text", ["l'ia", "ia", "IA", "L'IA", "détection par IA", "l'ia pour la santé"])
def test_analyze_language_ia_acronym_yields_ai(text):
    tr = Translator()
    info = analyze_language(text, "auto", tr)
    assert info.language == "fr"
    assert "ai" in info.english.lower().split() or "ai" in info.english.lower()
    assert info.original == text


def test_analyze_language_forced_english_expands_ia_acronym():
    tr = Translator()
    info = analyze_language("ia", "en", tr)
    assert info.language == "en" and info.forced
    assert info.english == "AI"


def test_glossary_translate_expands_ia_acronym_when_neural_unavailable():
    # Chemin de repli (pas de modèle neuronal) : glossary_translate doit aussi voir "AI"
    # une fois expand_acronyms appliqué en amont, comme le fait analyze_language (glossary_translate
    # met tout en minuscules, donc le terme final est "ai").
    assert glossary_translate(expand_acronyms("l'ia")) == "ai"


def test_translate_is_cached_and_returns_same_result_twice():
    tr = Translator()
    first = tr.translate("détection d'intrusion")
    second = tr.translate("détection d'intrusion")
    assert first == second


def test_translate_cache_actually_hits_on_repeat():
    tr = Translator()
    tr.translate("l'apprentissage automatique")
    info_before = tr._translate_cached.cache_info()
    tr.translate("l'apprentissage automatique")
    info_after = tr._translate_cached.cache_info()
    assert info_after.hits == info_before.hits + 1


def test_warm_up_never_raises():
    tr = Translator()
    tr.warm_up()  # ne doit jamais lever, même si le modèle neuronal est absent
    tr.warm_up()
