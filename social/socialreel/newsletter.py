"""Offline, quote-only owner drafts. No transport, model or publication."""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .common import PipelineError, read_json, sha256_bytes, write_json, parse_date
from . import grants, usagov
from .claims import build_claims as grant_claims
from .public_sources import html_record
from .usagov_facts import USAGovHTML, CONDITIONS, EXPIRED

NOTICE = "We are not a government agency. Always check the official page before applying."
SLOT = "[SPONSOR OR AFFILIATE: owner decides]"
HOSTS = {"www.usa.gov", "usa.gov", "www.grants.gov", "grants.gov"}


def official(url):
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in HOSTS or p.username or p.password or p.query or p.fragment or p.port not in (None, 443):
        raise PipelineError("Official source URL required; tracking/affiliate links refused")
    return url


def snapshot(bundle, receipt):
    rel = Path(receipt["file"])
    path = (bundle / rel).resolve()
    if rel.is_absolute() or not path.is_relative_to(bundle.resolve()):
        raise PipelineError("Snapshot escapes bundle")
    raw = path.read_bytes()
    if sha256_bytes(raw) != receipt["sha256"]:
        raise PipelineError("Snapshot SHA-256 mismatch")
    return raw


def verified(bundle, today):
    """Rebuild from hashed source bytes, never trust an editable factual ledger."""
    rec = read_json(bundle / "record.json")
    kind = rec.get("source_type", "grants")
    if kind == "usagov":
        receipt = rec["provenance"]
        raw = snapshot(bundle, receipt)
        rebuilt = html_record(raw, receipt, "usagov", parser_type=USAGovHTML)
        rows = usagov.build_claims(rebuilt)
    elif kind == "grants":
        receipts = list((rec.get("field_provenance") or {}).values())
        provenance = rec.get("provenance") or {}
        receipts += [v for v in provenance.values() if isinstance(v, dict) and "file" in v]
        if not receipts:
            for row in read_json(bundle / "claims.json"):
                src = row.get("source") or {}
                if src.get("snapshot_file"):
                    receipts.append({"file": src["snapshot_file"], "sha256": src["snapshot_sha256"]})
        hits, detail, search_meta, detail_meta, rebuilt = [], None, None, None, None
        for receipt in {r["file"]: r for r in receipts}.values():
            obj = json.loads(snapshot(bundle, receipt))
            records = obj if isinstance(obj, list) else obj.get("records", [])
            for row in records:
                if str((row.get("normalized_facts") or {}).get("opportunity_id")) == str(rec.get("opportunity_id")):
                    rebuilt = grants.from_fixture(row)
                    detail_meta = receipt
            data = obj.get("data", {}) if isinstance(obj, dict) else {}
            if isinstance(data, dict) and "oppHits" in data:
                hits, search_meta = data["oppHits"], receipt
            elif isinstance(data, dict) and str(data.get("id")) == str(rec.get("opportunity_id")):
                detail, detail_meta = data, receipt
        if rebuilt is None:
            hit = next((h for h in hits if str(h.get("id")) == str(rec.get("opportunity_id"))), {"id": rec.get("opportunity_id")})
            if detail is None:
                raise PipelineError("No verifiable Grants.gov source record")
            rebuilt = grants.normalize(hit, detail, search_snapshot=search_meta, detail_snapshot=detail_meta)
        rows = grant_claims(rebuilt, detail_meta, today)
    else:
        raise PipelineError("Newsletter supports verified USA.gov and Grants.gov bundles")
    official(rebuilt["source_url"])
    return rebuilt, rows


def past(text, today):
    month_date = r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:,?\s+20\d\d)?\b"
    for value in re.findall(month_date, text, re.I):
        # Missing year is ambiguous; do not turn it into upcoming advice.
        parsed = parse_date(value)
        if not re.search(r"20\d\d", value) or parsed is None or parsed < today:
            return True
    # Conservative: historical years/date formats cannot become upcoming advice.
    if any(int(y) < today.year for y in re.findall(r"\b(20\d\d)\b", text)):
        return True
    for value in re.findall(r"\b\d{1,2}[/\.]\d{1,2}[/\.]20\d\d\b", text):
        fmt = "%m/%d/%Y" if "/" in value else "%d.%m.%Y"
        try:
            if dt.datetime.strptime(value, fmt).date() < today:
                return True
        except ValueError:
            return True
    dates = re.findall(r"\b20\d\d-\d\d-\d\d\b", text)
    for value in dates:
        try:
            if dt.date.fromisoformat(value) < today:
                return True
        except ValueError:
            return True
    for match in re.finditer(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d\d)\b", text, re.I):
        try:
            if dt.datetime.strptime(" ".join(match.groups()), "%B %d %Y").date() < today:
                return True
        except ValueError:
            return True
    for value in re.findall(r"\b[A-Za-z]{3}\s+\d{1,2},?\s+20\d\d\b", text):
        parsed = parse_date(value)
        if parsed and parsed < today:
            return True
    return False


