# AGENTS.md — TokenEyes Codebase Guide

Tool-agnostic context file for AI coding agents. Read this before exploring the codebase.
See also: [CLAUDE.md](./CLAUDE.md) for Claude-specific guidance.

---

## What This Project Is

TokenEyes converts real-world prices (read from photos via vision AI) into AI token equivalents.
"That $6 latte? 1.2 million Claude Sonnet tokens."

**Primary product:** `cloudflare/` — a zero-backend static web app deployed on Cloudflare Pages.
**Secondary:** `tokeneyes/` Python package (CLI + local FastAPI server). Functional but not the focus.

---

## Architecture at a Glance

```
cloudflare/          ← MAIN PRODUCT (Cloudflare Pages static site)
  index.html         ← entire app: camera, provider config, token math, UI
  functions/
    advisor.js       ← Pages Function: free quip generation via Gemma 4 (Workers AI)
    country.js       ← Pages Function: returns visitor's CF country code (free)
  _headers           ← CSP + security headers
  DEPLOY.md          ← deployment instructions + required CF bindings

tokeneyes/           ← Python package (CLI + local web server)
  vision.py          ← Gemini & OpenRouter vision backends
  pricing.py         ← token pricing math (MODELS dict)
  display.py         ← Rich terminal output
  cli.py             ← Click CLI (`tokeneyes` command)
  web_runner.py      ← starts local FastAPI server

web/                 ← Local FastAPI server (secondary, not deployed)
  app.py             ← API endpoints (/api/analyze, /api/models)
  static/index.html  ← local web UI (mirrors cloudflare/index.html feature-wise)
```

---

## Key Commands

```bash
# Cloudflare app — no build step, open directly
python3 -m http.server 3000 -d cloudflare/   # local preview

# Python CLI
pip install -e .
tokeneyes photo.jpg                  # read price from image
tokeneyes --price 5.99               # skip vision, just convert
tokeneyes photo.jpg --guess          # estimate price (no visible tag)
tokeneyes --list-models              # show all pricing models
tokeneyes-web                        # start local web server (port 8000)

# Environment (copy and fill in)
cp .env.example .env
```

---

## Providers & API Keys

| Provider | Env var | Used for |
|---|---|---|
| Gemini | `GEMINI_API_KEY` | Vision (image → price) |
| OpenRouter | `OPENROUTER_API_KEY` | Vision (free models available) |
| Cloudflare Workers AI | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_WORKERS_API_KEY` | Vision (Llama/Gemma) |

The Cloudflare Pages app takes keys **in-browser only** — no server, no key logging.

---

## Quip Generation (Two Modes)

The funny one-liner after each result has two paths:

- **Normal mode** (default): calls user's vision provider with a culturally-enriched prompt using `detectedCountry` (from `/country` Pages Function). Uses ~100 output tokens from user's key.
- **Simple mode** (toggle in UI): calls `/advisor` Pages Function → Gemma 4 on Workers AI → KV pool → 25 hardcoded static quips. Zero user quota used.

---

## Pricing Table

`cloudflare/index.html` `MODELS` array and `tokeneyes/pricing.py` `MODELS` dict are **separate** — keep them in sync manually when updating prices. Token split: 30% input / 20% reasoning / 50% output (or 40/60 without reasoning).

---

## What NOT to Change

- **`cloudflare/_redirects`** — intentionally empty (no SPA fallback; Cloudflare would loop)
- **`cloudflare/_headers`** CSP — `connect-src` must list all API domains explicitly; breaking it blocks user API calls
- **`functions/advisor.js` `POOL_MAX`** — caps the quip pool at 300 entries to keep KV read/write fast; raising it is safe but pointless (diversity plateaus well before 300)
- **`web/` directory** — local dev only, not deployed; don't add complexity here

---

## Common Tasks → Where to Look

| Task | File(s) |
|---|---|
| Add a new pricing model to the table | `cloudflare/index.html` `MODELS` array + `tokeneyes/pricing.py` `MODELS` dict |
| Add a new vision model option (Gemini) | `cloudflare/index.html` `#gemini-model-input` select options + `geminiVisionModel` state |
| Add a new vision model option (CF AI) | `cloudflare/index.html` `#cf-model-input` select options + `cfVisionModel` state |
| Add a new OpenRouter free model | `cloudflare/index.html` `OPENROUTER_MODELS` array + `tokeneyes/vision.py` `OPENROUTER_FREE_MODELS` |
| Change quip prompt tone | `cloudflare/index.html` `quipPrompt` / `normalQuipPrompt` functions |
| Update Gemma model used for free quips | `cloudflare/functions/advisor.js` `ADVISOR_MODEL` constant |
| Change token split ratios | `cloudflare/index.html` `calcTokens()` `sp` object |
| Update share card design | `cloudflare/index.html` `#share-btn` click handler (Canvas API) |
| Add a fun fact reference | `cloudflare/index.html` `REFS` array |

