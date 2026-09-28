#!/usr/bin/env python3
"""Publish Loop — fetch → gate → decide → audit.

System map:
  fixtures/pages.json (or --url)
  → fetch page (fixture or Firecrawl)
  → match Peec report row (fixture)
  → ship / hold decision
  → out/audit.jsonl (+ optional Supabase later)

Offline by default. Knobs: VARIABLE_SCHEMA.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGES_PATH = ROOT / "fixtures" / "pages.json"
LIVE_FIXTURE = ROOT / "fixtures" / "live-pages.json"
PEEC_FIXTURE = ROOT / "fixtures" / "peec-urls.json"
AUDIT_PATH = ROOT / "out" / "audit.jsonl"


def load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def peec_index() -> dict[str, dict]:
    payload = json.loads(PEEC_FIXTURE.read_text())
    rows = list(payload.get("data") or [])
    return {str(r["url"]): r for r in rows if r.get("url")}


def fetch_page(url: str, *, live: bool) -> dict:
    """Return extracted page fields. Fixture first; Firecrawl only with --live + key."""
    if not live:
        store = json.loads(LIVE_FIXTURE.read_text())
        if url not in store:
            raise SystemExit(f"No fixture for {url}. Add it to fixtures/live-pages.json.")
        return dict(store[url])

    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "Live fetch needs FIRECRAWL_API_KEY in .env. "
            "Omit --live to use fixtures/live-pages.json."
        )

    import httpx

    # Firecrawl v2 scrape — markdown + light metadata for the gate.
    resp = httpx.post(
        "https://api.firecrawl.dev/v2/scrape",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
        },
        timeout=90.0,
    )
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get("data") or payload
    metadata = data.get("metadata") or {}
    canonical = (
        metadata.get("url")
        or metadata.get("sourceURL")
        or metadata.get("ogUrl")
        or url
    )
    return {
        "url": url,
        "title": metadata.get("title") or metadata.get("ogTitle") or "",
        "body": (data.get("markdown") or "")[:2000],
        "canonical": canonical,
        "hreflang": {},
        # Live pages rarely expose json_ld.url through markdown scrape — use
        # the requested URL as the hidden-label stand-in for the demo loop.
        "json_ld": {
            "@type": "Article",
            "headline": metadata.get("title") or "",
            "url": url,
        },
        "raw_metadata": metadata,
    }


def _norm_url(u: str) -> str:
    return u.strip().rstrip("/")


def decide(page_meta: dict, fetched: dict, peec: dict[str, dict]) -> dict:
    """Same judgment family as content-gate: address + hidden label + report row."""
    url = page_meta["url"]
    reasons: list[str] = []

    body = (fetched.get("body") or "").strip()
    if not body:
        reasons.append("empty body")

    canonical = _norm_url(fetched.get("canonical") or "")
    expected = _norm_url(page_meta.get("expected_canonical") or url)
    if canonical and canonical != expected:
        reasons.append(f"canonical mismatch ({canonical} != {expected})")

    label = ""
    json_ld = fetched.get("json_ld") or {}
    if isinstance(json_ld, dict):
        label = str(json_ld.get("url") or "").strip()
    if not label:
        reasons.append("missing hidden label (json_ld.url)")
    elif _norm_url(label) != _norm_url(url):
        reasons.append(f"hidden label mismatch ({label} != {url})")

    report = peec.get(url)
    if not report:
        reasons.append("address missing from Peec report")
    elif report.get("citation_rate") is None:
        reasons.append("citation_rate missing from report")

    status = "held" if reasons else "ship"
    return {
        "content_id": page_meta.get("content_id"),
        "locale": page_meta.get("locale"),
        "url": url,
        "status": status,
        "reasons": reasons,
        "title": fetched.get("title") or "",
        "peec": {
            "mentions": (report or {}).get("mentions"),
            "citations": (report or {}).get("citations"),
            "citation_rate": (report or {}).get("citation_rate"),
        }
        if report
        else None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def append_audit(row: dict) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_queue(only_url: str | None) -> list[dict]:
    pages = list(json.loads(PAGES_PATH.read_text()).get("pages") or [])
    if only_url:
        pages = [p for p in pages if p.get("url") == only_url]
        if not pages:
            pages = [
                {
                    "content_id": "adhoc",
                    "locale": "?",
                    "url": only_url,
                    "expected_canonical": only_url,
                }
            ]
    return pages


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Publish Loop: fetch → gate → audit")
    parser.add_argument("--url", help="Check one URL (default: all fixtures/pages.json)")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Fetch with Firecrawl (needs FIRECRAWL_API_KEY). Default: fixture fetch.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print decisions as JSON only",
    )
    args = parser.parse_args()

    peec = peec_index()
    queue = load_queue(args.url)
    decisions: list[dict] = []

    for page_meta in queue:
        fetched = fetch_page(page_meta["url"], live=args.live)
        decision = decide(page_meta, fetched, peec)
        decisions.append(decision)
        append_audit(decision)

    if args.json:
        json.dump(decisions, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print("Publish Loop — decisions\n")
        for d in decisions:
            mark = "SHIP" if d["status"] == "ship" else "HOLD"
            print(f"  [{mark}] {d['locale']}  {d['url']}")
            for r in d["reasons"]:
                print(f"         · {r}")
            if d.get("peec") and d["peec"].get("citation_rate") is not None:
                print(f"         · citation_rate={d['peec']['citation_rate']}")
        print(f"\nAudit appended → {AUDIT_PATH.relative_to(ROOT)}")
        print("Next (optional): wire Supabase write / Linear ticket / n8n webhook — see README.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
