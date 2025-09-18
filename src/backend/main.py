from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent_graph import run_search, stream_search
from .config import require_env  # ensures .env is loaded early

app = FastAPI(title="NaviSmart AI Opportunity Search PoC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str


@app.get("/health")
async def health() -> Dict[str, Any]:
    # Validate critical env keys exist for clearer error messages
    status = "ok"
    try:
        require_env("OPENAI_API_KEY")
        require_env("PERPLEXITY_API_KEY")
    except Exception as e:
        status = f"env_error: {e}"
    return {"status": status}


@app.post("/api/search")
async def api_search(req: SearchRequest) -> Dict[str, Any]:
    outcome = run_search(req.query)
    return {
        "query": outcome.get("query"),
        "steps": outcome.get("steps", []),
        "opportunities": outcome.get("opportunities", []),
        "result_markdown": outcome.get("result_markdown", ""),
    }


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    query: str | None = None
    try:
        # First message should contain the query, or use query param ?q=
        params_q = ws.query_params.get("q")
        if params_q:
            query = params_q
        else:
            first = await ws.receive_text()
            try:
                data = json.loads(first)
                query = str(data.get("query") or "").strip()
            except Exception:
                query = first.strip()

        if not query:
            await ws.send_text(json.dumps({"type": "error", "message": "Missing query"}))
            await ws.close()
            return

        await ws.send_text(json.dumps({"type": "ack", "query": query}))

        for event in stream_search(query):
            await ws.send_text(json.dumps(event))

    except WebSocketDisconnect:
        return
    except Exception as e:
        await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        try:
            await ws.close()
        except Exception:
            pass

# Serve the static frontend
app.mount("/ui", StaticFiles(directory="src/frontend", html=True), name="ui")
