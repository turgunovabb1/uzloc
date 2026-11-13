"""Quality checks for translation files.

Compare a source file (usually English) with a translation and report problems
a human reviewer would otherwise have to find by eye:

    missing        key exists in the source but not in the translation   (error)
    extra          key exists only in the translation                    (warning)
    empty          translation is an empty string                        (error)
    untranslated   translation is identical to the source text           (warning)
    placeholders   {name}, %s, %(n)d, {{x}} ... differ from the source    (error)
    tags           HTML tags such as <b> or </a> differ from the source   (error)
    script         Uzbek text mixes Latin and Cyrillic, or uses the wrong (warning)
                   script when --script is given
    whitespace     leading/trailing spaces differ from the source         (warning)
    punctuation    final . ! ? : … differs from the source                (warning)
    fuzzy          PO entry is marked "#, fuzzy" and needs review         (warning)
"""

import re
from collections import Counter
from dataclasses import asdict, dataclass

from uzloc.loaders import Catalog

ERROR, WARNING = "error", "warning"

SEVERITY = {
    "missing": ERROR,
    "empty": ERROR,
    "placeholders": ERROR,
    "tags": ERROR,
    "extra": WARNING,
    "untranslated": WARNING,
    "script": WARNING,
    "whitespace": WARNING,
    "punctuation": WARNING,
    "fuzzy": WARNING,
}
ALL_CHECKS = tuple(SEVERITY)

# {name} {0} {{name}} %s %d %1$s %(name)s %@ $name$
PLACEHOLDER_RE = re.compile(
    r"\{\{\s*[\w.]+\s*\}\}"            # {{name}}  (Handlebars, Vue, Angular)
    r"|\{[\w.]*(?::[^{}]*)?\}"         # {name} {0} {} {count:d}  (Python, ICU, Rust)
    r"|%(?:\d+\$)?[-+#0]*\d*(?:\.\d+)?[sdifuxXoeEgGc@](?![A-Za-z])"  # %s %d %1$s %.2f %@
    r"|%\([\w]+\)[sdif]"               # %(name)s  (Python %)
    r"|\$[A-Za-z_]\w*\$"               # $name$  (Chrome extensions)
)
TAG_RE = re.compile(r"</?[A-Za-z][\w-]*(?:\s[^<>]*)?/?>")
URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+\.\w+")
WORD_RE = re.compile(r"[^\W\d_]+(?:[-'ʻʼ‘’][^\W\d_]+)*")
END_PUNCTUATION = ".!?:…;"

# Short Latin words that are normal inside Uzbek Cyrillic text (brands, units).
LATIN_ALLOWED = re.compile(r"^(?:[A-Z0-9]{2,}|[A-Z][a-z]+[A-Z]\w*|iOS|macOS|Wi-?Fi|e-?mail)$")


@dataclass(frozen=True)
class Issue:
    key: str
    check: str
    message: str
    source: str = ""
    target: str = ""

    @property
    def severity(self) -> str:
        return SEVERITY[self.check]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["severity"] = self.severity
        return data


@dataclass
class Report:
    source_path: str
    target_path: str
    total: int        # number of keys in the source
    translated: int   # keys with a non-empty translation
    issues: list

    @property
    def errors(self) -> list:
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self) -> list:
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def progress(self) -> float:
        """Share of source keys that have a translation, 0-100."""
        return 100.0 if not self.total else round(100 * self.translated / self.total, 1)

    def counts(self) -> dict:
        return dict(Counter(i.check for i in self.issues))

    def to_dict(self) -> dict:
        return {
            "source": self.source_path,
            "target": self.target_path,
            "total": self.total,
            "translated": self.translated,
            "progress": self.progress,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "issues": [i.to_dict() for i in self.issues],
        }


# --- helpers -----------------------------------------------------------------

def placeholders(text: str) -> Counter:
    """Count every placeholder in the text. {count} twice -> {'{count}': 2}."""
    return Counter(re.sub(r"\s+", "", p) for p in PLACEHOLDER_RE.findall(text))


PRINTF_UNNUMBERED_RE = re.compile(r"%[-+#0]*\d*(?:\.\d+)?([sdifuxXoeEgGc@])(?![A-Za-z])")


def printf_order(text: str) -> list:
    """Unnumbered printf types in order: "Found %d files in %s" -> ['d', 's'].

    Their order matters: swapping %d and %s breaks the program, while
    numbered ones (%1$d, %2$s) may be reordered freely.
    """
    return PRINTF_UNNUMBERED_RE.findall(text)


def tags(text: str) -> Counter:
    """Count HTML tags by name and type: <b> and </b> are different tags."""
    return Counter(re.sub(r"\s.*", ">", t).lower().replace("/>", ">") for t in TAG_RE.findall(text))


