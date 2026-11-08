# uzloc 🇺🇿

**Uzbek localization toolkit** — a Python library for people who translate and build software in Uzbek.

![tests](https://img.shields.io/badge/tests-42%20passed-brightgreen) ![python](https://img.shields.io/badge/python-3.10%2B-blue)

## ✨ Features

- **Latin ↔ Cyrillic transliteration** following the official Uzbek spelling rules
  - `е` → `ye` at the start of a word or after a vowel (`ер` → `yer`, `поезд` → `poyezd`)
  - `ц` → `ts` after a vowel, otherwise `s` (`милиция` → `militsiya`, `цирк` → `sirk`)
  - all apostrophe variants for `o'` / `g'` are understood (`'` `ʻ` `‘` `’`)
  - letter case is kept (`ШАҲАР` → `SHAHAR`, `Шаҳар` → `Shahar`)
- **Script detection** — tells if a text is Latin, Cyrillic or mixed

## 🚀 Quick start

```bash
git clone https://github.com/turgunovabb1/uzloc.git
cd uzloc
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
```

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
- [ ] Command-line tool (`uzloc translit file.txt`)
- [ ] English · Uzbek · Russian IT glossary with search
- [ ] Translation file checker (JSON, PO, CSV): missing keys, broken placeholders, mixed scripts
- [ ] HTML / Markdown reports
- [ ] Web interface

---
Created by abb
