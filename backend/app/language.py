"""Langue de la requête : détection FR/EN et traduction FR→EN hors ligne.

Traduction neuronale : modèle Argos fr→en exécuté directement avec ctranslate2 +
sentencepiece (sans la librairie Argos, trop lourde). Repli : glossaire du domaine.
"""
import functools
import re
from dataclasses import dataclass

from . import config
from .glossary import EN_FIXES, FR_ACRONYMS, FR_EN, FR_FUNCTION_WORDS

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
    fr += sum(w in FR_ACRONYMS for w in words)                      # sigle français (ex. "ia" seul)
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


_ACRONYM_RE = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in sorted(FR_ACRONYMS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def expand_acronyms(text: str) -> str:
    """Remplace les sigles français (ex. "ia") par leur forme anglaise ("AI") avant traduction.

    Ne touche qu'aux mots entiers (donc jamais "via", "media", "tal" dans "digital" ou "sig"
    dans "signal") ; une éventuelle apostrophe d'élision ("l'ia", "l’IA", "d'IA") est déjà
    hors des limites de mot, donc conservée telle quelle ("l'AI").
    """
    return _ACRONYM_RE.sub(lambda m: FR_ACRONYMS[m.group(0).lower()], text)


_EN_FIXES_LOWER = {wrong.lower(): right for wrong, right in EN_FIXES.items()}
_FIX_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_EN_FIXES_LOWER, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _apply_fixes(text: str) -> str:
    def _replace(m: re.Match) -> str:
        right = _EN_FIXES_LOWER[m.group(0).lower()]
        last_word = right.rsplit(" ", 1)[-1]
        after = text[m.end():].lstrip()
        # Ne pas dupliquer un mot déjà correct juste après le match (ex. "search for
        # information" suivi de "retrieval system" -> ne pas produire "... retrieval retrieval ...").
        if re.match(rf"{re.escape(last_word)}\b", after, re.I):
            return m.group(0)
        return right

    return _FIX_RE.sub(_replace, text)


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
            self._tr = ctranslate2.Translator(str(d / "model"), device="cpu", intra_threads=4)
            self.available = True
        except Exception:
            self.available = False
        # Cache par instance (et non partagé par lru_cache posé sur la classe) : évite de
        # garder toutes les instances en vie via la clé de cache et rend cache_info() lisible.
        self._translate_cached = functools.lru_cache(maxsize=1024)(self._translate_uncached)

    def _translate_uncached(self, text: str) -> tuple[str, str]:
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

    def translate(self, text: str) -> tuple[str, str]:
        return self._translate_cached(text)

    def warm_up(self) -> None:
        """Traduit une courte phrase une fois pour préchauffer le modèle (latence de démo).

        Ne lève jamais, même si le modèle neuronal est absent.
        """
        try:
            self.translate("bonjour")
        except Exception:
            pass


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
    expanded = expand_acronyms(text)  # sigles FR (ex. "ia" -> "AI") avant traduction, quelle que
    # soit la langue détectée ou forcée -- l'original (`text`) reste affiché tel quel.
    if language == "fr":
        translated, method = translator.translate(expanded)
        return LanguageInfo(text, "fr", forced, translated, method, translated)
    return LanguageInfo(text, "en", forced, None, None, expanded)
