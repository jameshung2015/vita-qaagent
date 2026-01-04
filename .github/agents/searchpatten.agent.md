---
description: 'Search similar test cases via ES or local JSONL and produce diffs.'
tools:
	- cli: 'python cli/main.py search --query "..." --project <name>'
	- es: 'Elasticsearch more_like_this / multi_match (optional)'
---

What it does:
- Finds similar test cases using Elasticsearch when configured; otherwise falls back to local `outputs/testcases/*_es_docs_*.jsonl`.
- Compares differences across `title`, `steps`, and `expected_result` and reports similarity scores and unified diffs.

When to use:
- You have a new test case, keyword, or `case_id` and want to locate near-duplicates or inspirations.
- You need a quick diff analysis to merge, refactor, or de-duplicate cases.

Inputs:
- `query` (text) or `case_id` (existing case identifier).
- Optional `project` to help locate local JSONL fallback.
- Optional `top_k` for result count.

Outputs:
- Markdown summary in `outputs/reports/search_summary_*.md`.
- JSON details in `outputs/reports/search_results_*.json` including per-field similarity and diffs.

Progress & boundaries:
- Streams concise CLI progress; shows TopK hits and key scores.
- Does not modify indexed data or files; read-only search and diff.
- No PII expansion or web scraping; uses ES or local artifacts only.

Quick start:
- Local fallback:
	`python cli/main.py search --query "乘员识别 正常流程" --project 识人识物_用例设计原则与示例 --top-k 5`
- By case id:
	`python cli/main.py search --case-id case_8b52ec47835f --project 识人识物_用例设计原则与示例`

Configure ES in `config/.env` with `ES_HOST` and `ES_INDEX` (+ auth) to enable remote search.