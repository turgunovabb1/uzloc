"""Uzbek Latin <-> Cyrillic transliteration.

Follows the official Uzbek Latin alphabet (1995) rules:
- Cyrillic "е" becomes "ye" at the start of a word or after a vowel, otherwise "e".
- Cyrillic "ц" becomes "ts" after a vowel, otherwise "s".
- Latin "e" becomes "э" at the start of a word, otherwise "е".
- The apostrophe (tutuq belgisi) after a letter becomes "ъ".
"""

# Every apostrophe-like character people type for o' and g'.
APOSTROPHES = "'ʻʼ‘’`´"

CYR_VOWELS = set("аеёиоуўэюяАЕЁИОУЎЭЮЯ")
LAT_VOWELS = set("aeiouAEIOU")

CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ё": "yo", "ж": "j",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "x", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ь": "", "ы": "i",
    "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}

# Order matters: longer (two-letter) sequences are checked first.
LAT_DIGRAPHS = {
    "o'": "ў", "g'": "ғ", "sh": "ш", "ch": "ч",
    "yo": "ё", "yu": "ю", "ya": "я", "ye": "е",
}

LAT_TO_CYR = {
    "a": "а", "b": "б", "d": "д", "f": "ф", "g": "г", "h": "ҳ", "i": "и",
    "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п",
    "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "x": "х",
    "y": "й", "z": "з", "c": "с", "w": "в",
}


def normalize_apostrophes(text: str) -> str:
    """Replace every apostrophe variant (ʻ ‘ ’ ` ...) with a plain ' ."""
    for ch in APOSTROPHES[1:]:
        text = text.replace(ch, "'")
    return text


def _match_case(source: str, target: str, next_char: str = "", prev_char: str = "") -> str:
    """Give `target` the same letter case as `source`.

    For multi-letter results (Ш -> SH or Sh) we look at the neighbours:
    if the word is written in capitals, the whole result is capitalised.
    """
    if not target or not source[0].isupper():
        return target
    if len(target) == 1:
        return target.upper()
    neighbour_upper = (next_char.isalpha() and next_char.isupper()) or (
        not next_char.isalpha() and prev_char.isalpha() and prev_char.isupper()
    )
    return target.upper() if neighbour_upper else target[0].upper() + target[1:]


def cyrillic_to_latin(text: str) -> str:
    """Convert Uzbek Cyrillic text to the official Latin alphabet."""
    result = []
    for i, ch in enumerate(text):
        low = ch.lower()
        prev = text[i - 1] if i > 0 else ""
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if low == "е":
            word_start = not prev.isalpha()
            after_vowel = prev in CYR_VOWELS or prev.lower() in ("ъ", "ь")
            latin = "ye" if (word_start or after_vowel) else "e"
        elif low == "ц":
            latin = "ts" if prev in CYR_VOWELS else "s"
        elif low in CYR_TO_LAT:
            latin = CYR_TO_LAT[low]
        else:
            result.append(ch)
            continue

        result.append(_match_case(ch, latin, nxt, prev))
    return "".join(result)


def latin_to_cyrillic(text: str) -> str:
    """Convert Uzbek Latin text to Cyrillic."""
    text = normalize_apostrophes(text)
    result = []
    i = 0
    while i < len(text):
        ch = text[i]
        pair = text[i:i + 2].lower()
        prev = text[i - 1] if i > 0 else ""

        if pair in LAT_DIGRAPHS:
            result.append(_match_case(ch, LAT_DIGRAPHS[pair]))
            i += 2
            continue

        low = ch.lower()
        if low == "e":
            cyr = "э" if not prev.isalpha() else "е"
        elif ch == "'":
            # Tutuq belgisi between letters: ma'no -> маъно
            cyr = "ъ" if prev.isalpha() else "'"
        elif low in LAT_TO_CYR:
            cyr = LAT_TO_CYR[low]
        else:
            result.append(ch)
            i += 1
            continue

        result.append(_match_case(ch, cyr))
        i += 1
    return "".join(result)


def detect_script(text: str) -> str:
    """Return 'latin', 'cyrillic', 'mixed' or 'unknown' for the given text."""
    latin = sum(1 for ch in text if ch.isalpha() and ch.isascii())
    cyrillic = sum(1 for ch in text if "Ѐ" <= ch <= "ӿ")
    if latin and cyrillic:
        return "mixed"
    if latin:
        return "latin"
    if cyrillic:
        return "cyrillic"
    return "unknown"


def transliterate(text: str) -> str:
    """Detect the script automatically and convert to the other one."""
    script = detect_script(text)
    if script == "cyrillic":
        return cyrillic_to_latin(text)
    if script == "latin":
        return latin_to_cyrillic(text)
    return text
