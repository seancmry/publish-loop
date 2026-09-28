#!/usr/bin/env python3
"""Fake lab run for Publish Loop — saved sample only, no Firecrawl, no Peec live call.

Writes docs/lab.html, catalog, results, overview, report.html, and experiment-results.json.
Then run: python scripts/make_lab_pdf.py
"""

from __future__ import annotations

import json
from pathlib import Path

from loop import decide, peec_index

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
OUT_JSON = DOCS / "experiment-results.json"
OUT_HTML = DOCS / "lab.html"

# Demo catalog. Some are “happy path”, some are held on purpose.
CASES = [
    {
        "label": "Berlin taxes (DE)",
        "page_meta": {
            "content_id": "cnt_steuern_berlin",
            "locale": "de",
            "url": "https://example.com/de/steuern-berlin",
            "expected_canonical": "https://example.com/de/steuern-berlin",
        },
        "fetched": {
            "title": "Steuern in Berlin",
            "body": "Kurzüberblick zur Berliner Steuerlage.",
            "canonical": "https://example.com/de/steuern-berlin",
            "json_ld": {"url": "https://example.com/de/steuern-berlin"},
        },
        "in_sample_report": True,
    },
    {
        "label": "Berlin taxes (EN)",
        "page_meta": {
            "content_id": "cnt_steuern_berlin",
            "locale": "en",
            "url": "https://example.com/en/taxes-berlin",
            "expected_canonical": "https://example.com/en/taxes-berlin",
        },
        "fetched": {
            "title": "Taxes in Berlin",
            "body": "A short overview of Berlin tax basics.",
            "canonical": "https://example.com/en/taxes-berlin",
            "json_ld": {"url": "https://example.com/en/taxes-berlin"},
        },
        "in_sample_report": False,
    },
    {
        "label": "Home office (DE)",
        "page_meta": {
            "content_id": "cnt_home_office",
            "locale": "de",
            "url": "https://example.com/de/homeoffice",
            "expected_canonical": "https://example.com/de/homeoffice",
        },
        "fetched": {
            "title": "Homeoffice absetzen",
            "body": "Wann das Arbeitszimmer zählt.",
            "canonical": "https://example.com/de/homeoffice",
            "json_ld": {"url": "https://example.com/de/homeoffice"},
        },
        "in_sample_report": True,
    },
    {
        "label": "Filing deadline (EN)",
        "page_meta": {
            "content_id": "cnt_elster",
            "locale": "en",
            "url": "https://example.com/en/filing-deadline",
            "expected_canonical": "https://example.com/en/filing-deadline",
        },
        "fetched": {
            "title": "Filing deadline",
            "body": "The deadline is 31 July.",
            "canonical": "https://example.com/en/filing-deadline",
            "json_ld": {"url": "https://example.com/en/filing-deadline"},
        },
        "in_sample_report": False,
    },
    {
        "label": "Empty page",
        "page_meta": {
            "content_id": "cnt_empty",
            "locale": "de",
            "url": "https://example.com/de/steuern-berlin",
            "expected_canonical": "https://example.com/de/steuern-berlin",
        },
        "fetched": {
            "title": "Steuern in Berlin",
            "body": "",
            "canonical": "https://example.com/de/steuern-berlin",
            "json_ld": {"url": "https://example.com/de/steuern-berlin"},
        },
        "in_sample_report": True,
    },
    {
        "label": "Wrong hidden label",
        "page_meta": {
            "content_id": "cnt_bad_label",
            "locale": "de",
            "url": "https://example.com/de/steuern-berlin",
            "expected_canonical": "https://example.com/de/steuern-berlin",
        },
        "fetched": {
            "title": "Steuern in Berlin",
            "body": "Text is fine.",
            "canonical": "https://example.com/de/steuern-berlin",
            "json_ld": {"url": "https://example.com/de/other-page"},
        },
        "in_sample_report": True,
    },
    {
        "label": "Wrong public address on page",
        "page_meta": {
            "content_id": "cnt_bad_canon",
            "locale": "de",
            "url": "https://example.com/de/steuern-berlin",
            "expected_canonical": "https://example.com/de/steuern-berlin",
        },
        "fetched": {
            "title": "Steuern in Berlin",
            "body": "Text is fine.",
            "canonical": "https://example.com/de/somewhere-else",
            "json_ld": {"url": "https://example.com/de/steuern-berlin"},
        },
        "in_sample_report": True,
    },
    {
        "label": "Missing how-often-named score",
        "page_meta": {
            "content_id": "cnt_no_rate",
            "locale": "de",
            "url": "https://example.com/de/kirchensteuer",
            "expected_canonical": "https://example.com/de/kirchensteuer",
        },
        "fetched": {
            "title": "Kirchensteuer",
            "body": "Die Kirchensteuer steht auf dem Bescheid.",
            "canonical": "https://example.com/de/kirchensteuer",
            "json_ld": {"url": "https://example.com/de/kirchensteuer"},
        },
        "in_sample_report": "no_rate",
    },
]


