# FasoSearch, Système de Recherche d'Information

Devoir de Recherche d'Information, Master IA 2026-2027.
Moteur de recherche sur 90 articles scientifiques **en anglais** d'auteurs affiliés
à des institutions du **Burkina Faso**, interrogeable **en français ou en anglais**.

## Lancer (démo)

```bash
~/.venvs/sri/bin/python run.py
```
Le navigateur s'ouvre sur http://127.0.0.1:8000. Tout fonctionne **hors ligne**.

## Installation (une seule fois, avec internet)

```bash
python -m venv ~/.venvs/sri && ~/.venvs/sri/bin/pip install -r requirements.txt
~/.venvs/sri/bin/python scripts/setup_resources.py      # données NLTK + modèle de traduction fr -> en
cd frontend && npm install --no-bin-links && npm run build && cd ..
```

Ces deux étapes ont déjà été exécutées **sur ce poste de développement** (nécessitent
internet, ne pas les relancer sans raison) ; elles produisent des fichiers volumineux
non suivis par git (voir `.gitignore` et la section suivante), qu'il faut donc copier ou
régénérer sur toute autre machine (dépôt cloné, clé USB de remise du projet…) :
```bash
# (déjà fait ici) ~/.venvs/sri/bin/python scripts/augment_data.py    -> base complète (90 documents)
# (déjà fait ici) ~/.venvs/sri/bin/python scripts/fetch_w2v_cs.py    -> corpus d'entraînement Word2Vec (informatique)
```

## Fichiers à livrer avec le projet

