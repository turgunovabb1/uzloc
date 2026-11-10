# uzloc 🇺🇿

**Uzbek localization toolkit** — a Python library and command-line tool for people who translate and build software in Uzbek.

![tests](https://img.shields.io/badge/tests-84%20passed-brightgreen) ![python](https://img.shields.io/badge/python-3.10%2B-blue) ![version](https://img.shields.io/badge/version-0.3.0-orange)

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
```

Example:

```
$ uzloc glossary settings
English   O'zbekcha   Русский
--------  ----------  ---------
settings  sozlamalar  настройки
```

## 🐍 Python

```python
from uzloc.translit import transliterate, detect_script

transliterate("Ўзбекистон")   # "O'zbekiston"
transliterate("Toshkent")     # "Тошкент"
detect_script("Salom Салом")  # "mixed"

from uzloc.glossary import search, lookup

search("sozlamalar")[0].term.en   # "settings"
lookup("save").uz                 # "saqlash"
```

## 🧪 Tests

```bash
python3 -m pytest
```

## 🗺️ Roadmap

- [x] Latin ↔ Cyrillic transliteration
- [x] Command-line tool
- [x] English · Uzbek · Russian IT glossary with search
- [ ] Translation file checker (JSON, PO, CSV): missing keys, broken placeholders, mixed scripts
- [ ] HTML / Markdown reports
- [ ] Web interface

---
Created by abb