def plain_reasons(reasons: list[str]) -> str:
    known = {
        "empty body": "The page has no text, so it stays held.",
        "address missing from Peec report": "This address is not in the report, so it stays held.",
        "citation_rate missing from report": "The report lists the page, but not how often it was named, so it stays held.",
        "missing hidden label (json_ld.url)": "The hidden label is missing, so it stays held.",
    }
    out = []
    for r in reasons:
        if r in known:
            out.append(known[r])
        elif r.startswith("hidden label mismatch"):
            out.append("The hidden label does not match the address, so it stays held.")
        elif r.startswith("canonical mismatch"):
            out.append("The public address on the page does not match what we expected, so it stays held.")
        else:
            out.append(r)
    if not out:
        return "The page and the report match, so it can go live."
    return " ".join(out)


def run_cases() -> list[dict]:
    peec = peec_index()
    # Extra row: address present but no score (held).
    peec["https://example.com/de/kirchensteuer"] = {
        "url": "https://example.com/de/kirchensteuer",
        "mentions": 12,
        "citations": None,
        "citation_rate": None,
    }

    results = []
    for case in CASES:
        decision = decide(case["page_meta"], case["fetched"], peec)
        results.append(
            {
                "label": case["label"],
                "content_id": case["page_meta"]["content_id"],
                "locale": case["page_meta"]["locale"],
                "url": case["page_meta"]["url"],
                "status": decision["status"],
                "reasons": decision["reasons"],
                "why": plain_reasons(decision["reasons"]),
                "citation_rate": (decision.get("peec") or {}).get("citation_rate"),
                "in_sample_report": case["in_sample_report"],
            }
        )
    return results


