import pytest

from backend.app.language import Translator, analyze_language, detect_language, glossary_translate


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
])
def test_detect_language(text, expected):
    assert detect_language(text) == expected


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