def owner_picks(root):
    """Use the existing chain verifier; avoid creating an absent store/database."""
    if root is None or not (Path(root) / "queue.sqlite3").is_file():
        return {}, ["Хранилище решений отсутствует; используются только проверенные bundles."]
    from .concept_store import ConceptStore
    from .concept_choose import list_jobs
    picks, notes = {}, []
    for view in list_jobs(ConceptStore(root)):
        if view["state"] != "picked":
            continue
        card = next(c for c in view["proposal"]["concepts"] if c["id"] == view["current_decision"]["selected"])
        url = view["source"].get("source_url")
        keys = set(card.get("basis_claim_keys", []))
        claims = {c["key"]: c for c in view["trial"]["stages"]["claims"]}
        picks[url] = {k: claims[k]["statement"] for k in keys if k in claims}
    return picks, notes


def collect(bundles, today, picks):
    candidates, omitted = [], []
    for folder in bundles:
        folder = Path(folder)
        try:
            rec, rows = verified(folder, today)
            close = parse_date(rec.get("close_date"))
            if close and close < today:
                raise PipelineError("Opportunity close date is before issue date")
            invalid = {c["key"] for c in rows if c.get("expired") or EXPIRED.search(c.get("quote", c["statement"]))
                       or past(c.get("quote", c["statement"]), today)}
            while True:
                more = {c["key"] for c in rows if invalid.intersection(c.get("values", {}).get("required_context_keys", []))}
                if more <= invalid:
                    break
                invalid |= more
            for key in sorted(invalid):
                omitted.append({"bundle": str(folder), "claim_key": key, "reason": "Истёкший факт или дата до выпуска; исключён"})
            if any(c["key"] in invalid and CONDITIONS.search(c.get("quote", c["statement"])) for c in rows):
                raise PipelineError("Expired/past condition: whole bundle omitted rather than detaching its rules")
            active = [c for c in rows if c["key"] not in invalid]
            # Identity/lead holds page-wide context. Never detach its conditions.
            if "identity" in invalid:
                raise PipelineError("Page identity/lead is expired or contains a past date")
            conditions = [c for c in active if c["key"] in {"eligibility", "eligibility_conditions", "cost_sharing"} or
                          CONDITIONS.search(c.get("quote", c["statement"]))]
            if not conditions:
                raise PipelineError("No verified condition; no condition invented")
            picked = picks.get(rec["source_url"], {})
            matched = any(c["key"] in picked and c["statement"] == picked[c["key"]] for c in active)
            observed = max((str(c.get("observed_at", "")) for c in active), default="")
            candidates.append({"record": rec, "claims": active, "conditions": conditions,
                               "picked": matched, "observed": observed, "bundle": str(folder)})
        except (PipelineError, OSError, ValueError, KeyError, TypeError) as error:
            omitted.append({"bundle": str(folder), "reason": str(error)})
    candidates.sort(key=lambda c: (c["picked"], c["observed"]), reverse=True)
    unique, seen = [], set()
    for c in candidates:
        url = c["record"]["source_url"]
        if url in seen:
            omitted.append({"bundle": c["bundle"], "reason": "Повтор источника"})
        else:
            seen.add(url); unique.append(c)
    return unique, omitted


def quote(row):
    return row.get("quote") or row["statement"]


def citation(candidate, row):
    return {"claim_key": row["key"], "quote": quote(row), "source_url": candidate["record"]["source_url"],
            "source": row["source"], "bundle": candidate["bundle"]}


