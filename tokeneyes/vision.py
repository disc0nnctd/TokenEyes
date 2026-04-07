"""Vision backends for price extraction: Gemini and OpenAI-compatible hosts."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

# Free OpenRouter vision models (updated April 2026).
# openrouter/auto routes to the best available free multimodal model automatically.
OPENROUTER_FREE_MODELS = [
    "openrouter/auto",
    "qwen/qwen2.5-vl-72b-instruct:free",
    "qwen/qwen2.5-vl-32b-instruct:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]
OPENROUTER_DEFAULT_MODEL = OPENROUTER_FREE_MODELS[0]
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GEMINI_MODEL = "gemini-2.5-flash"

READ_PROMPT = """\
Look at this image carefully. Find any price tag, price label, menu price, \
receipt total, or displayed cost.

Return JSON (no markdown fencing):
{
  "item": "<short description of the item>",
  "price": <numeric price as a float>,
  "currency": "<3-letter currency code, e.g. USD, EUR, GBP>",
  "price_usd": <price converted to USD (use approximate current rates)>,
  "confidence": "read"
}

If you cannot find a visible price, return:
{"item": "<what you see>", "price": null, "currency": null, "price_usd": null, "confidence": "none"}
"""

GUESS_PROMPT = """\
Look at this image. Identify the main object or product shown.

Estimate its typical retail price in USD based on what it appears to be.

Return JSON (no markdown fencing):
{
  "item": "<short description>",
  "price": <estimated price as float>,
  "currency": "USD",
  "price_usd": <same as price>,
  "confidence": "estimated"
}
"""

TEXT_READ_PROMPT = """\
Read the user-provided text below. Extract a clearly stated price if one is present.

Return JSON (no markdown fencing):
{
  "item": "<short description of the item>",
  "price": <numeric price as a float>,
  "currency": "<3-letter currency code, e.g. USD, EUR, GBP>",
  "price_usd": <price converted to USD (use approximate current rates)>,
  "confidence": "read"
}

If no explicit price is present, return:
{"item": "<what is described>", "price": null, "currency": null, "price_usd": null, "confidence": "none"}
"""

TEXT_GUESS_PROMPT = """\
Read the user-provided text below. Identify the main item or product being described.

Estimate its typical retail price in USD based on that description.

Return JSON (no markdown fencing):
{
  "item": "<short description>",
  "price": <estimated price as float>,
  "currency": "USD",
  "price_usd": <same as price>,
  "confidence": "estimated"
}
"""

QUIP_PROMPT = """\
I just found out that a {item} (${price:.2f}) is equivalent to {tokens:,} {model_name} tokens.

