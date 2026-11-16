"""A small web interface for uzloc that runs on your own computer.

    uzloc web                 # opens http://127.0.0.1:8765 in the browser
    uzloc web --port 9000 --no-browser

Three tabs: transliterate text, search the glossary, and check a translation
file with an HTML report. It uses only Python's standard library, listens on
127.0.0.1 (this computer only) and never sends your files anywhere.

The API is plain JSON, so other tools can use it too:
    POST /api/translit   {"text": "...", "to": "auto" | "latin" | "cyrillic"}
    GET  /api/glossary?q=save&lang=any&limit=10
    POST /api/check      {"source": {"name": "en.json", "text": "..."},
                          "target": {"name": "uz.json", "text": "..."} | null,
                          "script": "latin" | "cyrillic" | null, "ignore": ["punctuation"]}
"""

import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from uzloc import __version__
from uzloc.checker import ALL_CHECKS, check
from uzloc.glossary import categories, load_glossary, search
from uzloc.loaders import LoadError, detect_format, load_csv, load_json, load_po
from uzloc.report import render_html, render_markdown
from uzloc.translit import cyrillic_to_latin, detect_script, latin_to_cyrillic, transliterate

PAGE_PATH = Path(__file__).parent / "data" / "web.html"
MAX_BODY = 5 * 1024 * 1024  # 5 MB is plenty for translation files
LOADERS = {"json": load_json, "po": load_po, "csv": load_csv}
CONVERTERS = {"auto": transliterate, "latin": cyrillic_to_latin, "cyrillic": latin_to_cyrillic}


class ApiError(ValueError):
    """A problem with the request; shown to the user as a message."""


# --- API functions (plain dicts in, plain dicts out, easy to test) --------------

def api_translit(data: dict) -> dict:
    text = data.get("text")
    to = data.get("to", "auto")
    if not isinstance(text, str):
        raise ApiError("Send some text to convert.")
    if to not in CONVERTERS:
        raise ApiError("'to' must be auto, latin or cyrillic.")
    return {"result": CONVERTERS[to](text), "input_script": detect_script(text)}


_TERMS = None


def _terms():
    global _TERMS
    if _TERMS is None:
        _TERMS = load_glossary()
    return _TERMS


def api_glossary(params: dict) -> dict:
    query = params.get("q", "").strip()
    lang = params.get("lang", "any")
    category = params.get("category") or None
    if lang not in ("any", "en", "uz", "ru"):
        raise ApiError("'lang' must be any, en, uz or ru.")
    try:
        limit = max(1, min(int(params.get("limit", 10)), 50))
    except ValueError:
        raise ApiError("'limit' must be a number.") from None
    terms = _terms()
    if not query:
        return {"matches": [], "categories": categories(terms)}
    matches = search(query, terms, lang=lang, category=category, limit=limit)
    return {
        "matches": [dict(m.term.to_dict(), score=m.score) for m in matches],
        "categories": categories(terms),
    }


def _catalog(file: dict, label: str):
    if not isinstance(file, dict) or not isinstance(file.get("text"), str):
        raise ApiError(f"Add the {label} file.")
    name = str(file.get("name") or label)
    try:
        fmt = detect_format(name)
        return LOADERS[fmt](file["text"].lstrip("﻿"), name)
    except LoadError as err:
        raise ApiError(str(err)) from None


def api_check(data: dict) -> dict:
    source = _catalog(data.get("source"), "source")
    if data.get("target"):
        target = _catalog(data["target"], "translation")
    else:
        if not source.sources:
            raise ApiError("With one file, it must be a .po file. Otherwise add a translation file.")
        target = source
    script = data.get("script") or None
    if script not in (None, "latin", "cyrillic"):
        raise ApiError("'script' must be latin or cyrillic.")
    ignore = data.get("ignore") or []
    if not isinstance(ignore, list) or set(ignore) - set(ALL_CHECKS):
        raise ApiError(f"'ignore' must list checks from: {', '.join(ALL_CHECKS)}")
    report = check(source, target, script=script, ignore=ignore)
    return {
        "summary": {k: v for k, v in report.to_dict().items() if k != "issues"},
        "html": render_html(report),
        "markdown": render_markdown(report),
        "json": report.to_dict(),
    }


# --- HTTP server ---------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = f"uzloc/{__version__}"

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    def _send(self, status, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, data):
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _error(self, status, message):
        self._json(status, {"error": message})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            page = PAGE_PATH.read_text(encoding="utf-8").replace("{{VERSION}}", __version__)
            self._send(HTTPStatus.OK, page.encode("utf-8"), "text/html; charset=utf-8")
        elif url.path == "/api/glossary":
            params = {k: v[0] for k, v in parse_qs(url.query).items()}
            self._run(api_glossary, params)
        elif url.path == "/api/version":
            self._json(HTTPStatus.OK, {"version": __version__, "checks": list(ALL_CHECKS)})
        else:
            self._error(HTTPStatus.NOT_FOUND, "Not found.")

    def do_POST(self):
        url = urlparse(self.path)
        routes = {"/api/translit": api_translit, "/api/check": api_check}
        if url.path not in routes:
            return self._error(HTTPStatus.NOT_FOUND, "Not found.")
        # Only the page itself may call the API: blocks other websites from
        # sending requests to this local server through your browser.
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != host:
            return self._error(HTTPStatus.FORBIDDEN, "Requests from other sites are not allowed.")
        if "application/json" not in self.headers.get("Content-Type", ""):
            return self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Send JSON.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Files are too large (5 MB max).")
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error(HTTPStatus.BAD_REQUEST, "The request is not valid JSON.")
        if not isinstance(data, dict):
            return self._error(HTTPStatus.BAD_REQUEST, "Send a JSON object.")
        self._run(routes[url.path], data)

    def _run(self, func, arg):
        try:
            self._json(HTTPStatus.OK, func(arg))
        except ApiError as err:
            self._error(HTTPStatus.BAD_REQUEST, str(err))


def make_server(host="127.0.0.1", port=8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def serve(host="127.0.0.1", port=8765, open_browser=True):
    server = make_server(host, port)
    url = f"http://{host}:{server.server_address[1]}"
    print(f"uzloc web is running at {url}  (press Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
