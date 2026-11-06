"""Gemini Embedding API client.

Embeds text using text-embedding-004 (768-dim).
Handles batching and retry with the same backoff logic as llm.py.
"""
import os
import time

import requests

# Load .env otomatis
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

EMBED_MODEL = "gemini-embedding-001"
TASK_TYPE_DOC = "RETRIEVAL_DOCUMENT"
TASK_TYPE_QUERY = "RETRIEVAL_QUERY"
BATCH_SIZE = 100


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    if not key:
        raise RuntimeError("GEMINI_API_KEY belum di-set. Tambahkan ke file .env atau Streamlit Secrets")
    return key


def _embed_url(key: str) -> str:
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{EMBED_MODEL}:batchEmbedContents?key={key}"
    )


def _post_with_retry(url: str, body: dict, tries: int = 4) -> dict:
    headers = {"Content-Type": "application/json"}
    delay = 5
    last = ""
    for i in range(1, tries + 1):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=60)
            if r.status_code not in (429, 500, 502, 503, 504):
                r.raise_for_status()
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except (requests.Timeout, requests.ConnectionError) as exc:
            last = str(exc)
        print(f"  [embed] transient error ({last}), attempt {i}/{tries}")
        if i < tries:
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"Embedding API gagal setelah {tries} percobaan: {last}")


def embed_texts(texts: list[str], task_type: str = TASK_TYPE_DOC) -> list[list[float]]:
    """Embed a list of texts. Returns list of float vectors (768-dim)."""
    key = _api_key()
    url = _embed_url(key)
    all_embeddings = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        body = {
            "requests": [
                {
                    "model": f"models/{EMBED_MODEL}",
                    "content": {"parts": [{"text": t}]},
                    "taskType": task_type,
                }
                for t in batch
            ]
        }
        result = _post_with_retry(url, body)
        for item in result["embeddings"]:
            all_embeddings.append(item["values"])

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([text], task_type=TASK_TYPE_QUERY)[0]