def render(mode, bundles, out, *, as_of=None, store=None):
    today = dt.date.fromisoformat(as_of) if as_of else dt.date.today()
    picks, notes = owner_picks(store) if mode == "draft" else ({}, [])
    candidates, omitted = collect(bundles, today, picks)
    items = []
    for c in candidates:
        rec = c["record"]
        if mode == "checklist":
            if not re.search(r"unclaimed|unpaid|wage", rec["source_url"], re.I):
                omitted.append({"bundle": c["bundle"], "reason": "Не источник о невостребованных деньгах"}); continue
            groups = [[r] for r in c["claims"] if r.get("kind") == "table_row" or r.get("values", {}).get("place")]
        else:
            body = []
            for row in c["claims"]:
                if row["key"] == "identity" or row.get("kind") == "page":
                    continue
                count = len(re.findall(r"[.!?](?=\s|$)", quote(row)))
                if count and sum(len(re.findall(r"[.!?](?=\s|$)", quote(r))) for r in body) + count <= 3 and len(quote(row).split()) <= 80:
                    body.append(row)
            groups = [body] if 2 <= sum(len(re.findall(r"[.!?](?=\s|$)", quote(r))) for r in body) <= 3 else []
        if not groups:
            omitted.append({"bundle": c["bundle"], "reason": "Недостаточно целых коротких цитат для формата"})
        for group in groups:
            if mode == "checklist" and (len(items) >= 5 or sum(len(f["quote"]) for i in items for f in i["facts"] + i["conditions"]) + sum(len(quote(r)) for r in group + c["conditions"]) > 2200):
                omitted.append({"url": rec["source_url"], "reason": "Лимит одной печатной страницы; целая строка пропущена"})
                continue
            items.append({"title": rec["title"], "url": rec["source_url"], "owner_picked": c["picked"],
                          "title_source": citation(c, next(r for r in c["claims"] if r["key"] == "identity")),
                          "facts": [citation(c, r) for r in group],
                          "conditions": [citation(c, r) for r in c["conditions"]]})
    if mode == "draft":
        for item in items[5:]:
            omitted.append({"url": item["url"], "reason": "Лимит пяти тем"})
        items = items[:5]
    heading = "Weekly source notes" if mode == "draft" else "Places the government may owe you money"
    lines = ["# " + heading, "", "Issue date: " + today.isoformat(), ""]
    for i, item in enumerate(items, 1):
        lines += ["## " + str(i) + ". " + item["title"], ""]
        lines += ["> " + f["quote"].replace("\n", "\n> ") for f in item["facts"]]
        lines += ["", "Official link: " + item["url"], "", "Conditions (source quotes):"]
        lines += ["> " + f["quote"].replace("\n", "\n> ") for f in item["conditions"]]
        lines += [""]
    lines += [NOTICE, "", "[SENDER POSTAL ADDRESS]", "[UNSUBSCRIBE LINK]", ""]
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    stem = "newsletter" if mode == "draft" else "checklist"
    text = "\n".join(lines)
    (out / (stem + ".md")).write_text(text, encoding="utf-8")
    if mode == "draft":
        (out / (stem + ".txt")).write_text(text.replace("# ", "").replace("> ", ""), encoding="utf-8")
    else:
        printable = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Checklist</title><style>body{font:11pt serif;max-width:190mm;margin:auto}article{break-inside:avoid}a{overflow-wrap:anywhere}@page{size:A4;margin:12mm}</style><h1>' + html.escape(heading) + '</h1>'
        for item in items:
            printable += '<article><p>☐ ' + html.escape(" ".join(f["quote"] for f in item["facts"])) + ' <a href="' + html.escape(item["url"], quote=True) + '">Official page</a><br>Conditions: ' + html.escape(" ".join(f["quote"] for f in item["conditions"])) + '</p></article>'
        (out / "checklist.html").write_text(printable + '<footer>' + html.escape(NOTICE) + '</footer></html>', encoding="utf-8")
    write_json(out / "trace.json", {"as_of": today.isoformat(), "items": items, "sponsor_enabled": False})
    (out / "sponsor-slot.txt").write_text("OFF — " + SLOT + "\n", encoding="utf-8")
    summary = {"выпуск": today.isoformat(), "тем": len(items), "мало_материала": mode == "draft" and len(items) < 3,
               "выбрано": [{"источник": i["url"], "почему": "Выбор владельца и проверенные цитаты" if i["owner_picked"] else "Проверенные цитаты; порядок по времени снимка"} for i in items],
               "пропущено": omitted, "заметки": notes + ["Ничего не отправлено и не опубликовано. Актуальность источников в сети не проверялась."]}
    write_json(out / "summary_ru.json", summary)
    return {"items": len(items), "out": str(out), "sent": False}


def add_parser(sub):
    p = sub.add_parser("newsletter", help="offline newsletter/checklist files for owner review")
    commands = p.add_subparsers(dest="newsletter_cmd", required=True)
    for mode in ("draft", "checklist"):
        c = commands.add_parser(mode)
        c.add_argument("--bundles", nargs="+", required=True, type=Path)
        c.add_argument("--out", required=True, type=Path)
        c.add_argument("--as-of", required=mode == "draft")
        if mode == "draft":
            c.add_argument("--store", required=True, type=Path)


def run(args):
    return render(args.newsletter_cmd, args.bundles, args.out, as_of=args.as_of, store=getattr(args, "store", None))
