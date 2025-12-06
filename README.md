# Competitor Analysis Engine (Insight-First Baseline)

This project turns competitor websites into actionable competitive intelligence. It scrapes target pages (Playwright or requests), derives dynamic technical/value terms from the content itself, computes sentiment and messaging mix, and produces artifacts (CSV/XLSX, charts, Markdown) plus a JSON summary that’s compatible with Hummingbird-style “runs” and “artifacts.”

**Key capabilities**
- JS-capable scraping (Playwright) with polite delays/retries.
- Dynamic term extraction (no pre-baked keyword lists): nouns → technical, adjectives/adverbs/verbs → value.
- Per-competitor sentiment, tech/value mix, top props/keywords, cards view.
- Artifacts: run-level CSV/XLSX (multi-sheet), per-competitor CSVs, keyword distribution chart with annotations, sentiment chart, enriched Markdown report.
- File-backed store (`store.json`) for runs/artifacts (prototype).

## Quickstart (CLI)

1) Install deps & browsers (one time):
```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

2) Set env (Playwright backend by default via `.env`):
```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
export PYTHONPATH=.
mkdir -p "$HOME/tmp"
export TMPDIR="$HOME/tmp"
export MPLCONFIGDIR="$HOME/tmp"
```

3) Run:
```bash
python -m competitor_analysis.cli \
  --project ws1 \
  --hum hum1 \
  --name demo-run \
  --base https://openai.com \
  --competitors competitors_config.json \
  --output competitor_content
```

Outputs: `competitor_content/{runId}/` (CSV, XLSX with sheets, per-competitor CSVs, keyword/sentiment PNGs, Markdown report) and run record in `competitor_content/store.json`.

## API (FastAPI)

Start server:
```bash
uvicorn competitor_analysis.api:app --reload
```

Endpoints (internal prototype):
- `POST /internal/competitor-analysis/runs` (body: projectId, humId, seriesBaseUrl, competitors[], settings, sync?)
- `GET  /internal/competitor-analysis/runs/{id}`
- `GET  /internal/competitor-analysis/runs/{id}/artifacts`
- `GET  /internal/competitor-analysis/runs/{id}/cards`
- `GET  /internal/competitor-analysis/runs` (list by projectId/humId)
- Minimal landscape/trends HTML (prototype): `uvicorn competitor_analysis.ui_server:app --reload` then open `/landscape/{runId}` or `/trends/{runId}` (debug views).

Auth: set `COMPETITOR_API_KEY` and send header `X-API-Key`.

## Configuration

Environment (see `.env`):
- `COMPETITOR_SCRAPER_BACKEND=playwright` (default) | requests
- `COMPETITOR_OUTPUT_DIR` (default `competitor_content`)
- `COMPETITOR_STORE_PATH` (default `competitor_content/store.json`)
- `COMPETITOR_SCRAPER_TIMEOUT`, `COMPETITOR_SCRAPER_RETRIES`, `COMPETITOR_SCRAPER_DELAY`, `COMPETITOR_SCRAPER_MAX_PAGES`, `COMPETITOR_SCRAPER_MAX_ELEMENTS`
- `COMPETITOR_USER_AGENT`
- Optional: embeddings/KeyBERT (`COMPETITOR_USE_EMBEDDINGS`, `COMPETITOR_USE_KEYBERT`, models)
- `COMPETITOR_YOUR_TERMS` (comma-separated) to compute overlap/differentiation vs your own messaging

Competitor config (`competitors_config.json`):
```json
{
  "competitors": [
    {"id": "me", "name": "OpenAI", "baseUrl": "https://openai.com", "priorityPages": ["/", "/agent-platform", "/business"]},
    {"id": "rival1", "name": "Claude", "baseUrl": "https://claude.com", "priorityPages": ["/", "/solutions/coding", "/solutions/agents", "/platform/api"]},
    {"id": "rival2", "name": "Google", "baseUrl": "https://gemini.google", "priorityPages": ["/", "/about", "/overview/deep-research", "/overview/video-generation", "/overview/image-generation"]}
  ]
}
```

## How it works (pipeline)
1. Scrape pages (Playwright or requests+BS4); extract h1/h2/h3/p.
2. Dynamic term extraction from corpus (POS-tagged nouns → technical, adjectives/adverbs/verbs → value).
3. Per-chunk sentiment (VADER) + keyword counts + intent classification; add cleaned_text.
4. Aggregate to summaryJson:
   - sentiment buckets, tech/value totals, top props/keywords, competitor cards (sentiment category, tech/value mix, top technical concepts), optional positioning/overlap when enabled.
5. Export artifacts: CSV/XLSX (Raw, Summary, Intent, Sentiment, Top Keywords), per-competitor CSVs, keyword distribution PNG (annotated), sentiment PNG, Markdown report (with intent mix, sentiment, tech/value mix, overlap info).

## Logs & Store
- Prototype persistence: JSON file at `COMPETITOR_STORE_PATH`.
- Outputs: `COMPETITOR_OUTPUT_DIR/{runId}/...`.

## Known considerations
- Playwright is recommended for JS-heavy sites; requests may miss content.
- Some sites block scraping; consider adding proxies/headers or ignoring robots (not enabled by default).
- LibreSSL warning from urllib3 can be ignored for scraping.

## Development
- Tests: `PYTHONPATH=. TMPDIR=$HOME/tmp MPLCONFIGDIR=$HOME/tmp pytest tests -q --cache-clear`
- Requirements: see `requirements.txt` (Playwright, pandas, matplotlib, nltk, sentence-transformers, keybert, scikit-learn, fastapi/uvicorn).

## Roadmap (insight-first)
- Positioning map and overlap/differentiation surfaced in UI.
- Trends (emerging/fading themes over time).
- GPT-generated executive summary and differentiation recommendations as artifacts.
- Optional embeddings/KeyBERT already wired; enable via env to experiment.
