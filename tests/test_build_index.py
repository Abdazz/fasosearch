from scripts import build_index


def test_fingerprint_changes_with_file(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a")
    f1 = build_index.fingerprint(p)
    p.write_text("abc")
    assert build_index.fingerprint(p) != f1


def test_fingerprint_of_missing_file():
    assert build_index.fingerprint(build_index.config.ROOT / "nope.xyz") == "absent"