def write_html(results: list[dict]) -> None:
    def cell(value: object) -> str:
        text = "—" if value is None else str(value)
        return text.replace("&", "&amp;").replace("<", "&lt;")

    catalog_rows = []
    result_rows = []
    for item in results:
        badge = "ship" if item["status"] == "ship" else "hold"
        decision = "Can go live" if item["status"] == "ship" else "Held back"
        catalog_rows.append(
            "<tr>"
            f"<td>{cell(item['label'])}</td>"
            f"<td>{cell(item['locale'])}</td>"
            f"<td>{cell(item['url'].removeprefix('https://example.com'))}</td>"
            f"<td>{cell(item['citation_rate'])}</td>"
            "</tr>"
        )
        result_rows.append(
            "<tr>"
            f"<td>{cell(item['label'])}</td>"
            f"<td class='{badge}'>{cell(decision)}</td>"
            f"<td>{cell(item['why'])}</td>"
            "</tr>"
        )

    shipped = sum(1 for item in results if item["status"] == "ship")
    held = len(results) - shipped
    style = """
    @font-face { font-family: Geist; src: url("fonts/Geist-Regular.woff2") format("woff2"); font-weight: 400; }
    @font-face { font-family: Geist; src: url("fonts/Geist-SemiBold.woff2") format("woff2"); font-weight: 600; }
    body { font-family: Geist, sans-serif; margin: 28px auto; max-width: 980px; color: #111; background: #fff; }
    h1 { font-weight: 600; font-size: 28px; margin-bottom: 4px; color: #111; }
    h2 { font-weight: 600; font-size: 20px; margin-top: 28px; color: #0a5f8a; }
    p { line-height: 1.45; }
    table { width: 100%; border-collapse: collapse; background: #fff; }
    th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #e6e6e6; font-size: 14px; }
    th { background: #0a5f8a; color: white; font-weight: 600; }
    .ship { color: #067a3a; font-weight: 600; }
    .hold { color: #d01212; font-weight: 600; }
    .tiles { display: flex; gap: 16px; margin: 16px 0 8px; }
    .tile { background: #f0f7fb; padding: 16px 20px; min-width: 140px; border-top: 4px solid #0a5f8a; }
    .tile b { display: block; font-size: 28px; }
"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Publish Loop lab</title>
  <style>{style}</style>
</head>
<body>
  <h1>Should this page go live?</h1>
  <p>We checked {len(results)} pages with a saved sample report. Nothing here calls the live web or a live naming report. The loop still does the same job: fetch facts, run the check, keep a written decision.</p>
  <div class="tiles">
    <div class="tile"><b>{shipped}</b>can go live</div>
    <div class="tile"><b>{held}</b>held back</div>
  </div>
  <h2 id="catalog">The pages</h2>
  <table>
    <thead><tr><th>Page</th><th>Language</th><th>Address</th><th>How often named</th></tr></thead>
    <tbody>
      {''.join(catalog_rows)}
    </tbody>
  </table>
  <h2 id="results">What we decided</h2>
  <table>
    <thead><tr><th>Page</th><th>Decision</th><th>Why</th></tr></thead>
    <tbody>
      {''.join(result_rows)}
    </tbody>
  </table>
</body>
</html>
"""
    DOCS.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html)
    head = html.split("<body>")[0] + "<body>\n"
    catalog_html = html.split('<h2 id="results">')[0] + "</body></html>\n"
    results_html = head + '<h2 id="results">' + html.split('<h2 id="results">')[1]
    (DOCS / "catalog.html").write_text(catalog_html)
    (DOCS / "results.html").write_text(results_html)

    (DOCS / "overview.html").write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Overview</title>
  <style>
    @font-face { font-family: Geist; src: url("fonts/Geist-Regular.woff2") format("woff2"); font-weight: 400; }
    @font-face { font-family: Geist; src: url("fonts/Geist-SemiBold.woff2") format("woff2"); font-weight: 600; }
    body { font-family: Geist, sans-serif; margin: 24px; background: #fff; color: #111; }
    h1 { font-size: 18px; font-weight: 600; margin: 0 0 16px; }
    .row { display: flex; align-items: stretch; gap: 12px; }
    .card { flex: 1; background: #f0f7fb; border-top: 4px solid #0a5f8a; padding: 14px 16px; }
    .card b { display: block; color: #0a5f8a; font-size: 13px; margin-bottom: 6px; }
    .card p { margin: 0; font-size: 15px; line-height: 1.35; }
    .plus, .arrow { align-self: center; color: #0a5f8a; font-weight: 600; font-size: 22px; }
    .go { flex: 0.9; background: #e9f8ef; border-top: 4px solid #067a3a; }
    .go b { color: #067a3a; }
  </style>
</head>
<body>
  <h1>A page goes live only when the loop finishes cleanly</h1>
  <div class="row">
    <div class="card"><b>Fetch the page</b><p>Read the live address, text, and hidden label.</p></div>
    <div class="plus">+</div>
    <div class="card"><b>Check the report</b><p>Was this address named, and is the score there?</p></div>
    <div class="plus">+</div>
    <div class="card"><b>Write it down</b><p>Keep a clear ship or hold decision in the audit log.</p></div>
    <div class="arrow">→</div>
    <div class="card go"><b>Can go live</b><p>Or stay held, with a reason anyone can read.</p></div>
  </div>
</body>
</html>
"""
    )

    (DOCS / "report.html").write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Publish Loop — a short note</title>
  <style>
    @font-face {{ font-family: Geist; src: url("fonts/Geist-Regular.woff2") format("woff2"); font-weight: 400; }}
    @font-face {{ font-family: Geist; src: url("fonts/Geist-SemiBold.woff2") format("woff2"); font-weight: 600; }}
    @page {{ margin: 14mm 14mm 16mm; }}
    body {{ font-family: Geist, sans-serif; margin: 0 auto; max-width: 860px; color: #111; }}
    h1 {{ font-weight: 600; color: #111; margin: 0 0 8px; font-size: 28px; }}
    h2 {{ font-weight: 600; color: #0a5f8a; margin: 0 0 8px; font-size: 20px; }}
    p, li {{ line-height: 1.45; }}
    code {{ font-family: ui-monospace, monospace; font-size: 0.92em; }}
    .keep {{ break-inside: avoid; page-break-inside: avoid; }}
    .results {{ break-before: page; page-break-before: always; }}
    .notes {{ break-before: page; page-break-before: always; }}
    img {{ width: 100%; border: 1px solid #e6e6e6; }}
  </style>
</head>
<body>
  <h1>Should this page go live?</h1>
  <p>We checked {len(results)} pages against a saved sample report. Nothing here calls the live web. The page cannot know whether it was named. The report can. The loop waits for both before it says ship or hold.</p>
  <p>A page can go live when its address, text, and hidden label agree with the report. How often it was named can be low. A missing score holds it back. Every decision is written to an audit log you can open later.</p>
  <section class="keep">
    <img src="images/overview.png" alt="How the loop works">
  </section>
  <section class="keep">
    <img src="images/catalog.png" alt="The pages we checked">
  </section>
  <section class="keep results">
    <img src="images/results.png" alt="What the check decided">
  </section>
  <section class="notes">
    <h2>What this is worth</h2>
    <ul>
      <li>Publishing stops being a gut feel. The page and the naming report have to agree first.</li>
      <li>A low “how often named” score still lets a page go live. A missing score does not. That difference is easy to miss by hand.</li>
      <li>Empty text, a wrong hidden label, or a wrong public address hold the page before the report is even used.</li>
      <li>Each run leaves a written trail. You can show a teammate why something stayed held without opening five tabs.</li>
    </ul>
    <p>Run the check again with <code>python experiments.py</code>. For a live fetch later, use <code>python loop.py --live</code> with a Firecrawl key.</p>
  </section>
</body>
</html>
"""
    )


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    results = run_cases()
    OUT_JSON.write_text(json.dumps(results, indent=2) + "\n")
    write_html(results)
    for item in results:
        print(f"{item['status']:4}  {item['locale']}  {item['label']}  — {item['why']}")


if __name__ == "__main__":
    main()
