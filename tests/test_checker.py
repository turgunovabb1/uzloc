import json
from collections import Counter
from pathlib import Path

import pytest

from uzloc.checker import (
    ALL_CHECKS,
    check,
    check_pair,
    placeholders,
    printf_order,
    tags,
    word_scripts,
)
from uzloc.cli import main
from uzloc.loaders import Catalog, load

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def checks(source, target, script=None):
    """Names of the checks that fail for one pair."""
    return [i.check for i in check_pair("k", source, target, script)]


# --- helpers -----------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("Hello {name}", {"{name}": 1}),
    ("{0} of {1}", {"{0}": 1, "{1}": 1}),
    ("Hi {{ user }}", {"{{user}}": 1}),
    ("%s and %d and %.2f", {"%s": 1, "%d": 1, "%.2f": 1}),
    ("%1$s %2$d", {"%1$s": 1, "%2$d": 1}),
    ("%(count)d files", {"%(count)d": 1}),
    ("Hello $USER$", {"$USER$": 1}),
    ("50% off", {}),
    ("100 % sure", {}),
])
def test_placeholders(text, expected):
    assert placeholders(text) == Counter(expected)


def test_printf_order():
    assert printf_order("Found %d files in %s") == ["d", "s"]
    assert printf_order("%1$s %2$d") == []


def test_tags():
    assert tags('Click <a href="x">here</a> or <br/>') == Counter({"<a>": 1, "</a>": 1, "<br>": 1})


def test_word_scripts_ignores_code_and_acronyms():
    counts = word_scripts("Салом {name}, open https://x.com — USB, Wi-Fi, iOS")
    assert counts["cyrillic"] == 1
    assert counts["latin"] == 1  # only "open"


# --- single pair -------------------------------------------------------------

def test_good_translation_has_no_issues():
    assert checks("Welcome, {name}!", "Xush kelibsiz, {name}!") == []


def test_empty():
    assert checks("Save", "  ") == ["empty"]


def test_untranslated():
    assert "untranslated" in checks("The request timed out.", "The request timed out.")


def test_short_identical_strings_are_ok():
    # "OK", "USB", "{0}" are often the same in every language.
    assert checks("OK", "OK") == []
    assert checks("{0}", "{0}") == []


def test_renamed_placeholder():
    issues = check_pair("k", "Hi {name}", "Salom {ism}")
    assert [i.check for i in issues] == ["placeholders"]
    assert "missing {name}" in issues[0].message
    assert "unexpected {ism}" in issues[0].message


def test_missing_placeholder():
    assert checks("%d files", "fayllar") == ["placeholders"]


def test_duplicated_placeholder():
    assert checks("{n} item", "{n} ta {n}") == ["placeholders"]


def test_printf_order_swapped():
    issues = check_pair("k", "Found %d files in %s.", "%s ichida %d ta fayl topildi.")
    assert [i.check for i in issues] == ["placeholders"]
    assert "order" in issues[0].message


def test_numbered_placeholders_may_move():
    assert checks("Found %1$d files in %2$s.", "%2$s ichida %1$d ta fayl topildi.") == []


def test_named_placeholders_may_move():
    assert checks("{a} of {b}", "{b} dan {a}") == []


def test_missing_tags():
    assert checks("Delete <b>all</b>?", "Hammasini o'chirasizmi?") == ["tags"]


def test_mixed_script():
    assert checks("Search history", "Qidiruv тарихи") == ["script"]


def test_expected_script():
    assert checks("Settings", "Созламалар", script="latin") == ["script"]
    assert checks("Settings", "Sozlamalar", script="latin") == []
    assert checks("Settings", "Sozlamalar", script="cyrillic") == ["script"]


def test_urls_do_not_count_as_latin_words():
    assert checks("Visit https://uz.example.com", "Кўринг https://uz.example.com",
                  script="cyrillic") == []


def test_whitespace():
    assert checks("Name: ", "Ism:") == ["whitespace"]


def test_punctuation():
    assert checks("Saved.", "Saqlandi") == ["punctuation"]
    assert checks("Saved", "Saqlandi!") == ["punctuation"]
    assert checks("Really?", "Rostdanmi?") == []


# --- whole files -------------------------------------------------------------

def cat(entries, path="x.json", **kw):
    return Catalog(path, entries, **kw)


def test_missing_and_extra_keys():
    report = check(cat({"a": "Open", "b": "Close"}), cat({"a": "Ochish", "c": "Eski"}))
    found = {(i.check, i.key) for i in report.issues}
    assert ("missing", "b") in found
    assert ("extra", "c") in found


