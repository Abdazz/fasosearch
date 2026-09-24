"""Vérifie les requêtes de démonstration sur la vraie base et affiche un rapport.

Usage : python scripts/smoke_demo.py
Critère de réglage du seuil Word2Vec : pour chaque requête de démo significative,
Word2Vec doit renvoyer entre 3 et 40 documents.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.engine import SearchEngine  # noqa: E402

DEMO_QUERIES = [
    ("intrusion detection in networks", "TF-IDF & cosinus / requête EN"),
    ("détection d'intrusion dans les réseaux", "Français → Anglais"),
    ("apprentissage automatique pour la santé", "Français → Anglais (correction « machine learning »)"),
    ("Internet exchange points in Africa", "Affichage des scores / comparaison"),
    ("ontologie pour l'agriculture", "Français → Anglais"),
    ("malware", "Word2Vec : documents sans le mot exact"),
    ("security of government websites", "BM25 vs TF-IDF"),
    ("deep learning image counting", "Word2Vec & cosinus"),
    ("the of and", "Requête prétraitée : que des stopwords"),
]


def main() -> None:
    engine = SearchEngine.load()
    bad = 0
    for q, criterion in DEMO_QUERIES:
        print(f"\n■ {q}   [{criterion}]")
        for model in ("tfidf", "w2v", "bm25"):
            r = engine.search(q, model=model)
            top = r["results"][0] if r["results"] else None
            print(f"  {model:6} total={r['total']:3} msg={r['message']} "
                  f"top={top['score'] if top else '-'} {top['title'][:60] if top else ''}")
            if model == "w2v" and r["message"] is None and not (3 <= r["total"] <= 40):
                bad += 1
        info = engine.analyze_query(q)
        print(f"  langue={info['language']} traduction={info['translated']} ({info['method']}) termes={info['terms']}")
    print(f"\nRequêtes où le seuil Word2Vec est hors de [3, 40] résultats : {bad}")


if __name__ == "__main__":
    main()
