# Variable schema — Publish Loop

**System map:** page queue → fetch (fixture | Firecrawl) → Peec report match → ship/hold → `out/audit.jsonl` (optional Supabase / Sheet / Linear later).

## Headline card

| Knob | Plain English |
|------|----------------|
| **`fixtures/pages.json`** | The queue of URLs to check (the “what should we publish?” list). |
| **`fixtures/live-pages.json`** | Fake live fetches so the demo runs with no API key. |
| **`fixtures/peec-urls.json`** | Stand-in for “was this URL named?” (same idea as content-gate). |
| **`--live`** | Use Firecrawl on the real web instead of the fake fetch store. |
| **`FIRECRAWL_API_KEY`** | Password for live fetches. Stays in `.env`. |
| **`out/audit.jsonl`** | Append-only log of every decision (the demo’s system of record). |

## Knobs

| Name | Type | Required? | Job | If wrong / missing |
|------|------|-----------|-----|--------------------|
| `--url` | text | no | Check one address | Defaults to every row in `pages.json` |
| `--live` | flag | no | Call Firecrawl | Without a key, the script exits |
| `--json` | flag | no | Machine-readable stdout | Human table is printed instead |
| `FIRECRAWL_API_KEY` | text | only with `--live` | Auth for scrape API | Live fetch cannot run |
| `SUPABASE_URL` / `SUPABASE_SECRET_KEY` | text | later | Write decisions into the content-gate project | Local audit still works |
| `AUDIT_SHEET_ID` | text | later | Append a Sheet row via MCP / script | Local audit still works |
| `fixtures/pages.json` | file | yes (unless `--url` ad-hoc) | Queue | Nothing to check |
| `fixtures/live-pages.json` | file | offline mode | Fake HTML extract | Offline URL not in store → exit |
| `fixtures/peec-urls.json` | file | yes | Visibility report sample | Every URL looks unnamed → all HOLD |

## Decision fields (written to audit)

| Name | Type | Job |
|------|------|-----|
| `status` | `ship` \| `hold` | Can go live or not |
| `reasons` | list of text | Why it held (empty when ship) |
| `peec.citation_rate` | number \| null | Named / found; **missing** holds, **low** still ships |
| `checked_at` | ISO time | When this loop ran |

## Relation to content-gate

Same judgment family (address + hidden label + report row). content-gate owns the rule deep-dive and Supabase `apply_check`. Publish Loop owns the **agent-operated loop**: fetch → decide → audit trail. Do not treat this as a second Peec product.
