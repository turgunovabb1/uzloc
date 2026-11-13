import pytest

from uzloc.loaders import LoadError, detect_format, flatten, load, load_csv, load_json, load_po


# --- JSON --------------------------------------------------------------------

def test_flatten_nested():
    data = {"menu": {"file": {"open": "Open"}, "save": "Save"}, "title": "App"}
    assert flatten(data) == {"menu.file.open": "Open", "menu.save": "Save", "title": "App"}


def test_flatten_lists_and_numbers():
    assert flatten({"days": ["Mon", "Tue"], "n": 3, "x": None}) == {
        "days.0": "Mon", "days.1": "Tue", "n": "3", "x": "",
    }


def test_load_json():
    cat = load_json('{"a": {"b": "Hello"}}', "en.json")
    assert cat.entries == {"a.b": "Hello"}
    assert cat.path == "en.json"
    assert len(cat) == 1


def test_invalid_json():
    with pytest.raises(LoadError, match="invalid JSON"):
        load_json('{"a": }')


def test_json_must_be_object():
    with pytest.raises(LoadError, match="object"):
        load_json('["a", "b"]')


# --- PO ----------------------------------------------------------------------

PO = r'''
# comment
msgid ""
msgstr ""
"Language: uz\n"

#: main.c:10
msgid "Open file"
msgstr "Faylni ochish"

#, fuzzy
msgid "Close"
msgstr "Yopish"

msgid ""
"Long text "
"on two lines"
msgstr "Uzun matn "
"ikki qatorda"

msgctxt "menu"
msgid "Open"
msgstr "Ochish"

msgid "Line\nbreak"
msgstr "Qator\nko'chishi"
msgid "No blank line before"
msgstr "Bo'sh qatorsiz"
'''


def test_load_po_entries():
    cat = load_po(PO)
    assert cat.entries["Open file"] == "Faylni ochish"
    assert cat.sources["Open file"] == "Open file"
    assert "" not in cat.entries  # header is skipped


def test_po_multiline_strings():
    cat = load_po(PO)
    assert cat.entries["Long text on two lines"] == "Uzun matn ikki qatorda"


def test_po_escapes():
    assert load_po(PO).entries["Line\nbreak"] == "Qator\nko'chishi"


def test_po_fuzzy():
    cat = load_po(PO)
    assert cat.fuzzy == {"Close"}


def test_po_context_gives_separate_key():
    cat = load_po(PO)
    assert cat.entries["menu\x04Open"] == "Ochish"
    assert cat.sources["menu\x04Open"] == "Open"


def test_po_entries_without_blank_line():
    assert load_po(PO).entries["No blank line before"] == "Bo'sh qatorsiz"


def test_po_plural_uses_first_form():
    text = 'msgid "file"\nmsgid_plural "files"\nmsgstr[0] "fayl"\n'
    assert load_po(text).entries == {"file": "fayl"}


def test_po_unknown_keyword():
    with pytest.raises(LoadError, match="unknown keyword"):
        load_po('msgid "a"\nmsgfoo "b"\n')


def test_po_orphan_string():
    with pytest.raises(LoadError, match="without msgid"):
        load_po('"hello"\n')


# --- CSV ---------------------------------------------------------------------

def test_load_csv_with_header():
    cat = load_csv("key,text\nsave,Saqlash\nopen,\"Ochish, tez\"\n")
    assert cat.entries == {"save": "Saqlash", "open": "Ochish, tez"}


def test_load_csv_without_header():
    assert load_csv("save,Saqlash\n").entries == {"save": "Saqlash"}


def test_csv_needs_two_columns():
    with pytest.raises(LoadError, match="two columns"):
        load_csv("save\n")


# --- files -------------------------------------------------------------------

def test_detect_format():
    assert detect_format("uz.json") == "json"
    assert detect_format("uz.PO") == "po"
    assert detect_format("uz.csv") == "csv"
    with pytest.raises(LoadError, match="Unsupported"):
        detect_format("uz.xlsx")


def test_load_from_disk(tmp_path):
    path = tmp_path / "uz.json"
    path.write_text('{"save": "Saqlash"}', encoding="utf-8")
    assert load(path).entries == {"save": "Saqlash"}


def test_load_utf8_bom(tmp_path):
    path = tmp_path / "uz.json"
    path.write_bytes('﻿{"a": "b"}'.encode("utf-8"))
    assert load(path).entries == {"a": "b"}


def test_load_missing_file(tmp_path):
    with pytest.raises(LoadError, match="not found"):
        load(tmp_path / "nope.json")