def _strip_code(text: str) -> str:
    """Remove placeholders, tags and URLs so only human words are left."""
    for pattern in (PLACEHOLDER_RE, TAG_RE, URL_RE):
        text = pattern.sub(" ", text)
    return text


def word_scripts(text: str) -> Counter:
    """Count words written in Latin and in Cyrillic letters."""
    counts = Counter()
    for word in WORD_RE.findall(_strip_code(text)):
        if any("Ѐ" <= ch <= "ӿ" for ch in word):
            counts["cyrillic"] += 1
        elif word.isascii():
            if not LATIN_ALLOWED.match(word):
                counts["latin"] += 1
    return counts


def _describe(diff: Counter) -> str:
    return ", ".join(f"{item}" + (f" ×{n}" if n > 1 else "") for item, n in sorted(diff.items()))


def _has_letters(text: str) -> bool:
    return any(ch.isalpha() for ch in _strip_code(text))


# --- single-string checks -----------------------------------------------------

def check_pair(key, source, target, script=None) -> list:
    """Run every text check on one source/translation pair."""
    issues = []

    def add(check, message):
        issues.append(Issue(key, check, message, source, target))

    if not target.strip():
        add("empty", "translation is empty")
        return issues

    if target.strip() == source.strip() and len(_strip_code(source).strip()) > 3 and _has_letters(source):
        add("untranslated", "translation is the same as the source text")

    src_ph, tgt_ph = placeholders(source), placeholders(target)
    if src_ph != tgt_ph:
        parts = []
        if src_ph - tgt_ph:
            parts.append(f"missing {_describe(src_ph - tgt_ph)}")
        if tgt_ph - src_ph:
            parts.append(f"unexpected {_describe(tgt_ph - src_ph)}")
        add("placeholders", "; ".join(parts))
    elif printf_order(source) != printf_order(target):
        add("placeholders", "printf placeholders changed order "
                            "(use numbered ones like %1$s, %2$d to reorder)")

    src_tags, tgt_tags = tags(source), tags(target)
    if src_tags != tgt_tags:
        parts = []
        if src_tags - tgt_tags:
            parts.append(f"missing {_describe(src_tags - tgt_tags)}")
        if tgt_tags - src_tags:
            parts.append(f"unexpected {_describe(tgt_tags - src_tags)}")
        add("tags", "; ".join(parts))

    words = word_scripts(target)
    if script in ("latin", "cyrillic"):
        other = "cyrillic" if script == "latin" else "latin"
        if words[other]:
            add("script", f"{words[other]} word(s) in {other.title()} script, expected {script.title()}")
    elif words["latin"] and words["cyrillic"]:
        add("script", f"mixes Latin ({words['latin']}) and Cyrillic ({words['cyrillic']}) words")

    if (source[:1].isspace(), source[-1:].isspace()) != (target[:1].isspace(), target[-1:].isspace()):
        add("whitespace", "leading/trailing spaces differ from the source")

    src_end = source.rstrip()[-1:] if source.rstrip()[-1:] in END_PUNCTUATION else ""
    tgt_end = target.rstrip()[-1:] if target.rstrip()[-1:] in END_PUNCTUATION else ""
    if src_end != tgt_end:
        want = f"'{src_end}'" if src_end else "no final punctuation"
        add("punctuation", f"source ends with {want}, translation ends with "
                           f"{repr(tgt_end) if tgt_end else 'none'}")
    return issues


# --- whole-file checks ---------------------------------------------------------

def check(source: Catalog, target: Catalog, script=None, ignore=()) -> Report:
    """Compare two catalogs and return a Report.

    For a single PO file, pass the same catalog twice: the msgid of each entry
    is used as the source text.
    """
    unknown = set(ignore) - set(ALL_CHECKS)
    if unknown:
        raise ValueError(f"Unknown check(s): {', '.join(sorted(unknown))}")

    po_mode = source is target
    source_texts = target.sources if po_mode else source.entries

    issues = []
    translated = 0
    for key, src_text in source_texts.items():
        if key not in target.entries:
            issues.append(Issue(key, "missing", "key is missing from the translation", src_text))
            continue
        tgt_text = target.entries[key]
        if tgt_text.strip():
            translated += 1
        issues.extend(check_pair(key, src_text, tgt_text, script))
        if key in target.fuzzy:
            issues.append(Issue(key, "fuzzy", "marked as fuzzy, needs review", src_text, tgt_text))

    if not po_mode:
        for key in target.entries.keys() - source.entries.keys():
            issues.append(Issue(key, "extra", "key does not exist in the source",
                                target=target.entries[key]))

    issues = [i for i in issues if i.check not in ignore]
    order = {name: n for n, name in enumerate(ALL_CHECKS)}
    issues.sort(key=lambda i: (i.severity != ERROR, order[i.check], i.key))
    return Report(source.path, target.path, len(source_texts), translated, issues)