`.gitignore` exclut volontairement les fichiers volumineux ou régénérables (modèles
entraînés, données NLTK, build du frontend, corpus d'entraînement téléchargés) : un
`git clone` seul ne suffit pas à faire tourner FasoSearch. Pour remettre ou déplacer le
projet (clé USB, archive pour la soutenance...), copier en plus, depuis ce poste :

| Chemin | Contenu | Obligatoire |
|---|---|---|
| `../données textuelles - base complète.xlsx` (hors de `sri/`, dans `Devoir/`) | les 90 documents indexés | oui |
| `data/w2v_extra.txt` | ~16 000 résumés burkinabè (entraînement Word2Vec) | oui |
| `data/w2v_cs.txt` | ~15 000 résumés d'informatique (entraînement Word2Vec) | oui |
| `data/openalex_cache/` | cache des réponses OpenAlex (évite de reconsommer le quota si `augment_data.py`/`fetch_w2v_cs.py` sont relancés) | non (optionnel) |
| `models/` | index prétraité (`doc_terms.json`) + Word2Vec entraîné (`w2v.kv`) | oui, sinon régénéré au premier lancement (15-25 min) |
| `lang_models/` | modèle de traduction fr -> en (Argos/ctranslate2) | oui |
| `nltk_data/` | stopwords, WordNet, tagger POS | oui |
| `backend/static/` | build du frontend (`npm run build`) | oui, sinon régénérable via `cd frontend && npm run build` |

Sans `models/`, `lang_models/` ou `nltk_data/`, relancer respectivement
`scripts/build_index.py` (ou laisser `run.py` le faire automatiquement) et
`scripts/setup_resources.py`.

## Origine des données

Les 60 articles ajoutés à la base d'origine (30 articles) viennent d'**OpenAlex**
(https://openalex.org), une base bibliographique ouverte qui agrège les métadonnées de
sources comme IEEE Xplore, ACM, arXiv, Springer, Elsevier, etc. : le champ DOI de chaque
article (`data/doi.json`) pointe vers l'éditeur d'origine. Limite connue : un article dont
le résumé n'est pas disponible dans OpenAlex (`has_abstract:false`) ne peut pas être indexé,
même s'il correspond au filtre d'affiliation et de domaine ; ce n'est donc pas un échantillon
exhaustif des publications burkinabè en informatique, seulement de celles dont le résumé est
public sur OpenAlex.

`scripts/augment_data.py` interroge OpenAlex pour les travaux ayant au moins un auteur
affilié à une institution du Burkina Faso (`institutions.country_code:BF`), en anglais, avec
résumé disponible. Comme le champ `primary_topic` d'OpenAlex ne couvre qu'une petite partie
du corpus et laisse passer des articles hors informatique, l'appartenance au domaine
informatique est décidée par un **filtre lexical strict** (`is_computer_science`) : au moins
2 termes non ambigus (« algorithm », « neural network », « cybersecurity », etc., voir
`STRONG_LEXICON`) dont un dans le titre, ou au moins 3 dans le titre et le résumé. Les termes
génériques (« data », « model », « platform »...) ne comptent jamais seuls, car ils
apparaissent aussi dans des articles de santé, d'agriculture ou d'économie qui utilisent le
machine learning comme simple outil. Une seconde passe humaine a écarté au cas par cas les
articles encore mal classés (ex. usage de l'IA en cardiologie, en épidémiologie du paludisme)
malgré le filtre lexical : voir `data/exclusions.txt` (122 titres exclus, avec le motif de
chaque exclusion en commentaire).

Répartition des éditeurs des 60 articles ajoutés (préfixe DOI, `data/doi.json`) :

| Éditeur | Articles |
|---|---|
| IEEE | 25 |
| SciRP | 5 |
| IJACSA | 5 |
| Elsevier | 2 |
| IFIP | 2 |
| ACM | 2 |
| AIRCC | 2 |
| IAES | 2 |
| Autres (12 éditeurs distincts, 1 article chacun) | 12 |
| Sans DOI (identifiant OpenAlex uniquement) | 3 |

4 articles de la base d'origine (`Document_03`, `Document_04`, `Document_07`, `Document_23`,
voir `data/affiliations_a_verifier.txt`) n'ont pas pu être rattachés automatiquement à une
université burkinabè (titre introuvable via l'API de recherche OpenAlex, quota ou
correspondance insuffisante) : **leur colonne University est à compléter à la main** dans
`données textuelles - base complète.xlsx` avant la soutenance (voir section suivante), à
partir des informations sur les auteurs qui figurent déjà dans
`data/affiliations_a_verifier.txt`.

## À faire avant la soutenance

Compléter à la main la colonne `University` de ces 4 documents dans
`données textuelles - base complète.xlsx` (auteurs ci-dessous, source :
`data/affiliations_a_verifier.txt`) puis relancer `scripts/build_index.py` :

| Document | Auteurs |
|---|---|
| `Document_03` | Tapsoba Abdou Romaric ; Ouédraogo Tounwendyam Frédéric |
| `Document_04` | Zerbo Boureima ; Ouédraogo Tounwendyam Frédéric ; Yélémou Tiguiane ; Séré Abdoulaye |
| `Document_07` | Frédéric T. Ouédraogo ; Boureima Zerbo |
| `Document_23` | Lydie Simone Kone/Tapsoba ; Yaya Traoré ; Sadouanouan Malo |

## Corpus d'entraînement Word2Vec

Word2Vec est entraîné sur un corpus plus large que les 90 documents indexés, jamais affiché
comme résultat de recherche :
- les 90 documents indexés (résumés + titres) ;
- `data/w2v_extra.txt` : environ 16 000 résumés d'auteurs burkinabè (tous domaines), pour que
  les mots généraux du corpus aient des voisins de qualité ;
- `data/w2v_cs.txt` : environ 15 000 résumés anglais d'informatique (toutes origines, via
  `scripts/fetch_w2v_cs.py`), ajoutés parce que le corpus burkinabè seul est dominé par
  l'agriculture, la santé et l'hydrologie : les mots d'informatique (« security », « attack »,
  « network »...) y avaient des voisins hors sujet (ex. liés à la sécurité alimentaire plutôt
  qu'à la cybersécurité). Ce corpus complémentaire donne à ces mots leur sens informatique.

Vocabulaire final (`min_count=5`) : environ 30 000 mots.

## Correspondance avec le barème

| Critère | Où le voir |
|---|---|
| Augmentation des données | `scripts/augment_data.py`, fichier `données textuelles - base complète.xlsx`, page **Corpus** |
| IHM | 6 écrans, thèmes Nuit / Faso, interface FR / EN |
| Prétraitement | `backend/app/preprocess.py`, page **Laboratoire** |
| Requête prétraitée | bloc « Requête -> Traduction -> Prétraitée » de chaque recherche |
| Affichage des scores | anneaux de score, « Pourquoi ce score ? », page **Comparer** |
| Français / Anglais | `backend/app/language.py` (détection + traduction hors ligne) |
| Word2Vec & Cosinus | `backend/app/word2vec.py` (seuil cosinus retenu : 0.58) |
| TF-IDF & Cosinus | `backend/app/tfidf.py` (TF = tf / max tf, IDF = log N/df) |
| Bonus BM25 (TP 3) | `backend/app/bm25.py` |

## Réglage du seuil Word2Vec

`scripts/smoke_demo.py` exécute les requêtes de démonstration sur la vraie base et compte
celles dont le nombre de résultats Word2Vec sort de l'intervalle [3, 40]. Au seuil initial de
la spec (0.40), la quasi-totalité du corpus dépassait ce seuil de similarité pour presque
toutes les requêtes (jusqu'à 90/90 documents) : les vecteurs moyens pondérés par IDF restent
globalement proches sur ce vocabulaire. Relevé par pas de 0.05, puis affiné par pas de 0.01 (le
prétraitement corrigé lors de la vague de correctifs finale, voir `PREPROCESS_VERSION`, a
légèrement déplacé tous les vecteurs moyens), le seuil **0.58** ramène le nombre de requêtes
hors intervalle à 1 sur 8 requêtes significatives (seule
`Internet exchange points in Africa` dépasse largement, avec 61 documents), ce qui respecte
la règle (au plus 2). `tests/test_config.py` vérifie `config.W2V_THRESHOLD == 0.58`.

## Requêtes de démonstration

`scripts/smoke_demo.py` :

```bash
~/.venvs/sri/bin/python scripts/smoke_demo.py
```

| Requête | Ce qu'elle montre |
|---|---|
| `intrusion detection in networks` | TF-IDF + cosinus, contributions par terme |
| `détection d'intrusion dans les réseaux` | même requête en français, détection de langue, traduction |
| `apprentissage automatique pour la santé` | traduction FR -> EN neuronale (« machine learning for health ») |
| `Internet exchange points in Africa` | comparaison des scores TF-IDF / Word2Vec / BM25 (page **Comparer**) |
| `ontologie pour l'agriculture` | traduction FR -> EN (« ontology for agriculture ») |
| `malware` (Word2Vec) | Word2Vec trouve 6 documents, dont 3 que TF-IDF ne trouve pas du tout (`Document_03`, `Document_49`, `Document_54` : « Detecting Illicit Data Leaks on Android Smartphones... », qui ne contient jamais le mot « malware » mais dont le vecteur moyen est proche par le sens) |
| `security of government websites` | comparaison BM25 vs TF-IDF (même classement, échelles de score différentes) |
| `deep learning image counting` | Word2Vec & cosinus, requête multi-termes |
| `the of and` | requête entièrement composée de mots vides : aucun terme après prétraitement |

## Architecture

`preprocess -> index inversé -> TF-IDF / BM25 / Word2Vec -> cosinus -> classement -> pagination`,
servi par FastAPI (`backend/app/api.py`) à une interface React (`frontend/`).

## Tests

```bash
~/.venvs/sri/bin/python -m pytest -v
cd frontend && npm test
```
