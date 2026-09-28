# Publish Loop

This is a small loop that decides whether a page is allowed to go live, then writes that decision down.

It fetches the page, checks a naming report, and keeps a clear **can go live** or **held back** answer. A saved sample stands in for the live web and the live report, so you can try the loop with no account.

![A page goes live only when the loop finishes cleanly](docs/images/overview.png)

## Why this exists

A page can tell you its address and its text. It cannot tell you whether an answer engine named that address. The report can. The loop waits for both, then leaves an audit line you can open later.

That is the value: publishing stops being a gut feel, and every hold comes with a reason a teammate can read.

## What the words mean

| Word | What it means |
| --- | --- |
| **Address** | The public link. The page and the report are matched on this. |
| **Hidden label** | A small note on the page that must repeat the same address. |
| **How often named** | Of the times the page was found, how often it was actually named. A low number does not stop the page. A missing number does. |
| **Can go live** | The page and the report match. |
| **Held back** | Something does not match, so the page stays unpublished. |
| **Audit log** | The written list of decisions in `out/audit.jsonl`. |

The full field list is in `VARIABLE_SCHEMA.md`.

## The lab (fake test)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python experiments.py
```

Eight sample pages. Some can go live. Some are held on purpose (missing from the report, empty text, wrong label, missing score).

![The pages we checked](docs/images/catalog.png)

![What the check decided](docs/images/results.png)

The same pictures, with a short note, are in [docs/publish-loop-lab.pdf](docs/publish-loop-lab.pdf).

To rebuild screenshots and the PDF after you change the lab:

```bash
pip install playwright
playwright install chromium
python scripts/make_lab_pdf.py
```

## Try one real run (still offline)

```bash
python loop.py
```

## Live fetch (optional)

Needs a Firecrawl key in `.env` (`FIRECRAWL_API_KEY`). The naming report stays the saved sample unless you wire a live report later.

```bash
python loop.py --live --url https://www.firecrawl.dev
```

## Related

[content-gate](../content-gate/) owns the deeper publish rule and database story. Publish Loop owns the **fetch → decide → write it down** path you would drive from an agent.
