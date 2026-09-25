"""Index des auteurs : nettoyage des noms, regroupement des variantes, recherche par nom."""
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .corpus import Document

# Accent détaché de sa lettre par l'extraction PDF : "Bassol ́e" -> "Bassolé".
_DETACHED_ACCENT_RE = re.compile(r"\s([̀-ͯ])([^\W\d_])")
_ORPHAN_MARK_RE = re.compile(r"(^|\s)[̀-ͯ]+")
_LAMDI_RE = re.compile(r"\s+lamdi\s*$", re.IGNORECASE)
_SPACES_RE = re.compile(r"\s+")
_ASCII_WORD_RE = re.compile(r"[a-z]+")
_WORD_RE = re.compile(r"[^\W\d_]+")
MIN_QUERY_LETTERS = 2


def clean_name(raw: str) -> str:
    """Nettoie une écriture brute : accents détachés, signes orphelins, suffixe Lamdi, espaces."""
    s = _DETACHED_ACCENT_RE.sub(r"\2\1", raw)
    s = _ORPHAN_MARK_RE.sub(r"\1", s)
    s = unicodedata.normalize("NFC", s)
    s = _LAMDI_RE.sub("", s)
    return _SPACES_RE.sub(" ", s).strip()


def display_authors(s: str) -> str:
    """Chaîne d'auteurs brute (colonne Authors) nettoyée pour l'affichage : recolle les accents
    détachés de chaque écriture (séparées par ';'), retire les écritures vides."""
    return "; ".join(c for c in (clean_name(p) for p in s.split(";")) if c)


def _has_caps_word(name: str) -> bool:
    """Vrai si `name` contient un mot de plus d'une lettre écrit tout en majuscules."""
    return any(len(w) > 1 and w.isupper() for w in _WORD_RE.findall(name))


