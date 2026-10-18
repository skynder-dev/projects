from __future__ import annotations

import html
from pathlib import Path


def _e(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def guide_path() -> Path:
    return Path(__file__).resolve().parent / "BETA_GUIDE.md"


def guide_text() -> str:
    try:
        from .i18n import ui_language
        ru = guide_path().with_name("BETA_GUIDE.ru.md")
        if ui_language() == "ru" and ru.exists():
            return ru.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return guide_path().read_text(encoding="utf-8", errors="replace")


def _inline(text: str) -> str:
    """**bold** and `code` of the guide (shown as such, not with the stars and backticks)."""
    import re
    t = _e(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`([^`]+)`", r"<code translate='no'>\1</code>", t)


def guide_html(text: str) -> str:
    """The guide's small Markdown (## headings, numbered steps, paragraphs, **bold**, `code`) as readable HTML."""
    out, para, items = [], [], []

    def flush():
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para.clear()
        if items:
            out.append("<ol>" + "".join("<li>" + _inline(" ".join(i)) + "</li>" for i in items) + "</ol>")
            items.clear()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
        elif line.startswith("# "):           # the page already has this title
            flush()
        elif line.startswith("## "):
            flush()
            out.append("<h2>" + _e(line[3:]) + "</h2>")
        elif line[:1].isdigit() and ". " in line[:4]:
            if para:
                flush()
            items.append([line.split(". ", 1)[1]])
        elif items and raw[:1] in (" ", "\t"):   # continuation of a step
            items[-1].append(line)
        else:
            if items:
                flush()
            para.append(line)
    flush()
    return "".join(out)


def guide_body() -> str:
    return ("<div class='pagehead'><div class='eyebrow'>Beta guide</div><h1>MediaEngine Beta Guide</h1>"
            "<div class='lead'>Bundled local-first beta guidance from this installed build.</div></div>"
            "<div class='card guide' style='max-width:900px;line-height:1.6'>" + guide_html(guide_text()) + "</div>")


def welcome_body(catalog: list[dict]) -> str:
    cards = []
    for item in catalog:
        required = bool(item.get("required"))
        cards.append(
            "<div class='card'><div class='row space'><b>" + _e(item.get("name")) + "</b>"
            + "<span class='badge " + ("ready" if required else "unreviewed") + "'>"
            + ("Required" if required else "Optional") + "</span></div>"
            + "<div class='muted' style='margin-top:6px'>" + _e(item.get("why")) + "</div>"
            + "<div class='about-list' style='margin-top:10px'>"
            + "<div><b>Status</b><div class='muted'>" + _e(item.get("status")) + "</div></div>"
            + "<div><b>Cost</b><div class='muted'>" + _e(item.get("cost")) + "</div></div>"
            + "<div><b>Data</b><div class='muted'>" + _e(item.get("data")) + "</div></div></div>"
            + "<div style='margin-top:10px'><a class='btn btn2' href='" + _e(item.get("href") or "#") + "'>"
            + _e(item.get("action") or "Open") + "</a></div></div>"
        )
    return """<div class='pagehead'><div class='eyebrow'>First run</div><h1>Start local. Add only what you need.</h1>
<div class='lead'>MediaEngine is local-first. Your media stays on this PC unless you explicitly connect a provider or enable an optional cloud workflow.</div>
<div class='row' style='margin-top:12px'><a class='btn' href='/import'>1 · Add a media source</a><a class='btn btn2' href='/settings/connections'>2 · Review optional connections</a><a class='btn btn2' href='/help'>3 · Help & recovery</a></div></div>
<div class='card callout'><b>A reel from your own videos:</b> <span class='muted'>open Auto Edit, choose a folder (or single videos), pick length, format and sound.</span><div class='row' style='margin-top:8px'><a class='btn' href='/auto'>Auto Edit</a><a class='btn btn2' href='/auto/check'>Check this PC</a></div></div>
<div class='card callout'><b>No external account or billing is required for local use.</b><div class='muted' style='margin-top:4px'>Cloud, social-provider and online-AI features are optional. They stay off or unconfigured until you explicitly enable or connect them.</div></div>
<div class='section-title'>What can leave this PC</div>
<div class='card'><p class='lead' style='font-size:15px'>Nothing leaves this PC by default. If you explicitly connect a provider or start an optional upload, authentication data, selected uploads, and provider analytics can be sent to that service.</p>
<div class='muted'>Provider credentials belong in Windows Credential Manager, not MediaEngine SQLite or Supabase. Cloud Vault is off by default and enabling cloud never deletes local or source originals.</div></div>
<div class='section-title'>Required vs optional</div><div class='about-grid'>""" + "".join(cards) + """</div>
<div class='section-title'>Analytics boundary</div><div class='card'>Provider analytics keep their source provenance and remain descriptive. MediaEngine does not automatically choose a cross-provider winner or create an opaque ranking.</div>"""


def connection_disclosure_html() -> str:
    return """<div class='card callout' style='margin:12px 0'><b>What can leave this PC</b><div class='muted' style='margin-top:4px'>Connecting a provider can send authentication data, selected uploads, and provider analytics to that service. Provider credentials stay in Windows Credential Manager, not MediaEngine SQLite or Supabase. Nothing is connected automatically.</div></div><p class='muted'>Provider connections are local-first. This page never asks ordinary users for API secrets.</p>"""


def help_body() -> str:
    return """<div class='pagehead'><div class='eyebrow'>Beta support</div><h1>Help & recovery</h1><div class='lead'>Local troubleshooting first. Nothing here silently uploads media, tokens, or diagnostics.</div></div>
<div class='about-grid'>
<div class='card'><h2 style='margin-top:0'>Jobs & errors</h2><p class='muted'>Open Activity → Jobs & errors to inspect durable job history. Failed jobs can be retried from their job detail page; running jobs can be cancelled safely.</p><a class='btn btn2' href='/jobs'>Open Jobs & errors</a></div>
<div class='card'><h2 style='margin-top:0'>Diagnostics</h2><p class='muted'>Diagnostics stay local by default. They are for local troubleshooting and release acceptance unless you explicitly choose to share diagnostic information.</p><a class='btn btn2' href='/activity'>Open Activity</a></div>
<div class='card'><h2 style='margin-top:0'>Support data</h2><p class='muted'>Support export/upload is explicit opt-in only; this beta does not auto-upload support data. Raw media and tokens are excluded by default.</p><a class='btn btn2' href='/settings/connections'>Review Connections</a></div>
<div class='card'><h2 style='margin-top:0'>Recovery safety</h2><p class='muted'>Update health checks can restore the previous build when a new release fails to start. Recovery does not weaken privacy settings and never deletes source originals.</p><div class='row'><a class='btn btn2' href='/auto/update'>Updates</a><a class='btn btn2' href='/about'>About update safety</a></div></div>
</div><div class='row' style='margin-top:14px'><a class='btn btn2' href='/help/guide'>Open bundled Beta Guide</a></div>
<div class='card callout' style='margin-top:14px'><b>Local-first reminder:</b><div class='muted'>No external account or billing is required for local use. Optional provider or cloud workflows remain user-initiated.</div></div>"""
