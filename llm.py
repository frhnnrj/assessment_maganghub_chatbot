"""Minimal Gemini client with backoff and fallback model."""
import os
import time

# Load .env file jika ada (tidak wajib, bisa juga export manual)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class FatalAPIError(Exception):
    """Auth/config/model errors that retrying cannot fix."""


class TransientAPIError(Exception):
    """Overload/timeouts that persisted after retries and fallbacks."""


MODEL = os.getenv("MODEL", "gemini-flash-lite-latest")
FALLBACKS = [m.strip() for m in os.getenv("FALLBACK_MODELS", "gemini-flash-latest").split(",") if m.strip()]


def _post(url, headers, body, tries=4, timeout=60):
    import requests

    delay, last = 5, ""
    for i in range(1, tries + 1):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
            if r.status_code not in (429, 500, 502, 503, 504):
                return r
            last = f"HTTP {r.status_code}"
        except (requests.Timeout, requests.ConnectionError) as exc:
            last = type(exc).__name__
        print(f"  transient error ({last}), attempt {i}/{tries}")
        if i < tries:
            time.sleep(delay)
            delay *= 2
    raise TransientAPIError(last)


def call_llm(system: str, user: str, temperature: float = 0.4) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise FatalAPIError("GEMINI_API_KEY belum di-set.")
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"},
    }
    last = None
    for model in [MODEL] + [m for m in FALLBACKS if m != MODEL]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = _post(url, headers, body)
        except TransientAPIError as exc:
            last = exc
            print(f"Model '{model}' sibuk ({exc}); mencoba model cadangan.")
            continue
        if r.status_code == 404:
            print(f"Model '{model}' tidak ditemukan (404).")
            continue
        if r.status_code in (400, 401, 403):
            raise FatalAPIError(f"Gemini API {r.status_code}: {r.text[:300]}")
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    raise TransientAPIError(f"semua model gagal/sibuk: {last}")
