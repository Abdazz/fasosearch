"""Augmentation des données — articles d'informatique d'auteurs burkinabè (OpenAlex).

Critères (spec §2.1) : ≥1 auteur affilié au Burkina Faso, domaine Computer Science,
anglais (filtre OpenAlex + langdetect), résumé de 60 à 450 mots, pas de doublon.
Filtre « informatique » supplémentaire : titre + résumé doivent contenir au moins 2
termes distincts du lexique CS_LEXICON (le filtre OpenAlex primary_topic.field.id:17
laisse passer trop d'articles hors informatique — économie, géologie, santé publique...).
Sélection : ~70 articles, au plus PER_SUBFIELD par sous-domaine, les plus récents d'abord.

Cache disque : chaque réponse OpenAlex 200 est écrite dans data/openalex_cache/<sha1>.json ;
_get() lit ce cache avant tout appel réseau (une relance ne recoûte aucun crédit pour les
pages déjà obtenues). Sur un 429, on ne boucle plus : QuotaExceeded(retry_after_seconds)
est levée immédiatement (les autres erreurs réseau gardent 3 nouvelles tentatives) ; main()
l'attrape et s'arrête sans écrire de fichier de sortie partiel.

Produit :
  Devoir/données textuelles - base complète.xlsx   (30 originaux + nouveaux)
  data/w2v_extra.txt        résumés BF non indexés (entraînement Word2Vec uniquement)
  data/doi.json             id -> lien DOI/OpenAlex
  data/affiliations_a_verifier.txt   originaux dont l'affiliation n'a pas été trouvée
  data/openalex_cache/      cache disque des réponses OpenAlex (ignoré par git)

Usage : python scripts/augment_data.py   (nécessite internet)
"""
import difflib
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import openpyxl
import requests
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import config  # noqa: E402
from backend.app.corpus import COLUMNS, load_corpus  # noqa: E402

API = "https://api.openalex.org"
MAILTO = "fasosearch@example.org"
BF_FILTER = "authorships.institutions.country_code:BF,language:en,has_abstract:true"
CS_FILTER = BF_FILTER + ",primary_topic.field.id:17"
SELECT = "id,title,abstract_inverted_index,authorships,publication_year,doi,primary_topic"
TARGET_NEW = 70
PER_SUBFIELD = 15  # OpenAlex n'a que quelques sous-domaines informatiques (décision du contrôleur)

CS_LEXICON = (
    "algorithm", "software", "network", "internet", "computer", "computing", "data", "database",
    "machine learning", "deep learning", "neural", "learning model", "classification", "classifier",
    "clustering", "dataset", "artificial intelligence", "ontology", "semantic", "web", "cloud",
    "security", "cyber", "encryption", "authentication", "protocol", "wireless", "sensor", "iot",
    "routing", "blockchain", "image processing", "computer vision", "segmentation",
    "detection model", "recognition", "natural language", "nlp", "text mining",
    "information system", "information retrieval", "digital", "mobile application",
    "simulation model", "optimization algorithm", "programming", "server", "architecture",
    "framework", "platform", "big data", "analytics", "prediction model", "convolutional",
    "transformer", "embedding", "graph", "e-learning", "e-health", "gis", "remote sensing",
    "satellite image", "drone", "uav",
)


class QuotaExceeded(Exception):
    """Levée quand OpenAlex renvoie 429 : quota de crédits épuisé pour la fenêtre en cours."""

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"quota OpenAlex épuisé, réessayer dans {retry_after_seconds}s")


