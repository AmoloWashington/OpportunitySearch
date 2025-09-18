from __future__ import annotations

import httpx

from .config import require_env


def call_openai_research(topic: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {require_env('OPENAI_API_KEY')}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert opportunity researcher. Respond ONLY with a strict JSON array.",
            },
            {
                "role": "user",
                "content": (
                    f"Research topic: {topic}. Return 5-10 opportunities as a JSON array. "
                    "Each item must have title, url, snippet. No explanations, JSON only."
                ),
            },
        ],
        "temperature": 0,
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def call_perplexity_research(topic: str) -> str:
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {require_env('PERPLEXITY_API_KEY')}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "model": "llama-3.1-sonar-large-128k-online",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Research topic: {topic}. Return 5-10 opportunities as a strict JSON array. "
                    "Each item must have title, url, snippet. No explanations, JSON only."
                ),
            }
        ],
        "temperature": 0,
    }
    with httpx.Client(timeout=60) as client:
        try:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except httpx.HTTPError:
            return call_openai_research(topic)


def call_openai_analyze(research_text: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {require_env('OPENAI_API_KEY')}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an analyst. Read the research JSON (array of opportunities) and return ONLY a strict JSON object "
                    "with key 'opportunities' (array of items with: title, summary, source, score 0-100)."
                ),
            },
            {
                "role": "user",
                "content": research_text,
            },
        ],
        "temperature": 0,
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