def fold(s: str) -> str:
    """Minuscules ASCII, sans diacritiques."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def name_tokens(name: str) -> list[str]:
    return _ASCII_WORD_RE.findall(fold(name))


def _key(name: str) -> str:
    return " ".join(name_tokens(clean_name(name)))


def _full(name: str) -> set[str]:
    return {t for t in name_tokens(name) if len(t) > 1}


def _initials(name: str) -> set[str]:
    return {t[0] for t in name_tokens(name)}


def _included(s: str, l: str) -> bool:
    fs = _full(s)
    return len(fs) >= 2 and fs <= _full(l) and _initials(s) <= _initials(l)


def same_person(a: str, b: str) -> bool:
    """Deux écritures désignent la même personne (règle symétrique de la spécification)."""
    return _included(a, b) or _included(b, a)


def slugify(name: str) -> str:
    return "-".join(name_tokens(name)) or "auteur"


def highlight_name(name: str, q: str) -> list[dict]:
    """Découpe le nom en segments ; hit=True pour les mots dont un mot normalisé commence par un mot de q."""
    qt = name_tokens(q)
    segs, last = [], 0
    for m in _WORD_RE.finditer(name):
        if qt and any(w.startswith(t) for w in name_tokens(m.group()) for t in qt):
            if m.start() > last:
                segs.append({"text": name[last:m.start()], "hit": False})
            segs.append({"text": m.group(), "hit": True})
            last = m.end()
    if last < len(name):
        segs.append({"text": name[last:], "hit": False})
    return segs


@dataclass(frozen=True)
class AliasRule:
    kind: str  # "fusion" ou "separer"
    a: str
    b: str
    line: int


def parse_aliases(path: Path) -> list[AliasRule]:
    rules = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, sep, rest = line.partition(":")
        kind = kind.strip().lower()
        splitter = {"fusion": "=", "separer": "|"}.get(kind)
        parts = [p.strip() for p in rest.split(splitter)] if sep and splitter else []
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"{path.name}, ligne {n} : format attendu « fusion: A = B » ou « separer: A | B »")
        rules.append(AliasRule(kind, parts[0], parts[1], n))
    return rules


def _auto_groups(forms: list[str]) -> list[list[str]]:
    parent = {f: f for f in forms}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(forms):
        for b in forms[i + 1:]:
            if same_person(a, b):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb
    groups: dict[str, list[str]] = {}
    for f in forms:
        groups.setdefault(find(f), []).append(f)
    return list(groups.values())


def _apply_rules(groups: list[list[str]], rules: list[AliasRule], source: str) -> list[list[str]]:
    by_key = {_key(f): f for g in groups for f in g}

    def resolve(name: str, line: int) -> str:
        f = by_key.get(_key(name))
        if f is None:
            raise ValueError(f"{source}, ligne {line} : auteur inconnu « {name} »")
        return f

    def group_of(f: str) -> list[str]:
        return next(g for g in groups if f in g)

    for r in (r for r in rules if r.kind == "separer"):
        a, b = resolve(r.a, r.line), resolve(r.b, r.line)
        g = group_of(a)
        if b not in g:
            continue
        groups.remove(g)
        ga, gb = [a], [b]
        for f in g:
            if f not in (a, b):
                (gb if len(_full(f) & _full(b)) > len(_full(f) & _full(a)) else ga).append(f)
        groups += [ga, gb]
    for r in (r for r in rules if r.kind == "fusion"):
        ga, gb = group_of(resolve(r.a, r.line)), group_of(resolve(r.b, r.line))
        if ga is not gb:
            groups.remove(gb)
            ga.extend(gb)
    return groups


@dataclass
class Author:
    id: str
    name: str
    variants: list[str]               # autres écritures, hors nom affiché, triées
    doc_ids: list[str]                # ordre du corpus
    word_sets: list[frozenset[str]]   # mots normalisés de chaque écriture


class AuthorIndex:
    def __init__(self, docs: list[Document], aliases: Path | None = None):
        self.docs = {d.id: d for d in docs}
        doc_names = {d.id: list(dict.fromkeys(c for c in (clean_name(x) for x in d.authors.split(";")) if c))
                     for d in docs}
        freq = Counter(n for names in doc_names.values() for n in names)
        groups = _auto_groups(sorted(freq))
        if aliases is not None and aliases.exists():
            groups = _apply_rules(groups, parse_aliases(aliases), aliases.name)

        named = sorted(((min(g, key=lambda f: (-freq[f], _has_caps_word(f),
                                                -sum(ord(c) > 127 for c in f), -len(f), f)), g)
                        for g in groups),
                       key=lambda x: (fold(x[0]), x[0]))
        used: Counter = Counter()
        self.authors: list[Author] = []
        form_to_author: dict[str, Author] = {}
        for display, g in named:
            base = slugify(display)
            used[base] += 1
            author = Author(base if used[base] == 1 else f"{base}-{used[base]}", display,
                            sorted(f for f in g if f != display), [], [frozenset(name_tokens(f)) for f in g])
            self.authors.append(author)
            form_to_author.update({f: author for f in g})
        self.by_id = {a.id: a for a in self.authors}

        self.by_doc: dict[str, list[tuple[str, str]]] = {}
        for d in docs:
            links: list[tuple[str, str]] = []
            for f in doc_names[d.id]:
                a = form_to_author[f]
                if all(a.id != i for i, _ in links):
                    links.append((a.id, a.name))
                    a.doc_ids.append(d.id)
            self.by_doc[d.id] = links

    # -- recherche
    def search(self, q: str) -> list[Author]:
        qt = name_tokens(q)
        if sum(map(len, qt)) < MIN_QUERY_LETTERS:
            return []
        qset = frozenset(qt)
        hits = []
        for a in self.authors:
            words = frozenset().union(*a.word_sets)
            if all(any(w.startswith(t) for w in words) for t in qt):
                hits.append((qset not in a.word_sets, -len(a.doc_ids), fold(a.name), a))
        hits.sort(key=lambda h: h[:3])
        return [h[3] for h in hits]

    # -- profils
    def _universities(self, doc_ids: list[str]) -> list[str]:
        c = Counter(u.strip() for i in doc_ids for u in self.docs[i].university.split(";") if u.strip())
        return [u for u, _ in sorted(c.items(), key=lambda kv: (-kv[1], fold(kv[0])))]

    def _years(self, doc_ids: list[str]) -> list[int] | None:
        ys = [self.docs[i].year for i in doc_ids if self.docs[i].year is not None]
        return [min(ys), max(ys)] if ys else None

    def summary(self, a: Author) -> dict:
        return {"id": a.id, "name": a.name, "count": len(a.doc_ids),
                "universities": self._universities(a.doc_ids), "years": self._years(a.doc_ids)}

    def profile(self, author_id: str) -> dict | None:
        a = self.by_id.get(author_id)
        if a is None:
            return None
        co: Counter = Counter()
        names: dict[str, str] = {}
        for i in a.doc_ids:
            for cid, cname in self.by_doc[i]:
                if cid != a.id:
                    co[cid] += 1
                    names[cid] = cname
        coauthors = [{"id": c, "name": names[c], "count": n}
                     for c, n in sorted(co.items(), key=lambda kv: (-kv[1], fold(names[kv[0]])))]
        doc_ids = sorted(a.doc_ids, key=lambda i: (self.docs[i].year is None, -(self.docs[i].year or 0),
                                                   fold(self.docs[i].title)))
        return {**self.summary(a), "variants": a.variants, "coauthors": coauthors, "doc_ids": doc_ids}