# ---------------------------------------------------------------- fonctions pures
def rebuild_abstract(inv: dict | None) -> str:
    """OpenAlex stocke les résumés en index inversé {mot: [positions]} : on le reconstruit."""
    if not inv:
        return ""
    pos = sorted((i, w) for w, idxs in inv.items() for i in idxs)
    return " ".join(w for _, w in pos)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _strip_accents(t or "").lower())


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"^\s*(abstract|summary)\s*[:.]?\s*", "", text.strip(), flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def bf_institutions(work: dict) -> list[str]:
    """Institutions burkinabè des auteurs, sans doublon, dans l'ordre d'apparition."""
    seen: list[str] = []
    for a in work.get("authorships") or []:
        for inst in a.get("institutions") or []:
            name = inst.get("display_name")
            if inst.get("country_code") == "BF" and name and name not in seen:
                seen.append(name)
    return seen


def select_diverse(cands: list[dict], n: int, per_subfield: int) -> list[dict]:
    """Les plus récents d'abord, au plus `per_subfield` par sous-domaine, au plus n."""
    chosen, per = [], {}
    for c in sorted(cands, key=lambda c: c.get("year") or 0, reverse=True):
        sf = c.get("subfield") or "?"
        if per.get(sf, 0) >= per_subfield:
            continue
        chosen.append(c)
        per[sf] = per.get(sf, 0) + 1
        if len(chosen) == n:
            break
    return chosen


def next_ids(start: int, count: int) -> list[str]:
    return ["Document_%02d" % i for i in range(start, start + count)]


def is_computer_science(text: str) -> bool:
    """Vrai si `text` (titre + résumé) contient au moins 2 termes distincts de CS_LEXICON."""
    low = (text or "").lower()
    found = {term for term in CS_LEXICON if re.search(r"\b" + re.escape(term) + r"\b", low)}
    return len(found) >= 2


