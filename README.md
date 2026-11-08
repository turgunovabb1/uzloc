# uzloc 🇺🇿

**Uzbek localization toolkit** — a Python library and command-line tool for people who translate and build software in Uzbek.

![tests](https://img.shields.io/badge/tests-50%20passed-brightgreen) ![python](https://img.shields.io/badge/python-3.10%2B-blue) ![version](https://img.shields.io/badge/version-0.2.0-orange)

## ✨ Features

- **Latin ↔ Cyrillic transliteration** following the official Uzbek spelling rules
  - `е` → `ye` at the start of a word or after a vowel (`ер` → `yer`, `поезд` → `poyezd`)
  - `ц` → `ts` after a vowel, otherwise `s` (`милиция` → `militsiya`, `цирк` → `sirk`)
  - all apostrophe variants for `o'` / `g'` are understood (`'` `ʻ` `‘` `’`)
  - letter case is kept (`ШАҲАР` → `SHAHAR`, `Шаҳар` → `Shahar`)
- **Script detection** — tells if a text is Latin, Cyrillic or mixed
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
```

## 🐍 Python

```python
from uzloc.translit import transliterate, detect_script

transliterate("Ўзбекистон")   # "O'zbekiston"
transliterate("Toshkent")     # "Тошкент"
detect_script("Salom Салом")  # "mixed"
```

## 🧪 Tests

```bash
python3 -m pytest
```

## 🗺️ Roadmap

- [x] Latin ↔ Cyrillic transliteration
- [x] Command-line tool
- [ ] English · Uzbek · Russian IT glossary with search
- [ ] Translation file checker (JSON, PO, CSV): missing keys, broken placeholders, mixed scripts
- [ ] HTML / Markdown reports
- [ ] Web interface

---
Created by abb