from __future__ import annotations

import re
from pathlib import Path

from tokeneyes.pricing import DISPLAY_NAMES, MODELS, WORKLOAD_PROFILES


ROOT = Path(__file__).parent
CLOUDFLARE_INDEX = ROOT / "cloudflare" / "index.html"


def parse_cloudflare_models() -> list[dict[str, object]]:
    text = CLOUDFLARE_INDEX.read_text()
    match = re.search(r"const MODELS = \[(.*?)\];", text, re.DOTALL)
    assert match, "MODELS array not found in cloudflare/index.html"

    model_re = re.compile(
        r"\{\s*id:'(?P<id>[^']+)'\s*,\s*name:'(?P<name>[^']+)'\s*,\s*"
        r"input:(?P<input>[0-9.]+)\s*,\s*cache:(?P<cache>null|[0-9.]+)\s*,\s*"
        r"output:(?P<output>[0-9.]+)\s*,\s*"
        r"reasoning:(?P<reasoning>null|[0-9.]+)\s*\}"
    )

    def num(raw: str) -> float | None:
        return None if raw == "null" else float(raw)

    models: list[dict[str, object]] = []
    for item in model_re.finditer(match.group(1)):
        models.append(
            {
                "id": item.group("id"),
                "name": item.group("name"),
                "input": float(item.group("input")),
                "cache": num(item.group("cache")),
                "output": float(item.group("output")),
                "reasoning": num(item.group("reasoning")),
            }
        )
    return models


def test_cloudflare_models_match_python_catalog() -> None:
    cloudflare_models = parse_cloudflare_models()

    assert [m["id"] for m in cloudflare_models] == list(MODELS.keys())

    for model in cloudflare_models:
        model_id = model["id"]
        assert model["name"] == DISPLAY_NAMES[model_id]
        assert model["input"] == MODELS[model_id]["input"]
        assert model["cache"] == MODELS[model_id].get("cache")
        assert model["output"] == MODELS[model_id]["output"]
        assert model["reasoning"] == MODELS[model_id].get("reasoning")


def test_cloudflare_workload_profiles_match_python_catalog() -> None:
    text = CLOUDFLARE_INDEX.read_text()
    match = re.search(r"const WORKLOAD_PROFILES = \[(.*?)\];", text, re.DOTALL)
    assert match, "WORKLOAD_PROFILES array not found in cloudflare/index.html"

    profile_re = re.compile(
        r"\{\s*id:'(?P<id>[^']+)'.*?"
        r"input:(?P<input>\d+)\s*,\s*cache:(?P<cache>\d+)\s*,\s*"
        r"reasoning:(?P<reasoning>\d+)\s*,\s*output:(?P<output>\d+)\s*\}"
    )
    profiles = {
        item.group("id"): {
            key: int(item.group(key)) / 100
            for key in ("input", "cache", "reasoning", "output")
        }
        for item in profile_re.finditer(match.group(1))
    }

    assert list(profiles.keys()) == list(WORKLOAD_PROFILES.keys())
    for profile_id, split in profiles.items():
        assert split == WORKLOAD_PROFILES[profile_id], profile_id
        assert abs(sum(split.values()) - 1.0) < 1e-9, profile_id


def test_reasoning_is_billed_at_the_output_rate() -> None:
    for model_id, prices in MODELS.items():
        reasoning = prices.get("reasoning")
        if reasoning is not None:
            assert reasoning == prices["output"], model_id


def test_cache_is_cheaper_than_fresh_input() -> None:
    for model_id, prices in MODELS.items():
        cache = prices.get("cache")
        if cache is not None:
            assert cache < prices["input"], model_id


def test_cloudflare_default_hero_model_stays_on_sonnet() -> None:
    text = CLOUDFLARE_INDEX.read_text()
    match = re.search(r"const DEFAULT_HERO_MODEL_ID = '([^']+)';", text)
    assert match, "DEFAULT_HERO_MODEL_ID not found in cloudflare/index.html"
    assert match.group(1) == "claude-sonnet-5"


def test_popular_hero_models_exist_in_catalog() -> None:
    text = CLOUDFLARE_INDEX.read_text()
    match = re.search(r"const POPULAR_HERO_MODELS = \[(.*?)\];", text, re.DOTALL)
    assert match, "POPULAR_HERO_MODELS not found in cloudflare/index.html"

    popular = re.findall(r"'([^']+)'", match.group(1))
    assert popular
    for model_id in popular:
        assert model_id in MODELS, f"{model_id} is not in the pricing catalog"
