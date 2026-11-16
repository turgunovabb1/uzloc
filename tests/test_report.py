from pathlib import Path

from uzloc.checker import check
from uzloc.cli import main
from uzloc.loaders import Catalog, load
from uzloc.report import render_html, render_markdown

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def cat(entries, path="x.json"):
    return Catalog(path, entries)


def example_report():
    return check(load(EXAMPLES / "en.json"), load(EXAMPLES / "uz.json"))


# --- HTML --------------------------------------------------------------------

def test_html_is_a_full_page():
    page = render_html(example_report(), generated="2026-01-01 10:00")
    assert page.startswith("<!doctype html>")
    assert "</html>" in page
    assert "2026-01-01 10:00" in page


def test_html_has_no_external_files():
    page = render_html(example_report())
    assert "http://" not in page.split("<main>")[0]
    assert "<link" not in page
    assert "src=" not in page


def test_html_lists_every_issue():
    report = example_report()
    page = render_html(report)
    assert page.count('<article class="card issue') == len(report.issues)
    assert "app.welcome" in page
    assert f"{len(report.errors)} error(s) to fix" in page


def test_html_escapes_untrusted_text():
    report = check(cat({"<script>alert(1)</script>": "Hi"}),
                   cat({"<script>alert(1)</script>": "<img src=x onerror=alert(1)>"}))
    page = render_html(report)
    assert "<script>alert(1)</script>" not in page
    assert "<img src=x" not in page
    assert "&lt;script&gt;" in page


def test_html_highlights_placeholders_and_tags():
    report = check(cat({"a": "Hi {name}, <b>welcome</b>"}), cat({"a": "Salom"}))
    page = render_html(report)
    assert "<code>{name}</code>" in page
    assert "<code>&lt;b&gt;</code>" in page


def test_html_shows_edge_spaces():
    report = check(cat({"a": "Name: "}), cat({"a": "Ism: "}), ignore=[])
    assert report.issues == []
    report = check(cat({"a": "Name:"}), cat({"a": "Ism:  "}))
    assert "Ism:··" in render_html(report)


def test_html_clean_report():
    report = check(cat({"a": "Save"}), cat({"a": "Saqlash"}))
    page = render_html(report)
    assert "No problems found" in page
    assert "<article" not in page
    assert 'class="badge pass"' in page


def test_html_warning_only_status():
    report = check(cat({"a": "Saved."}), cat({"a": "Saqlandi"}))
    assert 'class="badge warn"' in render_html(report)


def test_html_progress_bar():
    report = check(cat({"a": "Open", "b": "Close"}), cat({"a": "Ochish", "b": ""}))
    page = render_html(report)
    assert 'aria-valuenow="50.0"' in page
    assert "width:50.0%" in page


# --- Markdown ----------------------------------------------------------------

def test_markdown_table():
    report = example_report()
    md = render_markdown(report)
    assert md.startswith("## Translation check")
    assert "❌" in md
    assert "| Type | Check | Found |" in md
    assert md.count("\n| ❌ |") + md.count("\n| ⚠️ |") == len(report.issues)


def test_markdown_escapes_pipes():
    report = check(cat({"a": "A | B."}), cat({"a": "A | B"}))
    md = render_markdown(report)
    assert "A \\| B" in md


def test_markdown_clean():
    md = render_markdown(check(cat({"a": "Save"}), cat({"a": "Saqlash"})))
    assert "✅ **No problems found**" in md
    assert "| Type |" not in md


# --- command line ------------------------------------------------------------

def test_cli_html_to_file(tmp_path):
    out = tmp_path / "report.html"
    code = main(["check", str(EXAMPLES / "en.json"), str(EXAMPLES / "uz.json"),
                 "--format", "html", "-o", str(out)])
    assert code == 1  # the example has errors
    assert "<!doctype html>" in out.read_text(encoding="utf-8")


def test_cli_markdown_to_stdout(capsys):
    main(["check", str(EXAMPLES / "en.json"), str(EXAMPLES / "uz.json"), "--format", "markdown"])
    assert "## Translation check" in capsys.readouterr().out


def test_cli_errors_only_html(tmp_path):
    out = tmp_path / "r.html"
    main(["check", str(EXAMPLES / "en.json"), str(EXAMPLES / "uz.json"),
          "--format", "html", "--errors-only", "-o", str(out)])
    page = out.read_text(encoding="utf-8")
    assert 'data-severity="warning"' not in page
    assert 'data-severity="error"' in page


def test_cli_text_to_file(tmp_path, capsys):
    out = tmp_path / "r.txt"
    main(["check", str(EXAMPLES / "en.json"), str(EXAMPLES / "uz.json"), "-o", str(out)])
    assert "[placeholders] app.welcome" in out.read_text(encoding="utf-8")
    assert "[placeholders]" not in capsys.readouterr().out


def test_cli_bad_output_path(capsys):
    code = main(["check", str(EXAMPLES / "en.json"), str(EXAMPLES / "uz.json"),
                 "--format", "html", "-o", "/no/such/dir/r.html"])
    assert code == 2
    assert "Error" in capsys.readouterr().err
