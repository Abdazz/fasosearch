import zipfile

from scripts.prune_nltk import prune


def _zip(path, member):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(member, "data")


def test_prune_keeps_only_listed_packages_extracted(tmp_path):
    corpora = tmp_path / "corpora"
    corpora.mkdir()
    (corpora / "stopwords").mkdir()
    (corpora / "stopwords" / "english").write_text("the")
    _zip(corpora / "stopwords.zip", "stopwords/english")
    _zip(corpora / "wordnet.zip", "wordnet/index.noun")        # zip seul : doit être extrait
    (corpora / "brown").mkdir()                                # non listé : supprimé
    _zip(corpora / "brown.zip", "brown/ca01")

    prune(tmp_path, ["stopwords", "wordnet"])

    assert (corpora / "stopwords" / "english").exists()
    assert (corpora / "wordnet" / "index.noun").exists()
    assert not (corpora / "brown").exists()
    assert not list(tmp_path.rglob("*.zip"))
