import pytest

from uzloc.cli import main
from uzloc.glossary import (
    EXACT,
    GlossaryError,
    Term,
    categories,
    load_glossary,
    lookup,
    search,
)


@pytest.fixture(scope="module")
def terms():
    return load_glossary()


# --- loading -----------------------------------------------------------------

def test_builtin_glossary_loads(terms):
    assert len(terms) >= 150
    assert all(isinstance(t, Term) for t in terms)


def test_every_term_has_all_three_languages(terms):
    for t in terms:
        assert t.en and t.uz and t.ru, t


def test_no_duplicate_english_terms(terms):
    english = [t.en.lower() for t in terms]
    assert len(english) == len(set(english))


def test_custom_glossary_file(tmp_path):
    path = tmp_path / "mine.csv"
    path.write_text("en,uz,ru,category\nhello,salom,привет,greetings\n", encoding="utf-8")
    terms = load_glossary(path)
    assert terms == [Term("hello", "salom", "привет", "greetings")]


def test_category_defaults_to_general(tmp_path):
    path = tmp_path / "mine.csv"
    path.write_text("en,uz,ru\nhello,salom,привет\n", encoding="utf-8")
    assert load_glossary(path)[0].category == "general"


def test_missing_column_is_an_error(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("en,uz\nhello,salom\n", encoding="utf-8")
    with pytest.raises(GlossaryError, match="ru"):
        load_glossary(path)


def test_empty_glossary_is_an_error(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("en,uz,ru\n", encoding="utf-8")
    with pytest.raises(GlossaryError):
        load_glossary(path)


# --- search ------------------------------------------------------------------

def test_search_english(terms):
    best = search("password", terms)[0]
    assert best.term.uz == "parol"
    assert best.score == EXACT


def test_search_is_case_insensitive(terms):
    assert search("PASSWORD", terms)[0].term.en == "password"


def test_search_uzbek_latin(terms):
    assert search("sozlamalar", terms)[0].term.en == "settings"


def test_search_uzbek_any_apostrophe(terms):
    for spelling in ("o'chirish", "o‘chirish", "oʻchirish", "o’chirish"):
        assert search(spelling, terms, lang="uz")[0].term.en == "delete", spelling


def test_search_uzbek_cyrillic_matches_latin_entry(terms):
    assert search("созламалар", terms, lang="uz")[0].term.en == "settings"


def test_search_russian(terms):
    assert search("настройки", terms)[0].term.en == "settings"


def test_exact_match_ranks_first(terms):
    results = search("file", terms)
    assert results[0].term.en == "file"
    assert results[0].score > results[-1].score or len(results) == 1


def test_search_finds_multi_word_terms(terms):
    found = [m.term.en for m in search("machine", terms)]
    assert "machine learning" in found
    assert "machine translation" in found


def test_filter_by_category(terms):
    results = search("a", terms, category="git", limit=None)
    assert results and all(m.term.category == "git" for m in results)


def test_limit(terms):
    assert len(search("a", terms, limit=3)) == 3


def test_fuzzy_suggests_close_spelling(terms):
    results = search("pasword", terms)
    assert results and results[0].term.en == "password"
    assert results[0].score < 40


def test_fuzzy_can_be_turned_off(terms):
    assert search("pasword", terms, fuzzy=False) == []


def test_nothing_found(terms):
    assert search("xyzzyqq", terms) == []


def test_empty_query(terms):
    assert search("   ", terms) == []


def test_bad_language(terms):
    with pytest.raises(ValueError):
        search("file", terms, lang="de")


def test_lookup(terms):
    assert lookup("save", terms).uz == "saqlash"
    assert lookup("sav", terms) is None


def test_categories(terms):
    counts = categories(terms)
    assert "ui" in counts and "git" in counts
    assert sum(counts.values()) == len(terms)


# --- command line ------------------------------------------------------------

def test_cli_glossary_table(capsys):
    assert main(["glossary", "password"]) == 0
    out = capsys.readouterr().out
    assert "parol" in out and "пароль" in out and "English" in out


def test_cli_glossary_json(capsys):
    assert main(["glossary", "save", "--exact", "--format", "json"]) == 0
    assert '"uz": "saqlash"' in capsys.readouterr().out


def test_cli_glossary_csv(capsys):
    assert main(["glossary", "save", "--exact", "--format", "csv"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0] == "en,uz,ru,category"
    assert lines[1].startswith("save,saqlash,")


def test_cli_glossary_uzbek(capsys):
    assert main(["glossary", "sozlamalar", "--lang", "uz"]) == 0
    assert "settings" in capsys.readouterr().out


def test_cli_glossary_did_you_mean(capsys):
    assert main(["glossary", "pasword"]) == 0
    captured = capsys.readouterr()
    assert "Did you mean" in captured.err
    assert "password" in captured.out


def test_cli_glossary_not_found(capsys):
    assert main(["glossary", "xyzzyqq"]) == 1
    assert "No terms found" in capsys.readouterr().err


def test_cli_glossary_categories(capsys):
    assert main(["glossary", "--categories"]) == 0
    assert "ui" in capsys.readouterr().out


def test_cli_glossary_needs_a_query(capsys):
    assert main(["glossary"]) == 1


def test_cli_custom_glossary_file(tmp_path, capsys):
    path = tmp_path / "mine.csv"
    path.write_text("en,uz,ru,category\nhello,salom,привет,greetings\n", encoding="utf-8")
    assert main(["glossary", "salom", "--glossary-file", str(path)]) == 0
    assert "hello" in capsys.readouterr().out


def test_cli_missing_glossary_file(capsys):
    assert main(["glossary", "x", "--glossary-file", "no_such_file.csv"]) == 1
    assert "Error" in capsys.readouterr().err
