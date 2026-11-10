"""English · Uzbek · Russian IT glossary with search.

The built-in glossary lives in ``uzloc/data/glossary.csv``. You can also load
your own CSV with the same columns: ``en, uz, ru, category``.

Search works in all three languages. Uzbek can be typed in Latin or Cyrillic,
and any apostrophe variant (ʻ ‘ ’ ') is accepted for o' and g'.
"""

import csv
import difflib
from dataclasses import asdict, dataclass
from importlib import resources
from pathlib import Path

from uzloc.translit import cyrillic_to_latin, detect_script, normalize_apostrophes

LANGUAGES = ("en", "uz", "ru")
REQUIRED_COLUMNS = ("en", "uz", "ru")

# Scores for ranking results: a better kind of match gets a higher number.
EXACT, PREFIX, WORD, CONTAINS = 100, 80, 60, 40
FUZZY_CUTOFF = 0.75


@dataclass(frozen=True)
class Term:
    en: str
    uz: str
    ru: str
    category: str = "general"

    def get(self, lang: str) -> str:
        return getattr(self, lang)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Match:
    term: Term
    lang: str   # which column matched
    score: int  # higher is better


class GlossaryError(ValueError):
    """Raised when a glossary file is missing columns or is empty."""


def normalize(text: str) -> str:
    """Lower-case, trim, unify apostrophes and turn Uzbek Cyrillic into Latin.

    This lets "Ўчириш", "o‘chirish" and "O'CHIRISH" all match the same term.
    """
    text = normalize_apostrophes(text.strip().lower())
    return " ".join(text.split())


def _uz_key(text: str) -> str:
    """Normalize Uzbek text so Cyrillic input can match Latin entries."""
    text = normalize(text)
    if detect_script(text) in ("cyrillic", "mixed"):
        text = normalize(cyrillic_to_latin(text))
    return text


def _key(text: str, lang: str) -> str:
    return _uz_key(text) if lang == "uz" else normalize(text)


def load_glossary(path=None) -> list:
    """Load terms from a CSV file. With no path, load the built-in glossary."""
    if path is None:
        source = resources.files("uzloc").joinpath("data/glossary.csv")
        text = source.read_text(encoding="utf-8")
    else:
        text = Path(path).read_text(encoding="utf-8-sig")

    reader = csv.DictReader(text.splitlines())
    columns = [c.strip().lower() for c in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing:
        raise GlossaryError(f"Glossary is missing column(s): {', '.join(missing)}")

    terms = []
    for row in reader:
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        if not any(row.get(lang) for lang in REQUIRED_COLUMNS):
            continue  # skip empty lines
        terms.append(Term(
            en=row.get("en", ""),
            uz=row.get("uz", ""),
            ru=row.get("ru", ""),
            category=row.get("category") or "general",
        ))
    if not terms:
        raise GlossaryError("Glossary has no terms.")
    return terms


def _score(query: str, value: str) -> int:
    """How well does `value` match `query`? 0 means no match."""
    if not value:
        return 0
    if value == query:
        return EXACT
    if value.startswith(query):
        return PREFIX
    if query in value.split():
        return WORD
    if query in value:
        return CONTAINS
    return 0


def search(query, terms=None, lang="any", category=None, fuzzy=True, limit=10) -> list:
    """Find terms that match `query`.

    lang:     "en", "uz", "ru" or "any" (search all three columns)
    category: only return terms from this category (e.g. "ui", "git")
    fuzzy:    if nothing matches directly, suggest close spellings ("pasword")
    limit:    maximum number of results (None for all)
    """
    if terms is None:
        terms = load_glossary()
    if lang != "any" and lang not in LANGUAGES:
        raise ValueError(f"lang must be one of {LANGUAGES} or 'any', not {lang!r}")
    if not query or not query.strip():
        return []

    langs = LANGUAGES if lang == "any" else (lang,)
    pool = [t for t in terms if category is None or t.category == category]

    matches = []
    for term in pool:
        best = None
        for code in langs:
            score = _score(_key(query, code), _key(term.get(code), code))
            if score and (best is None or score > best.score):
                best = Match(term, code, score)
        if best:
            matches.append(best)

    if not matches and fuzzy:
        matches = _fuzzy(query, pool, langs)

    # Best score first, then shorter (more precise) terms, then A-Z.
    matches.sort(key=lambda m: (-m.score, len(m.term.get(m.lang)), m.term.en))
    return matches[:limit] if limit else matches


def _fuzzy(query, pool, langs) -> list:
    """Suggest terms with a similar spelling, for typos like 'pasword'."""
    found = {}
    for code in langs:
        q = _key(query, code)
        index = {_key(t.get(code), code): t for t in pool if t.get(code)}
        for close in difflib.get_close_matches(q, index, n=5, cutoff=FUZZY_CUTOFF):
            term = index[close]
            ratio = difflib.SequenceMatcher(None, q, close).ratio()
            score = int(ratio * CONTAINS)  # always ranks below real matches
            if term not in found or score > found[term].score:
                found[term] = Match(term, code, score)
    return list(found.values())


def lookup(word, terms=None, lang="en"):
    """Return the single term whose `lang` column equals `word`, or None."""
    for match in search(word, terms, lang=lang, fuzzy=False, limit=None):
        if match.score == EXACT:
            return match.term
    return None


def categories(terms=None) -> dict:
    """Return {category: number of terms}, sorted by name."""
    if terms is None:
        terms = load_glossary()
    counts = {}
    for term in terms:
        counts[term.category] = counts.get(term.category, 0) + 1
    return dict(sorted(counts.items()))
