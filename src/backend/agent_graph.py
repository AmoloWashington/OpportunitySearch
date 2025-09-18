from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .external import call_perplexity_research, call_openai_analyze


class AgentState(TypedDict, total=False):
    query: str
    steps: List[str]
    research_raw: str
    analysis_raw: str
    opportunities: List[Dict[str, Any]]
    result_markdown: str


def _append_step(state: AgentState, message: str) -> AgentState:
    steps = list(state.get("steps", []))
    steps.append(message)
    state["steps"] = steps
    return state




def _safe_json_extract(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except Exception:
        # Try to find JSON substring
        match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
        return None


# Graph nodes

def node_input(state: AgentState) -> AgentState:
    query = (state.get("query") or "").strip()
    state["query"] = query
    return _append_step(state, "Received query")


def node_research(state: AgentState) -> AgentState:
    query = state["query"]
    research_raw = call_perplexity_research(query)
    state["research_raw"] = research_raw
    return _append_step(state, "Completed research")


def node_analyze(state: AgentState) -> AgentState:
    research_raw = state.get("research_raw") or ""
    analysis_raw = call_openai_analyze(research_raw)
    state["analysis_raw"] = analysis_raw
    return _append_step(state, "Analyzed and structured opportunities via OpenAI API")


def node_aggregate(state: AgentState) -> AgentState:
    parsed = _safe_json_extract(state.get("analysis_raw") or "")
    items: List[Dict[str, Any]] = []
    if isinstance(parsed, dict) and isinstance(parsed.get("opportunities"), list):
        for it in parsed["opportunities"]:
            title = str(it.get("title", "")).strip()
            summary = str(it.get("summary", "")).strip()
            source = str(it.get("source", "")).strip()
            score_val = it.get("score")
            try:
                score = float(score_val) if score_val is not None else None
            except Exception:
                score = None
            items.append({"title": title, "summary": summary, "source": source, "score": score})

    # Fallback heuristic scoring if score missing
    for it in items:
        if it.get("score") is None:
            text = (it.get("summary") or "") + " " + (it.get("title") or "")
            base = 50.0
            boosts = 0.0
            keywords = {
                "market": 10,
                "growth": 10,
                "revenue": 10,
                "ai": 5,
                "partnership": 5,
                "expansion": 5,
            }
            t = text.lower()
            for k, v in keywords.items():
                if k in t:
                    boosts += v
            it["score"] = min(100.0, base + boosts)

    # Sort by score desc and keep top 8
    items.sort(key=lambda x: (x.get("score") or 0), reverse=True)
    items = items[:8]

    state["opportunities"] = items
    return _append_step(state, "Aggregated and scored opportunities")


def node_finalize(state: AgentState) -> AgentState:
    items = state.get("opportunities") or []
    lines = ["# NaviSmart AI Opportunity Search Results", ""]
    for i, it in enumerate(items, start=1):
        title = it.get("title") or "Untitled"
        summary = it.get("summary") or ""
        source = it.get("source") or ""
        score = it.get("score")
        score_txt = f"{score:.0f}" if isinstance(score, (int, float)) else "-"
        lines.append(f"{i}. {title} (Score: {score_txt})")
        if summary:
            lines.append(f"   - {summary}")
        if source:
            lines.append(f"   - Source: {source}")
        lines.append("")
    state["result_markdown"] = "\n".join(lines)
    return _append_step(state, "Compiled final results")


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("input", node_input)
    graph.add_node("research", node_research)
    graph.add_node("analyze", node_analyze)
    graph.add_node("aggregate", node_aggregate)
    graph.add_node("finalize", node_finalize)

    graph.set_entry_point("input")
    graph.add_edge("input", "research")
    graph.add_edge("research", "analyze")
    graph.add_edge("analyze", "aggregate")
    graph.add_edge("aggregate", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


def run_search(query: str) -> AgentState:
    app = build_graph()
    initial: AgentState = {"query": query, "steps": []}
    result: AgentState = app.invoke(initial)
    return result


def stream_search(query: str):
    app = build_graph()
    initial: AgentState = {"query": query, "steps": []}
    accumulated: AgentState = dict(initial)
    for event in app.stream(initial):
        # event is a dict mapping node name to state delta
        for node_name, state_delta in event.items():
            # Merge delta into accumulated state for a final snapshot
            for k, v in state_delta.items():
                accumulated[k] = v
            yield {"type": "step", "node": node_name, "state": state_delta}
    yield {"type": "final", "state": accumulated}
