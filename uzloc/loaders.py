"""Read translation files into a simple {key: text} dictionary.

Supported formats:
- JSON  (nested objects become dotted keys: {"menu": {"save": "Save"}} -> "menu.save")
- PO    (gettext: msgid -> msgstr; "#, fuzzy" entries are remembered)
- CSV   (first column = key, second column = text; a header row is skipped)
"""

import ast
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path


class LoadError(ValueError):
    """Raised when a translation file cannot be read."""


@dataclass
class Catalog:
    """All strings from one translation file."""
    path: str
    entries: dict                      # key -> translated text
    sources: dict = field(default_factory=dict)  # key -> source text (PO only)
    fuzzy: set = field(default_factory=set)      # keys marked "#, fuzzy" (PO only)

    def __len__(self):
        return len(self.entries)


def detect_format(path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in (".po", ".pot"):
        return "po"
    if suffix == ".csv":
        return "csv"
    raise LoadError(f"Unsupported file type '{suffix}' (use .json, .po or .csv)")


def load(path, fmt=None) -> Catalog:
    """Load any supported translation file."""
    path = Path(path)
    if not path.exists():
        raise LoadError(f"File not found: {path}")
    fmt = fmt or detect_format(path)
    text = path.read_text(encoding="utf-8-sig")
    loader = {"json": load_json, "po": load_po, "csv": load_csv}[fmt]
    return loader(text, str(path))


# --- JSON --------------------------------------------------------------------

def flatten(data, prefix="") -> dict:
    """Turn nested dicts/lists into {"a.b.0": value}."""
    flat = {}
    if isinstance(data, dict):
        items = data.items()
    elif isinstance(data, list):
        items = ((str(i), v) for i, v in enumerate(data))
    else:
        return {prefix: "" if data is None else str(data)}
    for key, value in items:
        full = f"{prefix}.{key}" if prefix else str(key)
        flat.update(flatten(value, full))
    return flat


def load_json(text, path="<json>") -> Catalog:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise LoadError(f"{path}: invalid JSON ({err.msg} at line {err.lineno})") from None
    if not isinstance(data, dict):
        raise LoadError(f"{path}: the top level must be an object {{...}}")
    return Catalog(path, flatten(data))


# --- PO ----------------------------------------------------------------------

def _unquote(chunk: str) -> str:
    """'"Hello\\n"' -> 'Hello\n' using Python's own string rules."""
    try:
        return ast.literal_eval(chunk)
    except (ValueError, SyntaxError):
        raise LoadError(f"bad quoted string: {chunk[:40]}") from None


def load_po(text, path="<po>") -> Catalog:
    entries, sources, fuzzy = {}, {}, set()
    current = {}
    field_name = None
    is_fuzzy = False

    def finish():
        nonlocal current, is_fuzzy
        msgid = current.get("msgid")
        if msgid:  # the header entry has an empty msgid and is skipped
            key = current.get("msgctxt", "") + "\x04" + msgid if "msgctxt" in current else msgid
            entries[key] = current.get("msgstr", current.get("msgstr[0]", ""))
            sources[key] = msgid
            if is_fuzzy:
                fuzzy.add(key)
        current, is_fuzzy = {}, False

    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            finish()
            field_name = None
            continue
        if line.startswith("#,") and "fuzzy" in line:
            is_fuzzy = True
            continue
        if line.startswith("#"):
            continue
        if line.startswith('"'):
            if field_name is None:
                raise LoadError(f"{path}:{number}: text without msgid/msgstr")
            current[field_name] += _unquote(line)
            continue
        name, _, rest = line.partition(" ")
        if name == "msgid" and "msgid" in current:
            finish()  # entries not separated by a blank line
        if name not in ("msgctxt", "msgid", "msgid_plural", "msgstr") and not name.startswith("msgstr["):
            raise LoadError(f"{path}:{number}: unknown keyword '{name}'")
        field_name = name
        current[name] = _unquote(rest.strip())
    finish()
    return Catalog(path, entries, sources, fuzzy)


# --- CSV ---------------------------------------------------------------------

HEADER_WORDS = {"key", "id", "string", "name", "source", "text", "value"}


def load_csv(text, path="<csv>") -> Catalog:
    rows = [row for row in csv.reader(text.splitlines()) if any(cell.strip() for cell in row)]
    if rows and rows[0] and rows[0][0].strip().lower() in HEADER_WORDS:
        rows = rows[1:]
    entries = {}
    for number, row in enumerate(rows, start=1):
        if len(row) < 2:
            raise LoadError(f"{path}: row {number} needs two columns (key, text)")
        entries[row[0].strip()] = row[1]
    return Catalog(path, entries)
