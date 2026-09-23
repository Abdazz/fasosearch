"""Langue de la requête : détection FR/EN et traduction FR→EN hors ligne.

Traduction neuronale : modèle Argos fr→en exécuté directement avec ctranslate2 +
sentencepiece (sans la librairie Argos, trop lourde). Repli : glossaire du domaine.
"""
import re
import unicodedata
from dataclasses import dataclass

from . import config
from .glossary import EN_FIXES, FR_EN, FR_FUNCTION_WORDS

FR_MARKERS = {"le", "la", "les", "des", "du", "de", "et", "pour", "dans", "une", "un", "sur", "par",
              "avec", "aux", "au", "est", "sont", "d", "l", "qu", "ou", "comment", "quels", "quelles"}
EN_MARKERS = {"the", "of", "and", "for", "in", "with", "on", "to", "an", "by", "is", "are", "how", "what"}
FR_ACCENTS = set("éèêëàâùûüôîïç")
WORD_RE = re.compile(r"[a-zà-ÿœæ]+(?:-[a-zà-ÿ]+)*")


def _words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower().replace("’", "'").replace("'", " "))


def detect_language(text: str) -> str:
    words = _words(text)
    if not words:
        return "en"
    fr = sum(w in FR_MARKERS for w in words) + 2 * any(c in FR_ACCENTS for c in text.lower())
    fr += sum(w in FR_EN and FR_EN[w] != w for w in words)          # mots français connus du glossaire
    en = sum(w in EN_MARKERS for w in words)
    if fr != en:
        return "fr" if fr > en else "en"
    if len(words) >= 3:
        try:
            from langdetect import DetectorFactory, detect
            DetectorFactory.seed = 0
            return "fr" if detect(text) == "fr" else "en"
        except Exception:
            pass
    return "en"


def _apply_fixes(text: str) -> str:
    out = text
    for wrong, right in EN_FIXES.items():
        out = re.sub(rf"\b{re.escape(wrong)}\b", right, out, flags=re.I)
    return out


def glossary_translate(text: str) -> str:
    s = " " + " ".join(_words(text)) + " "
    s_apostrophe = " " + text.lower().replace("’", "'") + " "
    # expressions d'abord (les plus longues), sur le texte avec apostrophes puis sans
    for fr in sorted((k for k in FR_EN if " " in k or "'" in k), key=len, reverse=True):
        if f" {fr} " in s_apostrophe or f" {fr.replace(chr(39), ' ')} " in s:
            s = s.replace(f" {fr.replace(chr(39), ' ')} ", f" {FR_EN[fr]} ")
    out = []
    for w in s.split():
        if w in FR_FUNCTION_WORDS:
            continue
        out.append(FR_EN.get(w, w))
    return " ".join(out)


class Translator:
    def __init__(self):
        self.available = False
        try:
            import ctranslate2
            import sentencepiece as spm
            d = config.LANG_MODEL_DIR
            self._sp = spm.SentencePieceProcessor(model_file=str(d / "sentencepiece.model"))
            self._tr = ctranslate2.Translator(str(d / "model"), device="cpu")
            self.available = True
        except Exception:
            self.available = False

    def translate(self, text: str) -> tuple[str, str]:
        if self.available:
            try:
                pieces = self._sp.encode(text, out_type=str)
                hyp = self._tr.translate_batch([pieces], beam_size=4)[0].hypotheses[0]
                out = "".join(hyp).replace("▁", " ").strip()
                out = re.sub(r"\s+", " ", out)
                if out:
                    return _apply_fixes(out), "neural"
            except Exception:
                pass
        return glossary_translate(text), "glossary"


@dataclass
class LanguageInfo:
    original: str
    language: str
    forced: bool
    translated: str | None
    method: str | None
    english: str


def analyze_language(text: str, lang: str, translator: Translator) -> LanguageInfo:
    forced = lang in ("fr", "en")
    language = lang if forced else detect_language(text)
    if language == "fr":
        translated, method = translator.translate(text)
        return LanguageInfo(text, "fr", forced, translated, method, translated)
    return LanguageInfo(text, "en", forced, None, None, text)
