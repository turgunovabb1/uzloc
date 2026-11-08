"""Command-line interface for uzloc.

Examples:
    uzloc translit "Salom dunyo"
    uzloc translit "Салом дунё" --to latin
    uzloc translit -f input.txt -o output.txt --to cyrillic
    echo "Toshkent" | uzloc translit
    uzloc detect "Salom Салом"
"""

import argparse
import sys
from pathlib import Path

from uzloc import __version__
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

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())