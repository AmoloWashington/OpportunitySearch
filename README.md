# NaviSmart AI · Automated Opportunity Search (LangGraph + APIChain PoC)

Minimal, standalone PoC demonstrating a LangGraph agent that uses LangChain's APIChain to call external APIs (Perplexity for research and OpenAI for analysis), streams progress to a simple HTML UI, and returns scored opportunities.

## Features

- LangGraph as the sole orchestrator (input → research via Perplexity → analysis via OpenAI → aggregation/scoring → finalize)
- LangChain APIChain used inside graph nodes to call:
  - Perplexity Chat Completions API for web exploration
  - OpenAI Chat Completions API for structured analysis
- .env-based configuration with python-dotenv
- FastAPI backend exposing:
  - REST: POST /api/search
  - WebSocket: /ws (streams stepwise progress)
- Plain HTML/CSS/JS frontend (no frameworks)
- In-memory only; no persistence

## Project Structure

```
src/
  backend/
    agent_graph.py   # LangGraph + APIChain agent implementation
    config.py        # Loads .env and provides env utilities
    main.py          # FastAPI app with REST + WebSocket
  frontend/
    index.html
    styles.css
    app.js
requirements.txt
.env.example
README.md
```

## Setup

1) Python environment
- Python 3.10+
- Create and activate a virtualenv

```
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
```

2) Install dependencies
```
pip install -r requirements.txt
```

3) Configure environment
- Copy .env.example to .env and set your keys
```
OPENAI_API_KEY=...
PERPLEXITY_API_KEY=...
LANGCHAIN_API_KEY=...
```

4) Run the server
```
uvicorn src.backend.main:app --reload --port 8000
```

5) Open the UI
- Navigate to http://localhost:8000/ui/ (static files are served by FastAPI)

## How It Works

- agent_graph.py builds two APIChains (Perplexity, OpenAI) using RequestsWrapper with Authorization headers from .env
- The LangGraph pipeline:
  1. input: read/normalize query
  2. research: APIChain → Perplexity /chat/completions to collect opportunities (JSON)
  3. analyze: APIChain → OpenAI /chat/completions to structure and enrich as opportunities with scores
  4. aggregate: parse/normalize and heuristic score fallback; sort top results
  5. finalize: format result markdown
- FastAPI exposes /api/search and /ws for streaming updates
- Frontend connects to /ws and renders live steps + results

## Notes

- All processing is in-memory; no DB used
- API keys are read only from environment, not hard-coded
- LangSmith/advanced tracing is excluded

## UI usage guide

- Enter a query and submit. Live progress updates appear on the left.
- Results: each item is selectable via checkbox; links are clickable and open in a new tab.
- Toolbar:
  - Select all toggles selection for the current list (respects “Show saved only” filter).
  - Apply to selected opens the source links for selected items (browser may block some popups).
  - Save selected bookmarks items for this session; toggle “Show saved only” to filter.
  - Download CSV exports the currently visible list (filtered) as opportunities.csv.

## Extending

- Add guardrails/validation for the JSON contract
- Introduce retries/backoff for API errors
- Swap models or plug additional research APIs by adding more APIChain nodes
- Add filters (region, industry) to the query form and pass through state


