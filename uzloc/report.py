"""Turn a checker Report into a file people can read: HTML or Markdown.

    html = render_html(report)        # one self-contained page, no internet needed
    md = render_markdown(report)      # for a GitHub issue, pull request or wiki

The HTML page has a progress bar, a summary by check, buttons to filter the
list, and source/translation pairs with placeholders and tags highlighted.
It works in light and dark mode and prints cleanly.
"""

import html
import re
from datetime import datetime

from uzloc import __version__
from uzloc.checker import ALL_CHECKS, ERROR, PLACEHOLDER_RE, SEVERITY, TAG_RE

# What each check means, in plain words, for the summary table.
CHECK_HELP = {
    "missing": "Key is in the source but not in the translation",
    "empty": "Translation is empty",
    "placeholders": "Placeholders such as {name} or %s differ from the source",
    "tags": "HTML tags such as <b> differ from the source",
    "extra": "Key is only in the translation",
    "untranslated": "Translation is the same as the source text",
    "script": "Latin and Cyrillic are mixed, or the wrong script is used",
    "whitespace": "Leading or trailing spaces differ from the source",
    "punctuation": "Final punctuation differs from the source",
    "fuzzy": "PO entry is marked fuzzy and needs review",
}

CODE_RE = re.compile(f"(?:{PLACEHOLDER_RE.pattern})|(?:{TAG_RE.pattern})")


def _ordered_counts(report) -> list:
    """(check, count) pairs in the checker's own order: errors first."""
    counts = report.counts()
    return [(name, counts[name]) for name in ALL_CHECKS if counts.get(name)]


def _status(report) -> tuple:
    if report.errors:
        return "fail", f"{len(report.errors)} error(s) to fix"
    if report.warnings:
        return "warn", f"No errors, {len(report.warnings)} warning(s) to review"
    return "pass", "No problems found"


# --- HTML ----------------------------------------------------------------------