---

## Docs Graph

```
AGENTS.md                    ← you are here (start here)
├── CLAUDE.md                ← Claude-specific guidance (builds on AGENTS.md)
├── cloudflare/DEPLOY.md     ← CF Pages deployment, required bindings (AI + KV)
├── .env.example             ← all supported env vars with comments
└── README.md                ← user-facing docs
```

External references:
- CF Workers AI model catalog: https://developers.cloudflare.com/workers-ai/models/
- OpenRouter free models: https://openrouter.ai/models?q=:free
- Gemini model list: https://ai.google.dev/gemini-api/docs/models

---

## Documentation Maintenance Rules (for agents)

**These rules apply whenever you add or modify documentation:**

### When to split a doc

Split a document when any of these are true:
- A single section exceeds ~80 lines and covers a self-contained concern
- A new subsystem is added (new provider, new UI section, new deployment target)
- An agent would need to load the whole file just to answer a narrow question

### How to split

1. Create a focused file under `docs/` (e.g. `docs/pricing.md`, `docs/providers.md`, `docs/ui-architecture.md`)
2. Replace the original section with a one-line pointer: `→ See [docs/pricing.md](./docs/pricing.md)`
3. Update the **Docs Graph** section in this file to include the new node
4. Each new doc must start with: what it covers, what links to it, and what it links out to

### Graph traversal contract

Every documentation file must declare its edges at the top:

```markdown
**Part of:** [AGENTS.md](../AGENTS.md)
**Related:** [docs/other.md](./other.md)
```

This lets an agent load only the relevant node without a full codebase scan.

### Current threshold

This codebase is small — one AGENTS.md is fine now. Split when `AGENTS.md` exceeds **200 lines** or when a second major subsystem (e.g. mobile app, browser extension, receipt mode) is added.

---

## Architecture Review

_Reviewed by Claude Sonnet 4.6 · 2026-04-07_

The architecture as documented is logically sound. Specific checks:

- **Security model** — user keys are memory-only in-browser, never touch any TokenEyes server. Pages Functions (`advisor.js`, `country.js`) use the deployer's Workers AI binding exclusively. No credentials are committed to the repo. Safe to open-source as-is.
- **Quip fallback chain** — Normal (user key + country context) → Simple toggle (`/advisor` → Gemma 4 → KV pool → 25 static quips). Every layer degrades gracefully; the UI always gets a quip or hides the card cleanly.
- **Provider/model flow** — per-provider model selectors (Gemini, CF AI, OpenRouter) wired to state variables and used in the correct API calls. Default model shown on first load. `r-via` chip reflects the actual model used.
- **Token math** — split ratios (30/20/50 with reasoning, 40/60 without) are applied consistently in `calcTokens()` and used in both the hero count and the full table.
- **Docs graph** — root (`AGENTS.md`) → task table covers all current entry points. Split rules have clear triggers and a defined process. No circular references.
- **Removed complexity** — local model (`or_base_url`) removed cleanly from JS, Python CLI, FastAPI, and vision module with no dangling references.

One known divergence to watch: `cloudflare/index.html` `MODELS` array and `tokeneyes/pricing.py` `MODELS` dict are manually synced — no test enforces parity. Acceptable at this scale; flag if the project grows.
