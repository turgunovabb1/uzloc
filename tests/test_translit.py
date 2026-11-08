import pytest

from uzloc.translit import (
    cyrillic_to_latin,
    detect_script,
    latin_to_cyrillic,
    normalize_apostrophes,
    transliterate,
)


@pytest.mark.parametrize(
    "cyrillic, latin",
    [
        ("Тошкент", "Toshkent"),
        ("Ўзбекистон", "O'zbekiston"),
        ("ғалаба", "g'alaba"),
        ("шаҳар", "shahar"),
        ("Шаҳар", "Shahar"),
        ("ШАҲАР", "SHAHAR"),
        ("мактаб", "maktab"),
        ("ер", "yer"),
        ("поезд", "poyezd"),
        ("съезд", "s'yezd"),
        ("цирк", "sirk"),
        ("милиция", "militsiya"),
        ("экран", "ekran"),
        ("ёз", "yoz"),
        ("юлдуз", "yulduz"),
        ("Чой ичамиз.", "Choy ichamiz."),
        ("маъно", "ma'no"),
    ],
)
def test_cyrillic_to_latin(cyrillic, latin):
    assert cyrillic_to_latin(cyrillic) == latin


@pytest.mark.parametrize(
    "latin, cyrillic",
    [
        ("Toshkent", "Тошкент"),
        ("O'zbekiston", "Ўзбекистон"),
        ("O‘zbekiston", "Ўзбекистон"),
        ("g'alaba", "ғалаба"),
        ("SHAHAR", "ШАҲАР"),
        ("ekran", "экран"),
        ("yer", "ер"),
        ("poyezd", "поезд"),
        ("ma'no", "маъно"),
        ("choy", "чой"),
        ("yoz", "ёз"),
        ("Yangilanish holati", "Янгиланиш ҳолати"),
    ],
)
def test_latin_to_cyrillic(latin, cyrillic):
    assert latin_to_cyrillic(latin) == cyrillic


@pytest.mark.parametrize(
    "word",
    ["Toshkent", "O'zbekiston", "shahar", "yulduz", "ma'lumotlar bazasi", "Sozlamalar"],
)
def test_round_trip(word):
    assert cyrillic_to_latin(latin_to_cyrillic(word)) == word


def test_normalize_apostrophes():
    assert normalize_apostrophes("Oʻzbek g’alaba") == "O'zbek g'alaba"


@pytest.mark.parametrize(
    "text, script",
    [
        ("Salom", "latin"),
        ("Салом", "cyrillic"),
        ("Salom Салом", "mixed"),
        ("123 !?", "unknown"),
    ],
)
def test_detect_script(text, script):
    assert detect_script(text) == script


def test_transliterate_auto():
    assert transliterate("Салом дунё") == "Salom dunyo"
    assert transliterate("Salom dunyo") == "Салом дунё"
    assert transliterate("123") == "123"


def test_keeps_numbers_and_punctuation():
    assert latin_to_cyrillic("Version 2.0, 100%!") == "Версион 2.0, 100%!"