def _highlight(text: str) -> str:
    """Escape text and wrap placeholders and tags in <code> so they stand out."""
    if not text:
        return '<span class="none">(empty)</span>'
    parts, last = [], 0
    for m in CODE_RE.finditer(text):
        parts.append(html.escape(text[last:m.start()]))
        parts.append(f"<code>{html.escape(m.group())}</code>")
        last = m.end()
    parts.append(html.escape(text[last:]))
    out = "".join(parts)
    # Make edge spaces and line breaks visible: they matter in translations.
    out = re.sub(r"^ +| +$", lambda s: "·" * len(s.group()), out)
    return out.replace("\n", '<span class="nl">↵</span><br>')


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1f23;--soft:#5b616e;--rule:#e3e5e8;
--err:#c4322b;--err-bg:#fdecea;--warn:#a35f00;--warn-bg:#fff4e0;--ok:#1d7a3e;--ok-bg:#e8f5ec;
--accent:#1f4fd8;--code:#eef1f6}
@media (prefers-color-scheme:dark){:root{--bg:#15171b;--card:#1e2126;--ink:#e8eaed;--soft:#a2a8b3;
--rule:#30343b;--err:#ff7b72;--err-bg:#3a1d1c;--warn:#f0b35a;--warn-bg:#382a14;--ok:#6fd08c;
--ok-bg:#16301f;--accent:#8ab4ff;--code:#2a2f37}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:32px 16px 48px}
h1{font-size:24px;margin:0 0 4px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--soft);margin:32px 0 12px}
.files{color:var(--soft);font-size:14px;word-break:break-all}
.card{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:16px}
.status{display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin-top:20px}
.badge{font-weight:600;padding:6px 12px;border-radius:999px}
.badge.fail{background:var(--err-bg);color:var(--err)}
.badge.warn{background:var(--warn-bg);color:var(--warn)}
.badge.pass{background:var(--ok-bg);color:var(--ok)}
.progress{flex:1;min-width:220px}
.bar{height:10px;background:var(--rule);border-radius:999px;overflow:hidden;margin-top:6px}
.bar span{display:block;height:100%;background:var(--accent)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:16px}
.stat b{display:block;font-size:26px}
.stat span{color:var(--soft);font-size:13px}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-size:13px;color:var(--soft);font-weight:600}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.filters button{font:inherit;font-size:13px;border:1px solid var(--rule);background:var(--card);
color:var(--ink);border-radius:999px;padding:4px 12px;cursor:pointer}
.filters button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:var(--card)}
.issue{border-left:4px solid var(--rule);margin-bottom:10px}
.issue.error{border-left-color:var(--err)}
.issue.warning{border-left-color:var(--warn)}
.issue header{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}
.tag{font-size:12px;font-weight:600;padding:1px 8px;border-radius:4px}
.tag.error{background:var(--err-bg);color:var(--err)}
.tag.warning{background:var(--warn-bg);color:var(--warn)}
.key{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;word-break:break-all}
.msg{color:var(--soft);margin:4px 0 8px}
.pair{display:grid;grid-template-columns:110px 1fr;gap:4px 12px;font-size:14px;margin:0}
.pair dt{color:var(--soft)}
.pair dd{margin:0;word-break:break-word}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.92em;background:var(--code);
padding:0 4px;border-radius:4px}
.none,.nl{color:var(--soft);font-style:italic}
.empty{text-align:center;padding:32px;color:var(--ok);font-weight:600}
footer{margin-top:40px;color:var(--soft);font-size:13px}
@media (max-width:600px){.pair{grid-template-columns:1fr}.pair dt{margin-top:4px}.meaning{display:none}}
@media print{body{background:#fff}.filters{display:none}.card,.issue{break-inside:avoid}}
"""

JS = """
document.querySelectorAll('.filters button').forEach(function(btn){
  btn.addEventListener('click',function(){
    document.querySelectorAll('.filters button').forEach(function(b){b.setAttribute('aria-pressed','false')});
    btn.setAttribute('aria-pressed','true');
    var f=btn.dataset.filter, shown=0;
    document.querySelectorAll('.issue').forEach(function(el){
      var ok=f==='all'||el.dataset.severity===f||el.dataset.check===f;
      el.hidden=!ok; if(ok) shown++;
    });
    document.getElementById('shown').textContent=shown;
  });
});
"""


def render_html(report, title="Translation check", generated=None) -> str:
    """Return one self-contained HTML page for a Report."""
    e = html.escape
    generated = generated or datetime.now().strftime("%Y-%m-%d %H:%M")
    state, headline = _status(report)
    counts = _ordered_counts(report)

    rows = "".join(
        f'<tr><td><span class="tag {SEVERITY[name]}">{SEVERITY[name]}</span></td>'
        f'<td><b>{e(name)}</b></td><td class="meaning">{e(CHECK_HELP[name])}</td><td>{n}</td></tr>'
        for name, n in counts
    )
    summary = (
        f'<div class="card"><table><thead><tr><th>Type</th><th>Check</th><th class="meaning">Meaning</th>'
        f"<th>Found</th></tr></thead><tbody>{rows}</tbody></table></div>"
        if counts else ""
    )

    buttons = ['<button type="button" data-filter="all" aria-pressed="true">'
               f"All ({len(report.issues)})</button>"]
    if report.errors and report.warnings:
        buttons.append(f'<button type="button" data-filter="error" aria-pressed="false">'
                       f"Errors ({len(report.errors)})</button>")
        buttons.append(f'<button type="button" data-filter="warning" aria-pressed="false">'
                       f"Warnings ({len(report.warnings)})</button>")
    buttons += [f'<button type="button" data-filter="{e(name)}" aria-pressed="false">'
                f"{e(name)} ({n})</button>" for name, n in counts]

    items = []
    for issue in report.issues:
        pair = ""
        if issue.source or issue.check == "missing":
            pair += f"<dt>Source</dt><dd>{_highlight(issue.source)}</dd>"
        if issue.check != "missing":
            pair += f"<dt>Translation</dt><dd>{_highlight(issue.target)}</dd>"
        items.append(
            f'<article class="card issue {issue.severity}" data-severity="{issue.severity}" '
            f'data-check="{e(issue.check)}"><header><span class="tag {issue.severity}">'
            f"{e(issue.check)}</span><span class=\"key\">{e(issue.key)}</span></header>"
            f'<p class="msg">{e(issue.message)}</p><dl class="pair">{pair}</dl></article>'
        )

    if report.issues:
        issues_html = (f'<div class="filters" role="group" aria-label="Filter issues">'
                       f'{"".join(buttons)}</div>'
                       f'<p class="files">Showing <span id="shown">{len(report.issues)}</span> '
                       f"of {len(report.issues)}</p>{''.join(items)}")
    else:
        issues_html = '<div class="card empty">✓ No problems found. Every check passed.</div>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>{e(title)}</h1>
<p class="files">Source: {e(report.source_path)}<br>Translation: {e(report.target_path)}</p>

<div class="card status">
  <span class="badge {state}">{e(headline)}</span>
  <div class="progress">{report.translated} of {report.total} keys translated ({report.progress}%)
    <div class="bar" role="progressbar" aria-valuenow="{report.progress}" aria-valuemin="0"
      aria-valuemax="100"><span style="width:{report.progress}%"></span></div>
  </div>
</div>

<div class="stats">
  <div class="card stat"><b>{report.total}</b><span>keys in source</span></div>
  <div class="card stat"><b>{report.translated}</b><span>translated</span></div>
  <div class="card stat"><b style="color:var(--err)">{len(report.errors)}</b><span>errors</span></div>
  <div class="card stat"><b style="color:var(--warn)">{len(report.warnings)}</b><span>warnings</span></div>
</div>

{"<h2>Summary</h2>" + summary if summary else ""}

<h2>Issues</h2>
{issues_html}

<footer>Made with uzloc {__version__} · {e(generated)}</footer>
</main>
<script>{JS}</script>
</body>
</html>
"""


# --- Markdown --------------------------------------------------------------------

def _md_cell(text: str, width: int = 80) -> str:
    """Make text safe inside a Markdown table cell."""
    if not text:
        return "*(empty)*"
    text = text.replace("\n", "\\n")
    if len(text) > width:
        text = text[: width - 1] + "…"
    text = text.replace("|", "\\|").replace("`", "'")
    return f"`{text}`"


def render_markdown(report, title="Translation check") -> str:
    """Return a Markdown report, ready to paste into GitHub."""
    state, headline = _status(report)
    icon = {"fail": "❌", "warn": "⚠️", "pass": "✅"}[state]
    lines = [
        f"## {title}",
        "",
        f"{icon} **{headline}**",
        "",
        f"- Source: `{report.source_path}`",
        f"- Translation: `{report.target_path}`",
        f"- Progress: {report.translated}/{report.total} keys translated ({report.progress}%)",
        "",
    ]
    counts = _ordered_counts(report)
    if counts:
        lines += ["| Type | Check | Found |", "| --- | --- | --- |"]
        lines += [f"| {SEVERITY[name]} | {name} | {n} |" for name, n in counts]
        lines.append("")
        lines += ["| | Check | Key | Problem | Source | Translation |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for i in report.issues:
            mark = "❌" if i.severity == ERROR else "⚠️"
            lines.append(f"| {mark} | {i.check} | {_md_cell(i.key, 50)} | "
                         f"{i.message.replace('|', chr(92) + '|')} | "
                         f"{_md_cell(i.source)} | {_md_cell(i.target)} |")
        lines.append("")
    lines.append(f"<sub>Made with uzloc {__version__}</sub>")
    return "\n".join(lines) + "\n"
