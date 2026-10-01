# Publish Loop

## The problem

Someone has to decide: can this page go live? Too often that answer lives in someone’s head, or in a chat that disappears.

A page can show its address and text. A naming report can show whether answer engines named that address. Neither alone is enough — and without a written trail, the next person cannot see **why** something was held back.

**What this program does:** it runs a small loop — fetch the page → check it against a naming report → write a clear **can go live** or **held back** line into an audit log. A saved sample stands in for the live web and live report, so you can try it with no account.

![A page goes live only when the loop finishes cleanly](docs/images/overview.png)

## Who it helps

- People who publish or review web content and want a repeatable check  
- Engineers or agents that need a **fetch → decide → write it down** path  
- Teammates who need a hold reason they can open later (`out/audit.jsonl`)  

For the deeper publish rule and database story, see [content-gate](https://github.com/seancmry/content-gate). This repo owns the loop you would drive day to day.

## How to run

**Offline lab** (recommended first):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python experiments.py
```

Eight sample pages. Some can go live; some are held on purpose (missing from the report, empty text, wrong label, missing score).

![The pages we checked](docs/images/catalog.png)

![What the check decided](docs/images/results.png)

Lab PDF: [docs/publish-loop-lab.pdf](docs/publish-loop-lab.pdf).

**One offline run** (same idea, single path):

```bash
python loop.py
```

### Optional: live fetch

Needs `FIRECRAWL_API_KEY` in `.env`. The naming report stays the saved sample unless you wire a live report later.

```bash
python loop.py --live --url https://www.firecrawl.dev
```

### Rebuild lab screenshots / PDF

```bash
pip install playwright
playwright install chromium
python scripts/make_lab_pdf.py
```

---

## What the words mean

| Word | What it means |
| --- | --- |
| **Address** | Public link — page and report are matched on this. |
| **Hidden label** | Note on the page that must repeat the same address. |
| **How often named** | Of the times found, how often named. Low is OK; **missing** blocks. |
| **Can go live** | Page and report match. |
| **Held back** | Something does not match. |
| **Audit log** | Written decisions in `out/audit.jsonl`. |

Full field list: `VARIABLE_SCHEMA.md`.
