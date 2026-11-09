"""Pick readable, unused official pages by measured demand; no model or API keys.

python -I social/trial/demand_pick.py DEMAND_JSON OUT --per-channel 3
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.parse
from pathlib import Path

SOCIAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOCIAL))

from socialreel import govpage, usagov  # noqa: E402
from socialreel.common import PipelineError, read_json, write_json, sha256_bytes  # noqa: E402
from socialreel.public_sources import HTML_HOSTS, official_url  # noqa: E402
from socialreel.source_intake import write_bundle  # noqa: E402
from socialreel.demand_channels import CHANNELS  # noqa: E402


def identity(url):
    p = urllib.parse.urlsplit(url)
    host = p.hostname or ""
    if host in HTML_HOSTS["usagov"]:
        host = "www.usa.gov"
    return urllib.parse.urlunsplit((p.scheme, host, p.path.rstrip("/") or "/", p.query, p.fragment))


def source_for(url):
    if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url) or "\\" in url or "?" in url or "#" in url:
        raise PipelineError("Demand URL must be HTTPS without query, fragment or whitespace")
    host = urllib.parse.urlsplit(url).hostname
    if host in HTML_HOSTS["usagov"]:
        official_url(url, HTML_HOSTS["usagov"])
        return "usagov"
    govpage.page_url(url)
    return "govpage"


args_flatten_used = True


def flatten_strings(v):
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        v = v.get("value", list(v.values()))
    return [x for item in (v if isinstance(v, list) else []) for x in flatten_strings(item)]


def pick(demand, out, *, per_channel=3, used_path=None, client_factory=None, cfg=None):
    if type(per_channel) is not int or per_channel < 1:
        raise PipelineError("--per-channel must be a positive integer")
    if not isinstance(demand, dict) or not isinstance(demand.get("pages"), list):
        raise PipelineError("demand.json must contain a pages array")
    used_path = Path(used_path) if used_path is not None else SOCIAL / "demand_used.json"
    values = read_json(used_path) if used_path.exists() else []
    if args_flatten_used and used_path != SOCIAL / "demand_used.json":
        values = flatten_strings(values)  # 09.11.2026: Windows PowerShell wrote the PC's list as {"value": [...]}
    if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
        raise PipelineError("demand_used.json must be an array of URL strings")
    used = {identity(v) for v in values}
    out = Path(out)
    cfg = cfg if cfg is not None else read_json(SOCIAL / "config.json")
    rows, skipped, picks, seen = [], [], [], set(used)
    for row in demand["pages"]:
        if not isinstance(row, dict):
            raise PipelineError("Every demand page must be an object")
        url, channel, views = row.get("url"), row.get("channel"), row.get("views_30d")
        if (not isinstance(channel, str) or channel not in CHANNELS or type(views) not in (int, float) or
                (type(views) is float and not math.isfinite(views)) or views < 0):
            skipped.append({"url": url, "reason": "invalid channel or views_30d"})
            continue
        try:
            source = source_for(url)
        except (PipelineError, ValueError) as error:
            skipped.append({"url": url, "reason": str(error)})
            continue
        rows.append((views, url, channel, source))
    rows.sort(key=lambda row: (-row[0], row[1], row[2]))
    counts = {channel: 0 for channel in CHANNELS}
    for views, url, channel, source in rows:
        key = identity(url)
        if key in seen:
            skipped.append({"url": url, "reason": "already used or duplicate"})
            continue
        if counts[channel] >= per_channel:
            continue
        seen.add(key)
        bundle = out / "bundles" / sha256_bytes(key.encode())[:16]
        try:
            factory = client_factory or (lambda kind, directory: (
                govpage.GovPageClient(directory) if kind == "govpage" else usagov.USAGovClient(directory)))
            if client_factory is None:
                time.sleep(2)  # 08.11.2026: bursts of requests to one site failed live; be gentle
            client = factory(source, bundle / "source")
            record, receipt = client.page(url)
            # USA.gov shares its existing structural parser; demand still needs real prose.
            if len(record["description"]) < 250 or len(record["description"].split()) < 45:
                raise PipelineError("Too little readable main text")
            record["channel"] = channel
            record["rubric"] = CHANNELS[channel]
            claims = (govpage if source == "govpage" else usagov).build_claims(record, receipt)
            result = write_bundle(record, claims, bundle, cfg)
            if result.get("request_refused"):
                raise PipelineError("Complete facts do not fit the existing concept limits")
        except (PipelineError, OSError, ValueError) as error:
            skipped.append({"url": url, "reason": str(error)})
            continue
        counts[channel] += 1
        picks.append({"url": url, "channel": channel, "views": views, "source_type": source,
                      "bundle": bundle.relative_to(out).as_posix()})
    result = {"kind": "SOCIAL_DEMAND_PICKS", "picks": picks, "skipped": skipped,
              "per_channel": per_channel, "model_called": False,
              "limitations": ["Popularity is not eligibility or evidence of current availability.",
                               "HTML format not checked live; refused pages are skipped."]}
    write_json(out / "picks.json", result)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("demand", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--per-channel", type=int, default=3)
    ap.add_argument("--used", type=Path, help="JSON array of page URLs already used (default social/demand_used.json)")
    args = ap.parse_args(argv)
    try:
        result = pick(read_json(args.demand), args.out, per_channel=args.per_channel, used_path=args.used)
    except (PipelineError, OSError, ValueError) as error:
        print(f"DEMAND PICK FAILED: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"picks": len(result["picks"]), "file": str(args.out / "picks.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
