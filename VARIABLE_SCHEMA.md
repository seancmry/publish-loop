# Inputs

Page queue, then fetch, then the naming-report match, then one line in `out/audit.jsonl`.

The judgment is the same family as content-gate: address, hidden label, and a report row. content-gate owns that rule and the Supabase `apply_check` function. This repo owns the run and the log.

## Knobs

| Name | Required | What it does |
| --- | --- | --- |
| `fixtures/pages.json` | yes, unless you pass `--url` | Queue of addresses. |
| `fixtures/live-pages.json` | for the offline run | Saved page extracts. An address that is not in here stops the offline run. |
| `fixtures/peec-urls.json` | yes | Saved naming report. With no row, every address is held. |
| `--url` | no | Check one address. |
| `--live` | no | Fetch with Firecrawl instead of the saved extracts. |
| `--json` | no | Machine-readable stdout. Otherwise a table is printed. |
| `FIRECRAWL_API_KEY` | only with `--live` | Stays in `.env`. |
| `out/audit.jsonl` | written | Append-only log of every decision. |

`SUPABASE_URL` and `SUPABASE_SECRET_KEY` can write the same decision into the content-gate project later. The local audit log still works without them.

## A line in the log

| Field | Meaning |
| --- | --- |
| `status` | `ship` or `hold`. |
| `reasons` | Why it held. Empty when it ships. |
| `peec.citation_rate` | Named divided by found. Missing holds. Low still ships. |
| `checked_at` | When this loop ran. |
