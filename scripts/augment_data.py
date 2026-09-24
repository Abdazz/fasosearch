"""Augmentation des données — articles d'informatique d'auteurs burkinabè (OpenAlex).

Critères (spec §2.1) : ≥1 auteur affilié au Burkina Faso, domaine Computer Science,
anglais (filtre OpenAlex + langdetect), résumé de 60 à 450 mots, pas de doublon.
Filtre « informatique » (is_computer_science, voir STRONG_LEXICON) : la requête OpenAlex ne
filtre plus par primary_topic.field.id:17 ("Computer Science"), car ce champ ne couvre que
408 des 17 282 travaux BF_FILTER et laisse quand même passer des articles hors informatique
(économie, géologie, santé publique...). On scanne donc tout BF_FILTER et c'est notre propre
filtre lexical qui décide : les termes génériques (WEAK_LEXICON : "data", "model",
"platform"...) ne comptent plus seuls, il faut des termes STRONG distincts.
Exclusion manuelle possible via data/exclusions.txt (titre normalisé ou id OpenAlex, un par
ligne) pour écarter au cas par cas un article encore mal classé malgré le filtre lexical.
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

Consomme (committé, édité à la main) :
  data/exclusions.txt       titres normalisés / ids OpenAlex à écarter des candidats

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
SELECT = "id,title,abstract_inverted_index,authorships,publication_year,doi,primary_topic"
TARGET_NEW = 70
PER_SUBFIELD = 15  # OpenAlex n'a que quelques sous-domaines informatiques (décision du contrôleur)
# On ne restreint plus la requête OpenAlex à primary_topic.field.id:17 ("Computer Science") :
# ce champ ne couvre que 408 des 17 282 travaux BF (constaté empiriquement) et laisse quand
# même passer beaucoup d'articles hors informatique. On scanne donc tout le corpus BF_FILTER
# et c'est is_computer_science (STRONG_LEXICON) qui décide seul de l'appartenance CS.
BF_FETCH_LIMIT = 20000

# Termes non ambigus : leur seule présence est un signal fort d'informatique.
STRONG_LEXICON = (
    "algorithm", "software", "computer", "computing", "machine learning", "deep learning",
    "neural network", "artificial intelligence", "dataset", "classifier", "clustering",
    "database", "ontology", "semantic web", "cloud computing", "cybersecurity",
    "security protocol", "encryption", "authentication", "network protocol", "routing",
    "wireless sensor", "iot", "internet of things", "blockchain", "computer vision",
    "image processing", "natural language processing", "nlp", "text mining",
    "information retrieval", "information system", "big data", "convolutional",
    "transformer", "embedding", "remote sensing image", "uav", "drone", "programming",
    "operating system", "distributed system", "edge computing", "fog computing",
    "internet", "e-learning platform",
)

# Termes génériques : trop ambigus pour compter seuls (ex. "data", "model", "platform" se
# retrouvent dans des articles d'économie, de santé publique, d'agriculture...). Ils ne sont
# pas utilisés par is_computer_science, mais restent documentés/disponibles (CS_LEXICON).
WEAK_LEXICON = (
    "data", "model", "digital", "platform", "framework", "analytics", "graph",
    "simulation model", "prediction model", "web", "mobile application",
    "network", "security", "cyber", "sensor", "wireless", "protocol", "semantic", "cloud",
    "segmentation", "detection model", "recognition", "learning model", "classification",
    "natural language", "satellite image", "gis", "e-health", "e-learning",
    "optimization algorithm", "architecture", "server",
)

CS_LEXICON = STRONG_LEXICON + WEAK_LEXICON  # >= 60 termes (contrat historique, cf. tests)


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


def _strong_terms_in(text: str) -> set[str]:
    low = (text or "").lower()
    return {term for term in STRONG_LEXICON if re.search(r"\b" + re.escape(term) + r"\b", low)}


def is_computer_science(title: str, abstract: str) -> bool:
    """Article accepté comme informatique (décision du contrôleur, suite task 2b-fix) :

    les termes génériques (WEAK_LEXICON : "data", "model", "platform"...) ne comptent plus
    seuls -- ils apparaissent aussi dans des articles d'économie, de santé publique, etc.
    On exige des termes STRONG distincts :
      - le titre contient >= 1 terme STRONG ET titre+résumé en contiennent >= 2 distincts ; OU
      - titre+résumé contiennent >= 3 termes STRONG distincts (même sans terme dans le titre).
    """
    title_strong = _strong_terms_in(title)
    combined_strong = _strong_terms_in(f"{title or ''} {abstract or ''}")
    if title_strong and len(combined_strong) >= 2:
        return True
    return len(combined_strong) >= 3


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
    if not is_computer_science(title, abstract):
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


def load_exclusions(path: Path) -> set[str]:
    """Charge la liste d'exclusion manuelle : un titre normalisé (norm_title) ou un id OpenAlex
    par ligne ; lignes vides et commentaires ('#') ignorés."""
    if not path.exists():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def is_excluded(work: dict, title: str, exclusions: set[str]) -> bool:
    """Vrai si `work` correspond à une entrée de la liste d'exclusion (titre normalisé ou id)."""
    wid = str(work.get("id") or "")
    return norm_title(title) in exclusions or wid in exclusions or wid.rsplit("/", 1)[-1] in exclusions


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
    # Best-effort : le endpoint `search` (10 crédits/appel) est distinct des endpoints
    # `filter` des phases 2/3 et peut être limité indépendamment (fenêtre courte). Un
    # QuotaExceeded ici ne doit pas annuler tout le run : les affiliations restantes sont
    # simplement laissées à vérifier manuellement (data/affiliations_a_verifier.txt), comme
    # c'est déjà le cas quand un titre n'est pas retrouvé.
    quota_hit_in_phase1 = False
    for d in originals:
        uni, url = "", None
        if not quota_hit_in_phase1:
            try:
                uni, url = find_original_affiliation(d.title)
                time.sleep(0.15)
            except QuotaExceeded as e:
                quota_hit_in_phase1 = True
                print(f"  quota OpenAlex atteint (endpoint search) : affiliations restantes "
                      f"laissées à vérifier manuellement (pause {e.retry_after_seconds}s avant la suite)")
                time.sleep(min(e.retry_after_seconds, 90))
        if not uni:
            todo.append(f"{d.id}\t{d.title}\t{d.authors}")
        if url:
            doi[d.id] = url
        rows.append([d.id, d.title, d.abstract, d.authors, d.year, uni])

    print("2/3 Candidats : informatique (filtre lexical), auteurs affiliés au Burkina Faso...")
    exclusions = load_exclusions(config.EXCLUSIONS)
    # Un seul passage sur tout le corpus BF_FILTER (17 282 travaux, ~87 pages à 1 crédit/page,
    # mis en cache disque) : réutilisé pour les candidats (ci-dessous) ET le corpus Word2Vec
    # (phase 3) -- pas de filtre OpenAlex par domaine, is_computer_science est seul juge.
    bf_works = fetch_all(BF_FILTER, limit=BF_FETCH_LIMIT)
    cands, excluded = [], 0
    for w in bf_works:
        c = to_candidate(w)
        if not c or norm_title(c["title"]) in seen:
            continue
        if is_excluded(w, c["title"], exclusions):
            excluded += 1
            continue
        seen.add(norm_title(c["title"]))
        cands.append(c)
    chosen = select_diverse(cands, TARGET_NEW, PER_SUBFIELD)
    for new_id, c in zip(next_ids(len(originals) + 1, len(chosen)), chosen):
        rows.append([new_id, c["title"], c["abstract"], c["authors"], c["year"], c["university"]])
        doi[new_id] = c["url"]
    print(f"   {len(bf_works)} travaux BF -> {len(cands)} candidats informatique valides "
          f"({excluded} exclus manuellement) -> {len(chosen)} retenus")

    print("3/3 Corpus d'entraînement Word2Vec (résumés BF non indexés)...")
    extra = []
    for w in bf_works:
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
