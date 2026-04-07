"""Token pricing database and conversion math."""

from __future__ import annotations

from dataclasses import dataclass

# Prices in USD per 1 million tokens (as of 2025-Q2)
MODELS: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input": 3.00,
        "output": 15.00,
        "reasoning": 3.00,
    },
    "claude-opus-4-6": {
        "input": 15.00,
        "output": 75.00,
        "reasoning": 15.00,
    },
    "claude-haiku-4-5": {
        "input": 0.80,
        "output": 4.00,
        "reasoning": 0.80,
    },
    "gemini-2.5-flash": {
        "input": 0.15,
        "output": 0.60,
        "reasoning": 0.25,
    },
    "gemini-2.5-pro": {
        "input": 1.25,
        "output": 10.00,
        "reasoning": 1.25,
    },
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
    },
}

# Friendly display names
DISPLAY_NAMES: dict[str, str] = {
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "claude-opus-4-6": "Claude Opus 4.6",
    "claude-haiku-4-5": "Claude Haiku 4.5",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gpt-4o": "GPT-4o",
    "gpt-4o-mini": "GPT-4o Mini",
}

# Default budget split: how a typical request distributes tokens.
# input 30%, reasoning 20%, output 50% (reasoning only if model supports it)
DEFAULT_SPLIT = {"input": 0.30, "reasoning": 0.20, "output": 0.50}
DEFAULT_SPLIT_NO_REASONING = {"input": 0.40, "output": 0.60}


@dataclass
class TokenBreakdown:
    """Token counts for a single model given a dollar budget."""

    model: str
    display_name: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None  # None if model doesn't support reasoning
    avg_requests: int  # estimated number of "average" requests (1k tokens each)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + (self.reasoning_tokens or 0)


def tokens_for_dollars(usd: float, model: str) -> TokenBreakdown:
    """Calculate how many tokens you get for a given dollar amount on a model."""
    prices = MODELS[model]
    has_reasoning = "reasoning" in prices

    if has_reasoning:
        split = DEFAULT_SPLIT
    else:
        split = DEFAULT_SPLIT_NO_REASONING

    # Allocate budget by split ratio
    budget = {}
    for token_type, ratio in split.items():
        budget[token_type] = usd * ratio

    # Convert dollars to tokens: (budget / price_per_million) * 1_000_000
    input_tokens = int((budget["input"] / prices["input"]) * 1_000_000)
    output_tokens = int((budget["output"] / prices["output"]) * 1_000_000)
    reasoning_tokens = None
    if has_reasoning:
        reasoning_tokens = int((budget["reasoning"] / prices["reasoning"]) * 1_000_000)

    # Average request estimate: assume ~1000 tokens per request (mixed in/out)
    # Use blended cost per token
    total_tokens = input_tokens + output_tokens + (reasoning_tokens or 0)
    blended_cost_per_token = usd / total_tokens if total_tokens > 0 else 0
    avg_request_tokens = 1000
    avg_requests = int(usd / (blended_cost_per_token * avg_request_tokens)) if blended_cost_per_token > 0 else 0

    return TokenBreakdown(
        model=model,
        display_name=DISPLAY_NAMES.get(model, model),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        avg_requests=avg_requests,
    )


def convert_all(usd: float, models: list[str] | None = None) -> list[TokenBreakdown]:
    """Convert a dollar amount to token breakdowns for all (or specified) models."""
    if models is None:
        models = list(MODELS.keys())
    return [tokens_for_dollars(usd, m) for m in models if m in MODELS]


def list_models() -> list[str]:
    """Return all available model IDs."""
    return list(MODELS.keys())
