"""Command-line interface for uzloc.

Examples:
    uzloc translit "Salom dunyo"
    uzloc translit "Салом дунё" --to latin
    uzloc translit -f input.txt -o output.txt --to cyrillic
    echo "Toshkent" | uzloc translit
    uzloc detect "Salom Салом"
    uzloc glossary password
    uzloc glossary "o'chirish" --lang uz
    uzloc glossary --categories
    uzloc check en.json uz.json
    uzloc check uz.po --script latin
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from uzloc import __version__
from uzloc.checker import ALL_CHECKS, check
from uzloc.glossary import GlossaryError, categories, load_glossary, search
from uzloc.loaders import LoadError, load
from uzloc.translit import (
    cyrillic_to_latin,
    detect_script,
    latin_to_cyrillic,
    transliterate,
)

CONVERTERS = {
    "auto": transliterate,
    "latin": cyrillic_to_latin,
    "cyrillic": latin_to_cyrillic,
}


def read_input(text_parts, file_path):
    """Get the text from (1) a file, (2) command-line words, or (3) stdin."""
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    if text_parts:
        return " ".join(text_parts)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def write_output(text, output_path):
    """Print the result or save it to a file."""
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
        print(f"Saved to {output_path}", file=sys.stderr)
    else:
        print(text, end="" if text.endswith("\n") else "\n")


def cmd_translit(args):
    text = read_input(args.text, args.file)
    if text is None:
        print("Error: give some text, a file (-f) or pipe text in.", file=sys.stderr)
        return 1
    converter = CONVERTERS[args.to]
    write_output(converter(text), args.output)
    return 0


def cmd_detect(args):
    text = read_input(args.text, args.file)
    if text is None:
        print("Error: give some text or a file (-f).", file=sys.stderr)
        return 1
    print(detect_script(text))
    return 0


def _print_table(matches):
    """Print results as an aligned three-column table."""
    rows = [("English", "O'zbekcha", "Русский")]
    rows += [(m.term.en, m.term.uz, m.term.ru) for m in matches]
    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    for n, row in enumerate(rows):
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
        if n == 0:
            print("  ".join("-" * w for w in widths))


def cmd_glossary(args):
    try:
        terms = load_glossary(args.glossary_file)
    except (GlossaryError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    if args.categories:
        for name, count in categories(terms).items():
            print(f"{name:<14}{count}")
        return 0

    query = " ".join(args.query)
    if not query:
        print("Error: give a word to search, or use --categories.", file=sys.stderr)
        return 1

    matches = search(query, terms, lang=args.lang, category=args.category,
                     fuzzy=not args.exact, limit=args.limit)
    if args.exact:
        matches = [m for m in matches if m.score == 100]
    if not matches:
        print(f"No terms found for '{query}'.", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps([m.term.to_dict() for m in matches], ensure_ascii=False, indent=2))
    elif args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["en", "uz", "ru", "category"])
        for m in matches:
            writer.writerow([m.term.en, m.term.uz, m.term.ru, m.term.category])
    else:
        if matches[0].score < 40:
            print("No exact match. Did you mean:", file=sys.stderr)
        _print_table(matches)
    return 0


def _short(text, width=60):
    text = text.replace("\n", "\\n")
    return text if len(text) <= width else text[: width - 1] + "…"


def _print_report(report, show_warnings=True):
    print(f"Source:      {report.source_path}")
    print(f"Translation: {report.target_path}")
    print(f"Progress:    {report.translated}/{report.total} keys translated ({report.progress}%)")
    print()
    shown = report.issues if show_warnings else report.errors
    for issue in shown:
        mark = "✗" if issue.severity == "error" else "!"
        print(f"{mark} [{issue.check}] {issue.key}: {issue.message}")
        if issue.source:
            print(f"    source: {_short(issue.source)}")
        if issue.target:
            print(f"    target: {_short(issue.target)}")
    if shown:
        print()
    counts = ", ".join(f"{name} {n}" for name, n in sorted(report.counts().items()))
    print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)"
          + (f" — {counts}" if counts else ""))
    if not report.issues:
        print("✓ No problems found.")


def cmd_check(args):
    try:
        if args.target:
            source, target = load(args.source), load(args.target)
        else:
            source = target = load(args.source)
            if not target.sources:
                print("Error: with one file, it must be a .po file. "
                      "Otherwise give a source and a translation.", file=sys.stderr)
                return 2
        ignore = [c.strip() for c in args.ignore.split(",")] if args.ignore else []
        report = check(source, target, script=args.script, ignore=ignore)
    except (LoadError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_report(report, show_warnings=not args.errors_only)

    failed = report.errors or (args.strict and report.warnings)
    return 1 if failed else 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="uzloc",
        description="Uzbek localization toolkit.",
    )
    parser.add_argument("--version", action="version", version=f"uzloc {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_tr = sub.add_parser("translit", help="Convert Uzbek text between Latin and Cyrillic.")
    p_tr.add_argument("text", nargs="*", help="Text to convert.")
    p_tr.add_argument("-f", "--file", help="Read text from this file.")
    p_tr.add_argument("-o", "--output", help="Save the result to this file.")
    p_tr.add_argument(
        "--to",
        choices=CONVERTERS.keys(),
        default="auto",
        help="Target script (default: auto-detect and convert to the other one).",
    )
    p_tr.set_defaults(func=cmd_translit)

    p_det = sub.add_parser("detect", help="Tell if a text is Latin, Cyrillic or mixed.")
    p_det.add_argument("text", nargs="*", help="Text to check.")
    p_det.add_argument("-f", "--file", help="Read text from this file.")
    p_det.set_defaults(func=cmd_detect)

    p_gl = sub.add_parser("glossary", help="Search the English · Uzbek · Russian IT glossary.")
    p_gl.add_argument("query", nargs="*", help="Word to look up (any of the three languages).")
    p_gl.add_argument("--lang", choices=["any", "en", "uz", "ru"], default="any",
                      help="Only search this language column (default: all).")
    p_gl.add_argument("-c", "--category", help="Only show terms from this category.")
    p_gl.add_argument("-n", "--limit", type=int, default=10, help="Maximum results (default: 10).")
    p_gl.add_argument("--exact", action="store_true", help="Only show exact matches.")
    p_gl.add_argument("--format", choices=["table", "json", "csv"], default="table",
                      help="Output format (default: table).")
    p_gl.add_argument("--glossary-file", help="Use your own CSV (columns: en, uz, ru, category).")
    p_gl.add_argument("--categories", action="store_true", help="List categories and term counts.")
    p_gl.set_defaults(func=cmd_glossary)

    p_ch = sub.add_parser(
        "check",
        help="Check a translation file for missing keys, broken placeholders and more.",
        description="Compare a source file with its translation (.json, .po or .csv). "
                    "Exit code: 0 = OK, 1 = problems found, 2 = could not read the files.",
    )
    p_ch.add_argument("source", help="Source file (e.g. en.json), or a single .po file.")
    p_ch.add_argument("target", nargs="?", help="Translated file (e.g. uz.json).")
    p_ch.add_argument("--script", choices=["latin", "cyrillic"],
                      help="Expected Uzbek script; words in the other script are reported.")
    p_ch.add_argument("--ignore", metavar="CHECKS",
                      help=f"Comma-separated checks to skip. Available: {', '.join(ALL_CHECKS)}")
    p_ch.add_argument("--format", choices=["text", "json"], default="text",
                      help="Output format (default: text).")
    p_ch.add_argument("--errors-only", action="store_true", help="Hide warnings in the text output.")
    p_ch.add_argument("--strict", action="store_true", help="Fail (exit code 1) on warnings too.")
    p_ch.set_defaults(func=cmd_check)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())