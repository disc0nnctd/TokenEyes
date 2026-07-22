"""Token pricing database and conversion math."""

from __future__ import annotations

from dataclasses import dataclass

# Prices in USD per 1 million tokens (updated 2026-07-22).
# Keep this in sync with the MODELS array in cloudflare/index.html.
# Claude Sonnet 5 is at its introductory $2/$10 tier (list $3/$15 from 2026-09-01).
MODELS: dict[str, dict[str, float]] = {
    "claude-sonnet-5": {
        "input": 2.00,
        "cache": 0.2,
        "output": 10.00,
        "reasoning": 10.00,
    },
    "claude-fable-5": {
        "input": 10.00,
        "cache": 1.0,
        "output": 50.00,
        "reasoning": 50.00,
    },
    "claude-opus-4-8": {
        "input": 5.00,
        "cache": 0.5,
        "output": 25.00,
        "reasoning": 25.00,
    },
    "claude-sonnet-4-6": {
        "input": 3.00,
        "cache": 0.3,
        "output": 15.00,
        "reasoning": 15.00,
    },
    "claude-haiku-4-5": {
        "input": 1.00,
        "cache": 0.1,
        "output": 5.00,
        "reasoning": 5.00,
    },
    "gpt-5-6-sol": {
        "input": 5.00,
        "cache": 0.5,
        "output": 30.00,
        "reasoning": 30.00,
    },
    "gpt-5-6-terra": {
        "input": 2.50,
        "cache": 0.25,
        "output": 15.00,
        "reasoning": 15.00,
    },
    "gpt-5-6-luna": {
        "input": 1.00,
        "cache": 0.1,
        "output": 6.00,
        "reasoning": 6.00,
    },
    "gpt-5-4-mini": {
        "input": 0.75,
        "cache": 0.075,
        "output": 4.50,
    },
    "gpt-5-4-nano": {
        "input": 0.20,
        "cache": 0.02,
        "output": 1.25,
    },
    "gemini-3-pro": {
        "input": 2.00,
        "cache": 0.2,
        "output": 12.00,
        "reasoning": 12.00,
    },
    "gemini-3-flash": {
        "input": 0.50,
        "cache": 0.05,
        "output": 3.00,
        "reasoning": 3.00,
    },
    "gemini-2.5-flash": {
        "input": 0.30,
        "cache": 0.03,
        "output": 2.50,
        "reasoning": 2.50,
    },
    "gemini-2.5-flash-lite": {
        "input": 0.10,
        "cache": 0.01,
        "output": 0.40,
    },
    "kimi-k3": {
        "input": 3.00,
        "cache": 0.3,
        "output": 15.00,
    },
    "deepseek-v4": {
        "input": 0.435,
        "cache": 0.0435,
        "output": 0.87,
    },
    "deepseek-v4-flash": {
        "input": 0.14,
        "cache": 0.014,
        "output": 0.28,
    },
}

# Friendly display names
DISPLAY_NAMES: dict[str, str] = {
    "claude-sonnet-5": "Claude Sonnet 5",
    "claude-fable-5": "Claude Fable 5",
    "claude-opus-4-8": "Claude Opus 4.8",
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "claude-haiku-4-5": "Claude Haiku 4.5",
    "gpt-5-6-sol": "GPT-5.6 Sol",
    "gpt-5-6-terra": "GPT-5.6 Terra",
    "gpt-5-6-luna": "GPT-5.6 Luna",
    "gpt-5-4-mini": "GPT-5.4 Mini",
    "gpt-5-4-nano": "GPT-5.4 Nano",
    "gemini-3-pro": "Gemini 3 Pro",
    "gemini-3-flash": "Gemini 3 Flash",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash-Lite",
    "kimi-k3": "Kimi K3",
    "deepseek-v4": "DeepSeek V4 Pro",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
}

# How a real request splits its token budget. Percentages are of tokens, not of
# spend — a coding agent re-reads a large cached prefix every turn, which is why
# its cached share dominates. Keep in sync with WORKLOAD_PROFILES in
# cloudflare/index.html.
WORKLOAD_PROFILES: dict[str, dict[str, float]] = {
    "agent": {"input": 0.10, "cache": 0.55, "reasoning": 0.15, "output": 0.20},
    "chat": {"input": 0.25, "cache": 0.00, "reasoning": 0.15, "output": 0.60},
    "rag": {"input": 0.30, "cache": 0.45, "reasoning": 0.05, "output": 0.20},
    "batch": {"input": 0.40, "cache": 0.00, "reasoning": 0.00, "output": 0.60},
}
DEFAULT_PROFILE = "chat"


@dataclass
class TokenBreakdown:
    """Token counts for a single model given a dollar budget."""

    model: str
    display_name: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None  # None if model doesn't support reasoning
    cached_tokens: int | None  # None if model has no prompt-cache tier
    avg_requests: int  # estimated number of "average" requests (1k tokens each)

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + (self.reasoning_tokens or 0)
            + (self.cached_tokens or 0)
        )


def tokens_for_dollars(
    usd: float, model: str, profile: str = DEFAULT_PROFILE
) -> TokenBreakdown:
    """Calculate how many tokens you get for a given dollar amount on a model."""
    prices = MODELS[model]
    split = WORKLOAD_PROFILES.get(profile, WORKLOAD_PROFILES[DEFAULT_PROFILE])
    has_reasoning = "reasoning" in prices
    has_cache = "cache" in prices

    # Fold unsupported buckets into the nearest supported one so the split always
    # accounts for the whole budget regardless of model capability.
    ratios = dict(split)
    if not has_cache:
        ratios["input"] += ratios.pop("cache", 0.0)
        ratios["cache"] = 0.0
    if not has_reasoning:
        ratios["output"] += ratios.pop("reasoning", 0.0)
        ratios["reasoning"] = 0.0

    def tokens(bucket: str, price_key: str) -> int:
        return int((usd * ratios[bucket] / prices[price_key]) * 1_000_000)

    input_tokens = tokens("input", "input")
    output_tokens = tokens("output", "output")
    reasoning_tokens = tokens("reasoning", "reasoning") if has_reasoning else None
    cached_tokens = tokens("cache", "cache") if has_cache else None

    # Average request estimate: assume ~1000 tokens per request (mixed in/out)
    total_tokens = (
        input_tokens + output_tokens + (reasoning_tokens or 0) + (cached_tokens or 0)
    )
    avg_requests = total_tokens // 1000

    return TokenBreakdown(
        model=model,
        display_name=DISPLAY_NAMES.get(model, model),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        cached_tokens=cached_tokens,
        avg_requests=avg_requests,
    )


def convert_all(
    usd: float, models: list[str] | None = None, profile: str = DEFAULT_PROFILE
) -> list[TokenBreakdown]:
    """Convert a dollar amount to token breakdowns for all (or specified) models."""
    if models is None:
        models = list(MODELS.keys())
    return [tokens_for_dollars(usd, m, profile) for m in models if m in MODELS]


def list_models() -> list[str]:
    """Return all available model IDs."""
    return list(MODELS.keys())