def test_progress():
    report = check(cat({"a": "Open", "b": "Close", "c": "Save", "d": "Copy"}),
                   cat({"a": "Ochish", "b": "", "c": "Saqlash"}))
    assert report.total == 4
    assert report.translated == 2
    assert report.progress == 50.0


def test_errors_come_before_warnings():
    report = check(cat({"a": "Hi.", "b": "{x}"}), cat({"a": "Salom", "b": "y"}))
    assert [i.severity for i in report.issues] == ["error", "warning"]


def test_ignore_checks():
    report = check(cat({"a": "Hi."}), cat({"a": "Salom"}), ignore=["punctuation"])
    assert report.issues == []


def test_unknown_ignore_name():
    with pytest.raises(ValueError, match="Unknown check"):
        check(cat({}), cat({}), ignore=["spelling"])


def test_po_single_file_mode():
    po = Catalog("uz.po", {"Open": "Ochish", "Close": ""},
                 sources={"Open": "Open", "Close": "Close"}, fuzzy={"Open"})
    report = check(po, po)
    assert {i.check for i in report.issues} == {"empty", "fuzzy"}
    assert report.total == 2


def test_report_to_dict():
    data = check(cat({"a": "Hi {n}"}), cat({"a": "Salom"})).to_dict()
    assert data["errors"] == 1
    assert data["issues"][0]["check"] == "placeholders"
    assert data["issues"][0]["severity"] == "error"


def test_every_check_has_a_severity():
    assert set(ALL_CHECKS) == {
        "missing", "extra", "empty", "untranslated", "placeholders",
        "tags", "script", "whitespace", "punctuation", "fuzzy",
    }


def test_example_files():
    report = check(load(EXAMPLES / "en.json"), load(EXAMPLES / "uz.json"))
    found = {(i.check, i.key) for i in report.issues}
    assert ("placeholders", "app.welcome") in found
    assert ("placeholders", "app.files_found") in found
    assert ("tags", "app.delete_confirm") in found
    assert ("untranslated", "errors.timeout") in found
    assert ("extra", "old_key") in found


# --- command line ------------------------------------------------------------

def test_cli_check_finds_problems(capsys):
    code = main(["check", str(EXAMPLES / "en.json"), str(EXAMPLES / "uz.json")])
    out = capsys.readouterr().out
    assert code == 1
    assert "[placeholders] app.welcome" in out
    assert "error(s)" in out


def test_cli_check_clean_files(tmp_path, capsys):
    (tmp_path / "en.json").write_text('{"save": "Save"}', encoding="utf-8")
    (tmp_path / "uz.json").write_text('{"save": "Saqlash"}', encoding="utf-8")
    assert main(["check", str(tmp_path / "en.json"), str(tmp_path / "uz.json")]) == 0
    assert "No problems found" in capsys.readouterr().out


def test_cli_warnings_pass_unless_strict(tmp_path):
    (tmp_path / "en.json").write_text('{"a": "Saved."}', encoding="utf-8")
    (tmp_path / "uz.json").write_text('{"a": "Saqlandi"}', encoding="utf-8")
    files = [str(tmp_path / "en.json"), str(tmp_path / "uz.json")]
    assert main(["check", *files]) == 0
    assert main(["check", *files, "--strict"]) == 1


def test_cli_json_output(capsys):
    main(["check", str(EXAMPLES / "en.json"), str(EXAMPLES / "uz.json"), "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["total"] == 9
    assert data["errors"] >= 2


def test_cli_single_po(capsys):
    code = main(["check", str(EXAMPLES / "uz.po"), "--script", "latin"])
    out = capsys.readouterr().out
    assert code == 1
    assert "[empty] Copy link" in out
    assert "[script] Search history" in out
    assert "[fuzzy] Close window" in out


def test_cli_single_json_is_an_error(capsys):
    assert main(["check", str(EXAMPLES / "en.json")]) == 2
    assert "must be a .po file" in capsys.readouterr().err


def test_cli_errors_only(capsys):
    main(["check", str(EXAMPLES / "en.json"), str(EXAMPLES / "uz.json"), "--errors-only"])
    out = capsys.readouterr().out
    assert "[placeholders]" in out
    assert "[untranslated]" not in out


def test_cli_ignore(capsys):
    main(["check", str(EXAMPLES / "en.json"), str(EXAMPLES / "uz.json"),
          "--ignore", "placeholders,tags"])
    out = capsys.readouterr().out
    assert "[placeholders]" not in out and "[tags]" not in out


def test_cli_bad_file(capsys):
    assert main(["check", "missing.json", "also_missing.json"]) == 2
    assert "Error" in capsys.readouterr().err
