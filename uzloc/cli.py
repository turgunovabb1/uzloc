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
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from uzloc import __version__
from uzloc.glossary import GlossaryError, categories, load_glossary, search
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

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())