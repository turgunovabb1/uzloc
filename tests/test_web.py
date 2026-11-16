import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from uzloc.web import ApiError, api_check, api_glossary, api_translit, make_server

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def example(name):
    return {"name": name, "text": (EXAMPLES / name).read_text(encoding="utf-8")}


# --- API functions -----------------------------------------------------------

def test_translit_auto():
    r = api_translit({"text": "Salom dunyo"})
    assert r["result"] == "Салом дунё"
    assert r["input_script"] == "latin"


def test_translit_to_latin():
    assert api_translit({"text": "Тошкент", "to": "latin"})["result"] == "Toshkent"


def test_translit_bad_input():
    with pytest.raises(ApiError):
        api_translit({})
    with pytest.raises(ApiError):
        api_translit({"text": "a", "to": "greek"})


def test_glossary_search():
    r = api_glossary({"q": "save"})
    assert r["matches"][0]["en"] == "save"
    assert r["matches"][0]["uz"]
    assert "score" in r["matches"][0]
    assert sum(r["categories"].values()) > 100


def test_glossary_empty_query_returns_categories():
    r = api_glossary({"q": ""})
    assert r["matches"] == []
    assert r["categories"]


def test_glossary_bad_params():
    with pytest.raises(ApiError):
        api_glossary({"q": "save", "lang": "fr"})
    with pytest.raises(ApiError):
        api_glossary({"q": "save", "limit": "many"})


def test_check_two_files():
    r = api_check({"source": example("en.json"), "target": example("uz.json")})
    assert r["summary"]["errors"] >= 2
    assert r["html"].startswith("<!doctype html>")
    assert r["markdown"].startswith("## Translation check")
    assert r["json"]["issues"]


def test_check_single_po_with_script():
    r = api_check({"source": example("uz.po"), "script": "latin"})
    checks = {i["check"] for i in r["json"]["issues"]}
    assert {"empty", "script", "fuzzy"} <= checks


def test_check_ignore():
    r = api_check({"source": example("en.json"), "target": example("uz.json"),
                   "ignore": ["placeholders", "tags"]})
    assert r["summary"]["errors"] == 0


def test_check_errors():
    with pytest.raises(ApiError, match="source"):
        api_check({})
    with pytest.raises(ApiError, match="Unsupported"):
        api_check({"source": {"name": "a.xlsx", "text": ""}, "target": example("uz.json")})
    with pytest.raises(ApiError, match="invalid JSON"):
        api_check({"source": {"name": "a.json", "text": "{"}, "target": example("uz.json")})
    with pytest.raises(ApiError, match=".po"):
        api_check({"source": example("en.json")})
    with pytest.raises(ApiError):
        api_check({"source": example("uz.po"), "ignore": ["spelling"]})


def test_check_bom_is_ok():
    src = {"name": "en.json", "text": "﻿{\"a\": \"Save\"}"}
    tgt = {"name": "uz.json", "text": "{\"a\": \"Saqlash\"}"}
    assert api_check({"source": src, "target": tgt})["summary"]["errors"] == 0


# --- real HTTP server --------------------------------------------------------

@pytest.fixture(scope="module")
def base_url():
    server = make_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def request(url, data=None, headers=None, raw=None):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    h = {"Content-Type": "application/json"} if body is not None else {}
    h.update(headers or {})
    req = urllib.request.Request(url, data=body, headers=h)
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, res.headers, res.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read().decode("utf-8")


def test_page(base_url):
    status, headers, body = request(base_url + "/")
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert "uzloc" in body and "{{VERSION}}" not in body


def test_http_translit(base_url):
    status, _, body = request(base_url + "/api/translit", {"text": "Salom"})
    assert status == 200
    assert json.loads(body)["result"] == "Салом"


def test_http_glossary(base_url):
    status, _, body = request(base_url + "/api/glossary?q=parol")
    assert status == 200
    assert json.loads(body)["matches"]


def test_http_check(base_url):
    status, _, body = request(base_url + "/api/check",
                              {"source": example("en.json"), "target": example("uz.json")})
    assert status == 200
    assert json.loads(body)["summary"]["total"] == 9


def test_http_user_error_is_400(base_url):
    status, _, body = request(base_url + "/api/check", {})
    assert status == 400
    assert "source" in json.loads(body)["error"]


def test_http_not_found(base_url):
    assert request(base_url + "/nope")[0] == 404
    assert request(base_url + "/api/nope", {})[0] == 404


def test_http_bad_json(base_url):
    assert request(base_url + "/api/translit", raw=b"{not json")[0] == 400


def test_http_needs_json_content_type(base_url):
    status, _, _ = request(base_url + "/api/translit", raw=b'{"text":"a"}',
                           headers={"Content-Type": "text/plain"})
    assert status == 415


def test_http_blocks_other_sites(base_url):
    status, _, _ = request(base_url + "/api/translit", {"text": "a"},
                           headers={"Origin": "https://evil.example"})
    assert status == 403


def test_http_allows_own_origin(base_url):
    status, _, _ = request(base_url + "/api/translit", {"text": "a"},
                           headers={"Origin": base_url})
    assert status == 200


def test_http_too_large(base_url):
    status, _, _ = request(base_url + "/api/check", raw=b"{}",
                           headers={"Content-Length": str(6 * 1024 * 1024)})
    assert status == 413