# ---------------------------------------------------------------- accès OpenAlex + cache disque
def _cache_key(path: str, params: dict) -> str:
    canonical = json.dumps({"path": path, **params}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def _cache_file(path: str, params: dict) -> Path:
    return config.OPENALEX_CACHE_DIR / f"{_cache_key(path, params)}.json"


def _get(path: str, params: dict) -> dict:
    params = {**params, "mailto": MAILTO}
    config.OPENALEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_file(path, params)
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    for attempt in range(4):
        try:
            r = requests.get(f"{API}/{path}", params=params, timeout=40)
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", "60"))
                raise QuotaExceeded(retry_after)
            r.raise_for_status()
            data = r.json()
            cache_file.write_text(json.dumps(data), encoding="utf-8")
            return data
        except requests.RequestException as e:
            print(f"  nouvel essai {attempt + 1} : {e}")
            time.sleep(2 + 2 * attempt)
    return {}


def fetch_all(filter_str: str, limit: int = 5000) -> list[dict]:
    out, cursor = [], "*"
    while cursor and len(out) < limit:
        data = _get("works", {"filter": filter_str, "per-page": 200, "cursor": cursor, "select": SELECT})
        out.extend(data.get("results", []))
        cursor = (data.get("meta") or {}).get("next_cursor")
        time.sleep(0.2)
    return out


def _is_english(text: str) -> bool:
    from langdetect import DetectorFactory, detect
    DetectorFactory.seed = 0
    try:
        return detect(text) == "en"
    except Exception:
        return False


def to_candidate(w: dict) -> dict | None:
    title = clean(w.get("title"))
    abstract = clean(rebuild_abstract(w.get("abstract_inverted_index")))
    n_words = len(abstract.split())
    unis = bf_institutions(w)
    if not title or not unis or not (60 <= n_words <= 450):
        return None
    if not is_computer_science(f"{title} {abstract}"):
        return None
    if not (_is_english(title) and _is_english(abstract)):
        return None
    authors = "; ".join(a["author"]["display_name"] for a in (w.get("authorships") or [])[:8]
                        if a.get("author") and a["author"].get("display_name"))
    pt = w.get("primary_topic") or {}
    return {
        "title": title, "abstract": abstract, "authors": authors or "Unknown",
        "year": w.get("publication_year"), "university": "; ".join(unis),
        "subfield": (pt.get("subfield") or {}).get("display_name"),
        "url": w.get("doi") or w.get("id"),
    }


def find_original_affiliation(title: str) -> tuple[str, str | None]:
    """Retrouve un article d'origine par son titre ; renvoie (universités BF, url)."""
    data = _get("works", {"search": title, "per-page": 5, "select": SELECT})
    for w in data.get("results", []):
        ratio = difflib.SequenceMatcher(None, norm_title(title), norm_title(w.get("title") or "")).ratio()
        if ratio >= 0.9:
            return "; ".join(bf_institutions(w)), (w.get("doi") or w.get("id"))
    return "", None


# ---------------------------------------------------------------- écriture
def write_excel(rows: list[list], path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Base complète"
    ws.append(COLUMNS)
    for r in rows:
        ws.append(r)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="231710")
    for letter, width in zip("ABCDEF", (15, 60, 100, 45, 8, 40)):
        ws.column_dimensions[letter].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    wb.save(path)


def main() -> None:
    """Attrape QuotaExceeded : message clair, aucun fichier de sortie partiel écrit."""
    try:
        _run()
    except QuotaExceeded as e:
        minutes = -(-e.retry_after_seconds // 60)  # arrondi au supérieur
        print(f"Quota OpenAlex épuisé : réessayez dans {minutes} minutes.")
        sys.exit(1)


def _run() -> None:
    originals = load_corpus(config.ORIGINAL_EXCEL)
    seen = {norm_title(d.title) for d in originals}
    rows, doi, todo = [], {}, []

    print("1/3 Affiliations des 30 articles d'origine...")
    for d in originals:
        uni, url = find_original_affiliation(d.title)
        if not uni:
            todo.append(f"{d.id}\t{d.title}\t{d.authors}")
        if url:
            doi[d.id] = url
        rows.append([d.id, d.title, d.abstract, d.authors, d.year, uni])
        time.sleep(0.15)

    print("2/3 Candidats : informatique, auteurs affiliés au Burkina Faso...")
    cands = []
    for w in fetch_all(CS_FILTER):
        c = to_candidate(w)
        if c and norm_title(c["title"]) not in seen:
            seen.add(norm_title(c["title"]))
            cands.append(c)
    chosen = select_diverse(cands, TARGET_NEW, PER_SUBFIELD)
    for new_id, c in zip(next_ids(len(originals) + 1, len(chosen)), chosen):
        rows.append([new_id, c["title"], c["abstract"], c["authors"], c["year"], c["university"]])
        doi[new_id] = c["url"]
    print(f"   {len(cands)} candidats valides -> {len(chosen)} retenus")

    print("3/3 Corpus d'entraînement Word2Vec (résumés BF non indexés)...")
    extra = []
    for w in fetch_all(BF_FILTER, limit=6000):
        t, a = clean(w.get("title")), clean(rebuild_abstract(w.get("abstract_inverted_index")))
        if t and len(a.split()) >= 40 and norm_title(t) not in seen and _is_english(a):
            extra.append(f"{t}. {a}")

    config.DATA_DIR.mkdir(exist_ok=True)
    write_excel(rows, config.CORPUS_EXCEL)
    config.W2V_EXTRA.write_text("\n".join(extra), encoding="utf-8")
    config.DOI_JSON.write_text(json.dumps(doi, indent=1), encoding="utf-8")
    config.AFFILIATIONS_TODO.write_text(
        "ID\tTitre\tAuteurs  (affiliation à compléter à la main dans la colonne University)\n"
        + "\n".join(todo), encoding="utf-8")
    print(f"\nBase complète : {len(rows)} articles -> {config.CORPUS_EXCEL.name}")
    print(f"Résumés d'entraînement Word2Vec : {len(extra)}")
    print(f"Affiliations à vérifier : {len(todo)} (voir {config.AFFILIATIONS_TODO.name})")


if __name__ == "__main__":
    main()
