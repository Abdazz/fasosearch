"""Corpus d'ENTRAÎNEMENT Word2Vec (task 17b) : résumés anglais d'informatique (OpenAlex),
de toutes origines — jamais indexés, jamais affichés comme résultat de recherche. Seul
`scripts/build_index.py` les consomme, en plus de la base indexée (90 documents burkinabè,
inchangée) et de `data/w2v_extra.txt` (résumés BF non indexés).

Décision du contrôleur (constat : le corpus d'entraînement actuel est dominé par
l'agriculture/santé/hydrologie, ce qui donne des voisins Word2Vec hors sujet pour les mots
d'informatique). On complète donc, sans toucher à la base indexée, avec des résumés
d'informatique de toutes origines (pas seulement burkinabè) sur ces sous-domaines OpenAlex :
Artificial Intelligence (1702), Computer Networks and Communications (1705),
Computer Vision and Pattern Recognition (1707), Information Systems (1710), Software (1712),
Signal Processing (1711), Hardware and Architecture (1708), Computer Science Applications
(1706).

Pour chaque sous-domaine : `filter=primary_topic.subfield.id:<ID>,language:en,
has_abstract:true,type:article`, `sort=cited_by_count:desc`, `per-page=200`, pagination par
curseur, au plus `MAX_PAGES_PER_SUBFIELD` pages (1 000 résultats bruts) -- budget borné à
8 * 5 = 40 crédits (1 crédit/page non déjà en cache disque), sous la limite de 60 crédits
fixée pour cette tâche.

Un résumé est gardé (`f"{title}. {abstract}"`) s'il fait >= `MIN_WORDS` mots ; dédoublonné par
titre normalisé (`norm_title`) ; les titres déjà présents dans la base indexée (90 articles)
sont exclus (elle ne doit jamais être modifiée par ce script).

Tout est accumulé en mémoire et `data/w2v_cs.txt` n'est écrit qu'à la toute fin : sur
`QuotaExceeded` (429 OpenAlex), message clair et arrêt immédiat, sans fichier partiel.

Usage : python scripts/fetch_w2v_cs.py   (nécessite internet)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import config  # noqa: E402
from backend.app.corpus import load_corpus  # noqa: E402
from scripts.augment_data import QuotaExceeded, _get, clean, norm_title, rebuild_abstract  # noqa: E402

SUBFIELDS = {
    "1702": "Artificial Intelligence",
    "1705": "Computer Networks and Communications",
    "1707": "Computer Vision and Pattern Recognition",
    "1710": "Information Systems",
    "1712": "Software",
    "1711": "Signal Processing",
    "1708": "Hardware and Architecture",
    "1706": "Computer Science Applications",
}
PER_PAGE = 200
MAX_PAGES_PER_SUBFIELD = 5  # 1 000 résultats bruts max par sous-domaine
MIN_WORDS = 40
SELECT = "id,title,abstract_inverted_index"


def fetch_subfield_raw(subfield_id: str, max_pages: int = MAX_PAGES_PER_SUBFIELD,
                        per_page: int = PER_PAGE) -> list[dict]:
    """Résultats bruts OpenAlex d'un sous-domaine, pagination par curseur, au plus
    `max_pages` pages (budget), arrêt anticipé si `next_cursor` est vide."""
    filt = f"primary_topic.subfield.id:{subfield_id},language:en,has_abstract:true,type:article"
    out: list[dict] = []
    cursor = "*"
    for _ in range(max_pages):
        if not cursor:
            break
        data = _get("works", {"filter": filt, "sort": "cited_by_count:desc",
                               "per-page": per_page, "cursor": cursor, "select": SELECT})
        out.extend(data.get("results", []))
        cursor = (data.get("meta") or {}).get("next_cursor")
    return out


def keep_line(work: dict, seen_titles: set[str], min_words: int = MIN_WORDS) -> str | None:
    """Renvoie `"Titre. Résumé"` si le résumé fait >= `min_words` mots et que le titre
    normalisé n'est pas déjà dans `seen_titles` (mis à jour en place sinon)."""
    title = clean(work.get("title"))
    if not title:
        return None
    abstract = clean(rebuild_abstract(work.get("abstract_inverted_index")))
    if len(abstract.split()) < min_words:
        return None
    key = norm_title(title)
    if key in seen_titles:
        return None
    seen_titles.add(key)
    return f"{title}. {abstract}"


def indexed_titles() -> set[str]:
    """Titres normalisés de la base indexée (90 documents) : jamais réintroduits dans le
    corpus d'entraînement Word2Vec puisqu'ils y figurent déjà via `doc_terms`."""
    return {norm_title(d.title) for d in load_corpus(config.CORPUS_EXCEL)}


def _run() -> list[str]:
    seen = indexed_titles()
    lines: list[str] = []
    for subfield_id, name in SUBFIELDS.items():
        works = fetch_subfield_raw(subfield_id)
        before = len(lines)
        for w in works:
            line = keep_line(w, seen)
            if line:
                lines.append(line)
        print(f"  {name} ({subfield_id}) : {len(works)} résultats bruts -> "
              f"{len(lines) - before} résumés retenus")
    return lines


def main() -> None:
    """Attrape QuotaExceeded : message clair, aucun fichier de sortie partiel écrit (tout est
    accumulé en mémoire dans `_run`, l'écriture disque est la toute dernière étape)."""
    try:
        lines = _run()
    except QuotaExceeded as e:
        minutes = -(-e.retry_after_seconds // 60)  # arrondi au supérieur
        print(f"Quota OpenAlex épuisé : réessayez dans {minutes} minutes. Aucun fichier écrit.")
        sys.exit(1)
    config.DATA_DIR.mkdir(exist_ok=True)
    config.W2V_CS.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{len(lines)} résumés d'informatique écrits dans {config.W2V_CS.name}")


if __name__ == "__main__":
    main()