Write a single short funny one-liner (under 100 chars) about this. Be witty and slightly \
absurd. No quotes around it. Just the line.
"""


@dataclass
class VisionResult:
    item: str
    price_usd: float | None
    currency: str | None
    confidence: str  # "read", "estimated", or "none"
    backend: str = "unknown"


def _get_key(*names: str) -> str | None:
    """Look up an env var by multiple possible names (case-insensitive fallbacks)."""
    for name in names:
        val = os.environ.get(name)
        if val:
            return val
    return None


def _gemini_key() -> str | None:
    return _get_key("GEMINI_API_KEY", "GeminiAPIKey", "GEMINI_KEY")


def _openrouter_key() -> str | None:
    return _get_key("OPENROUTER_API_KEY", "OpenRouterKey", "OPENROUTER_KEY")


def _openai_compatible_key() -> str | None:
    return _get_key(
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "OPENAI_COMPATIBLE_API_KEY",
        "OpenRouterKey",
        "OPENROUTER_KEY",
    )


def _backend_label(model: str) -> str:
    return f"openrouter/{model}"


def detect_backend() -> str:
    """Auto-detect which backend to use based on available API keys."""
    if _gemini_key():
        return "gemini"
    if _openai_compatible_key():
        return "openrouter"
    raise RuntimeError(
        "No API key found. Set GEMINI_API_KEY or an OpenAI-compatible API key.\n"
        "  Gemini (free): https://aistudio.google.com/apikey\n"
        "  OpenRouter (free models available): https://openrouter.ai/keys"
    )


# ── Gemini backend ────────────────────────────────────────────────────────────

def _gemini_client():
    from google import genai
    return genai.Client(api_key=_gemini_key())


def _gemini_image_part(source: str):
    from google.genai import types
    from pathlib import Path
    path = Path(source)
    if path.exists():
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}
        mime = mime_map.get(path.suffix.lower(), "image/jpeg")
        return types.Part.from_bytes(data=path.read_bytes(), mime_type=mime)
    return types.Part.from_uri(file_uri=source, mime_type="image/jpeg")


def _query_gemini(source: str, prompt: str) -> VisionResult:
    from google.genai import types
    client = _gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[_gemini_image_part(source), prompt],
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=1024),
    )
    return _parse_result(response.text, backend="gemini")


def _query_gemini_text(text: str, prompt: str) -> VisionResult:
    from google.genai import types
    client = _gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[f"{prompt}\n\nUser text:\n{text}"],
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=1024),
    )
    return _parse_result(response.text, backend="gemini")


def _quip_gemini(prompt: str) -> str:
    from google.genai import types
    client = _gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(temperature=0.9, max_output_tokens=512),
    )
    return response.text.strip()


# ── OpenAI-compatible backend ────────────────────────────────────────────────

def _image_to_data_url(source: str) -> str:
    """Convert a local file or URL to a base64 data URL for the OpenAI messages API."""
    path = Path(source)
    if path.exists():
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}
        mime = mime_map.get(path.suffix.lower(), "image/jpeg")
        b64 = base64.b64encode(path.read_bytes()).decode()
        return f"data:{mime};base64,{b64}"
    # Remote URL — pass through directly
    return source


def _openrouter_client():
    from openai import OpenAI
    return OpenAI(api_key=_openai_compatible_key(), base_url=OPENROUTER_BASE_URL)


def _query_openrouter(source: str, prompt: str, model: str) -> VisionResult:
    client = _openrouter_client()
    image_url = _image_to_data_url(source)
    response = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt},
            ],
        }],
        max_tokens=1024,
        temperature=0.1,
    )
    text = response.choices[0].message.content or ""
    return _parse_result(text, backend=_backend_label(model))


def _query_openrouter_text(text: str, prompt: str, model: str) -> VisionResult:
    client = _openrouter_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": f"{prompt}\n\nUser text:\n{text}"}],
        max_tokens=1024,
        temperature=0.1,
    )
    content = response.choices[0].message.content or ""
    return _parse_result(content, backend=_backend_label(model))


def _quip_openrouter(prompt: str, model: str) -> str:
    client = _openrouter_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.9,
    )
    return (response.choices[0].message.content or "").strip()


# ── Shared ────────────────────────────────────────────────────────────────────

def _parse_result(text: str, backend: str) -> VisionResult:
    text = text.strip()
    if text.startswith("```"):
        # Strip opening fence (```json or ```)
        text = text.split("\n", 1)[1] if "\n" in text else ""
        # Strip closing fence
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return VisionResult(item="unknown", price_usd=None, currency=None,
                            confidence="none", backend=backend)
    return VisionResult(
        item=data.get("item", "unknown"),
        price_usd=data.get("price_usd"),
        currency=data.get("currency"),
        confidence=data.get("confidence", "none"),
        backend=backend,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def read_price(source: str, backend: str = "auto", or_model: str = OPENROUTER_DEFAULT_MODEL) -> VisionResult:
    """Extract a visible price from an image."""
    return _dispatch(source, READ_PROMPT, backend, or_model)


def guess_price(source: str, backend: str = "auto", or_model: str = OPENROUTER_DEFAULT_MODEL) -> VisionResult:
    """Estimate the price of an object in an image."""
    return _dispatch(source, GUESS_PROMPT, backend, or_model)


def read_price_text(text: str, backend: str = "auto", or_model: str = OPENROUTER_DEFAULT_MODEL) -> VisionResult:
    """Extract an explicitly stated price from plain text."""
    return _dispatch_text(text, TEXT_READ_PROMPT, backend, or_model)


def guess_price_text(text: str, backend: str = "auto", or_model: str = OPENROUTER_DEFAULT_MODEL) -> VisionResult:
    """Estimate the price of an item described in plain text."""
    return _dispatch_text(text, TEXT_GUESS_PROMPT, backend, or_model)


def _dispatch(source: str, prompt: str, backend: str, or_model: str) -> VisionResult:
    if backend == "auto":
        backend = detect_backend()
    if backend == "gemini":
        return _query_gemini(source, prompt)
    if backend == "openrouter":
        return _query_openrouter(source, prompt, or_model)
    raise ValueError(f"Unknown backend: {backend!r}. Use 'gemini' or 'openrouter'.")


def _dispatch_text(text: str, prompt: str, backend: str, or_model: str) -> VisionResult:
    if backend == "auto":
        backend = detect_backend()
    if backend == "gemini":
        return _query_gemini_text(text, prompt)
    if backend == "openrouter":
        return _query_openrouter_text(text, prompt, or_model)
    raise ValueError(f"Unknown backend: {backend!r}. Use 'gemini' or 'openrouter'.")


def generate_quip(item: str, price: float, tokens: int, model_name: str,
                  backend: str = "auto", or_model: str = OPENROUTER_DEFAULT_MODEL) -> str:
    """Generate a fun one-liner comparing the purchase to tokens."""
    try:
        if backend == "auto":
            backend = detect_backend()
        prompt = QUIP_PROMPT.format(item=item, price=price, tokens=tokens, model_name=model_name)
        if backend == "gemini":
            return _quip_gemini(prompt)
        if backend == "openrouter":
            return _quip_openrouter(prompt, or_model)
    except Exception:
        pass
    return f"That's a lot of tokens for a {item}."
