# uzloc 🇺🇿

**Uzbek localization toolkit** — a Python library and command-line tool for people who translate and build software in Uzbek.

![tests](https://img.shields.io/badge/tests-151%20passed-brightgreen) ![python](https://img.shields.io/badge/python-3.10%2B-blue) ![version](https://img.shields.io/badge/version-0.4.0-orange)

## ✨ Features

- **Latin ↔ Cyrillic transliteration** following the official Uzbek spelling rules
  - `е` → `ye` at the start of a word or after a vowel (`ер` → `yer`, `поезд` → `poyezd`)
  - `ц` → `ts` after a vowel, otherwise `s` (`милиция` → `militsiya`, `цирк` → `sirk`)
  - all apostrophe variants for `o'` / `g'` are understood (`'` `ʻ` `‘` `’`)
  - letter case is kept (`ШАҲАР` → `SHAHAR`, `Шаҳар` → `Shahar`)
- **Script detection** — tells if a text is Latin, Cyrillic or mixed
- **English · Uzbek · Russian IT glossary** — 168 software and UI terms in 11 categories
  - search in any of the three languages, Uzbek in Latin *or* Cyrillic
  - "Did you mean…?" suggestions for typos (`pasword` → `password`)
  - output as a table, JSON or CSV, or load your own glossary file
- **Translation file checker** for JSON, PO and CSV — finds what a reviewer would miss:
  - missing, extra and empty keys, and strings left in English
  - broken placeholders (`{name}`, `%s`, `%(n)d`, `{{x}}`) and swapped printf order
  - missing HTML tags, mixed Latin/Cyrillic text, wrong script, spacing and punctuation
  - fuzzy PO entries, translation progress in %, JSON output and CI-friendly exit codes
- **Command-line tool** — convert words, whole files or piped text

## 🚀 Install

```bash
git clone https://github.com/turgunovabb1/uzloc.git
cd uzloc
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 💻 Command line

```bash
uzloc translit "Salom dunyo"                  # Салом дунё
uzloc translit "Ўзбекистон"                   # O'zbekiston
uzloc translit "Toshkent" --to latin          # force the target script
uzloc translit -f book.txt -o book_latin.txt  # convert a whole file
echo "Тошкент" | uzloc translit               # works with pipes
uzloc detect "Salom Салом"                    # mixed

uzloc glossary password                       # parol · пароль
uzloc glossary "ўчириш" --lang uz             # delete · o'chirish · удалить
uzloc glossary save --exact --format json     # machine-readable output
uzloc glossary -c git a -n 20                 # every Git term
uzloc glossary --categories                   # list categories
uzloc glossary salom --glossary-file my.csv   # use your own glossary

uzloc check en.json uz.json                   # compare a translation with its source
uzloc check uz.po --script latin              # check one PO file, expect Latin script
uzloc check en.json uz.json --format json     # machine-readable report
uzloc check en.json uz.json --ignore punctuation --strict
```

Example:

```
$ uzloc glossary settings
English   O'zbekcha   Русский
--------  ----------  ---------
settings  sozlamalar  настройки
```

## 🔎 Checking a translation

Try it on the files in [`examples/`](examples):

```
$ uzloc check examples/en.json examples/uz.json
Source:      examples/en.json
Translation: examples/uz.json
Progress:    9/9 keys translated (100.0%)

✗ [placeholders] app.welcome: missing {name}; unexpected {ism}
    source: Welcome, {name}!
    target: Xush kelibsiz, {ism}!
✗ [placeholders] app.files_found: printf placeholders changed order (use numbered ones like %1$s, %2$d to reorder)
    source: Found %d files in %s.
    target: %s ichida %d ta fayl topildi.
✗ [tags] app.delete_confirm: missing </b>, <b>
...
3 error(s), 3 warning(s)
```

| Check | Level | What it finds |
|---|---|---|
| `missing` | error | key is in the source but not in the translation |
| `empty` | error | translation is an empty string |
| `placeholders` | error | `{name}`, `%s`, `%(n)d` … differ, or printf order changed |
| `tags` | error | HTML tags such as `<b>` or `</a>` differ |
| `extra` | warning | key exists only in the translation |
| `untranslated` | warning | translation is identical to the source |
| `script` | warning | Latin and Cyrillic mixed, or the wrong script for `--script` |
| `whitespace` | warning | leading/trailing spaces differ |
| `punctuation` | warning | final `. ! ? :` differs |
| `fuzzy` | warning | PO entry marked `#, fuzzy` |

Exit codes: `0` no errors · `1` errors found (or warnings with `--strict`) · `2` files could not be read.
This makes `uzloc check` easy to use in CI to stop broken translations from being merged.

## 🐍 Python

```python
from uzloc.translit import transliterate, detect_script

transliterate("Ўзбекистон")   # "O'zbekiston"
transliterate("Toshkent")     # "Тошкент"
detect_script("Salom Салом")  # "mixed"

from uzloc.glossary import search, lookup

search("sozlamalar")[0].term.en   # "settings"
lookup("save").uz                 # "saqlash"

from uzloc.loaders import load
from uzloc.checker import check

report = check(load("en.json"), load("uz.json"))
report.progress                   # 100.0
[i.message for i in report.errors]
```

## 🧪 Tests

```bash
python3 -m pytest
```

## 🗺️ Roadmap

- [x] Latin ↔ Cyrillic transliteration
- [x] Command-line tool
- [x] English · Uzbek · Russian IT glossary with search
- [x] Translation file checker (JSON, PO, CSV): missing keys, broken placeholders, mixed scripts
- [ ] HTML / Markdown reports
- [ ] Web interface

---
Created by abb